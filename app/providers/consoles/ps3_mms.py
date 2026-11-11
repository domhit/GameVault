import re, struct

TITLE_ID_RE=re.compile(rb'(?:NP[A-Z]{2}|[BNSU][A-Z]{3}|SC[A-Z]{2}|SL[A-Z]{2})\d{5}')
TARGETS={'NPUI94240','NPUI94451','SLES54819'}
TARGET_ORIGINALS={'NPUI94240':'SCUS94240','NPUI94451':'SCUS94451','SLES54819':'SLES54819'}
REQUIRED_GAME_FIELDS=(
    'Common.title','Common.titleForSort','Common.fileName','Common.dirPath',
    'Common.timeCreated','Common.timeModified','Common.stat.playCount','Common.stat.timeLastUsed',
    'Game.titleId','Game.subTitleId','Game.version','Game.bootable','Game.category',
    'Game.gameCategory','Game.timeModified'
)
PAGE_SIZE=0x2000

def _ascii_strings(blob, minimum=3):
    out=[];start=None
    for i,b in enumerate(blob+b'\x00'):
        if 32 <= b <= 126:
            if start is None:start=i
        elif start is not None:
            if i-start>=minimum:out.append((start,blob[start:i].decode('ascii','replace')))
            start=None
    return out

def parse_schema(schema:bytes):
    strings=_ascii_strings(schema);fields=[];seen=set()
    for offset,value in strings:
        if '.' not in value:continue
        m=re.search(r'(Common|Game)\.[A-Za-z0-9_.]+',value)
        if not m:continue
        name=m.group(0).rstrip('.')
        if name not in seen:seen.add(name);fields.append({'name':name,'schema_offset':offset})
    available={x['name'] for x in fields}
    return {'mode':'schema_structural','classes':sorted({x['name'].split('.',1)[0] for x in fields}),
            'fields':fields,'required_game_fields':{n:n in available for n in REQUIRED_GAME_FIELDS},
            'all_required_fields_present':all(n in available for n in REQUIRED_GAME_FIELDS)}

def _page_profile(data,page_no,target_offsets):
    start=page_no*PAGE_SIZE;page=data[start:start+PAGE_SIZE];strings=_ascii_strings(page)
    ids=[{'value':m.group().decode('ascii','replace'),'offset_in_page':m.start(),'absolute_offset':start+m.start()} for m in TITLE_ID_RE.finditer(page)]
    return {'page':page_no,'start_offset':start,'bytes':len(page),'header_hex':page[:64].hex(),
            'header_u16':[struct.unpack_from('<H',page,i)[0] for i in range(0,min(64,len(page)-1),2)],
            'header_u32':[struct.unpack_from('<I',page,i)[0] for i in range(0,min(64,len(page)-3),4)],
            'nonzero_bytes':sum(1 for b in page if b),'zero_bytes':sum(1 for b in page if not b),
            'ascii_string_count':len(strings),'title_ids':ids,
            'target_offsets_in_page':[o-start for o in target_offsets if start<=o<start+PAGE_SIZE],
            'first_strings':[{'offset_in_page':o,'value':v} for o,v in strings[:30]]}

def _target_window(data,tid,offset,original_id=None,before=1024,after=2048):
    start=max(0,offset-before);end=min(len(data),offset+after);blob=data[start:end]
    strings=_ascii_strings(blob)
    ids=[{'value':m.group().decode('ascii','replace'),'relative_to_target':start+m.start()-offset,'absolute_offset':start+m.start()} for m in TITLE_ID_RE.finditer(blob)]
    original_offsets=[]
    if original_id:
        needle=original_id.encode('ascii')
        pos=data.find(needle,start,end)
        while pos>=0:
            original_offsets.append({'absolute_offset':pos,'relative_to_target':pos-offset})
            pos=data.find(needle,pos+1,end)
    return {'title_id':tid,'target_offset':offset,'window_start':start,'window_end':end,
            'crosses_pages':sorted({start//PAGE_SIZE,(end-1)//PAGE_SIZE}),
            'target_offset_in_page':offset%PAGE_SIZE,'original_id':original_id,
            'original_id_offsets':original_offsets,'title_ids':ids,
            'strings':[{'relative_to_target':start+o-offset,'absolute_offset':start+o,'value':v} for o,v in strings]}

def _compare_targets(windows):
    pairs=[]
    for a,b in (('NPUI94240','NPUI94451'),):
        wa=windows.get(a);wb=windows.get(b)
        if not wa or not wb:continue
        oa=wa['original_id_offsets'][0]['relative_to_target'] if wa['original_id_offsets'] else None
        ob=wb['original_id_offsets'][0]['relative_to_target'] if wb['original_id_offsets'] else None
        pairs.append({'targets':[a,b],'package_id_distance':wb['target_offset']-wa['target_offset'],
                      'original_to_package_offsets':[oa,ob],
                      'original_to_package_delta':None if oa is None or ob is None else abs(abs(oa)-abs(ob)),
                      'layout_consistent':oa is not None and ob is not None and abs(abs(oa)-abs(ob))<=16})
    return pairs

RECORD_MARKER=b'\x41\xff\x00\x00\x00\x00'

def _read_cstr(blob,offset,maxlen=256):
    raw=blob[offset:offset+maxlen].split(b'\0',1)[0]
    return raw.decode('utf-8','replace')

def _heap_string(data,base,slot):
    table=base+0x125+slot*4
    if table+4>len(data):return None
    off,length=struct.unpack_from('>HH',data,table)
    if not off or not length or base+off+4>len(data):return None
    # MMS heap entry: 4-byte layout/hash prefix, UTF-8 bytes, NUL padding, length byte and pointer.
    value=data[base+off+4:base+off+length].split(b'\0',1)[0]
    return value.decode('utf-8','replace') if value else None

def _rtc8(raw):
    if len(raw)!=8 or raw==b'\0'*8:return None
    year=struct.unpack('>H',raw[:2])[0];month,day,hour,minute,second,sub=raw[2:]
    if not (2000<=year<=2100 and 1<=month<=12 and 1<=day<=31 and hour<24 and minute<60 and second<60):return None
    return f'{year:04d}-{month:02d}-{day:02d}T{hour:02d}:{minute:02d}:{second:02d}+00:00'

def _decode_game_record(data,marker,index):
    # The reflected record base is marker+2. This maps Game.titleId schema offset 0xDD
    # to the observed fixed field at marker+0xDF and Common.stat.* to 0x78/0x7C.
    base=marker+2
    original=_read_cstr(data,base+0xdd,16)
    if not re.fullmatch(r'(?:[A-Z]{4}\d{5}|NP[A-Z]{2}\d{5})',original or ''):return None
    package=_heap_string(data,base,4)
    title=_heap_string(data,base,2)
    if title:
        title=re.sub(r'[®™](?=\d)', ' ', title);title=title.replace('®','').replace('™','').strip()
    dir_path=_heap_string(data,base,5)
    if not package or not re.fullmatch(r'(?:[A-Z]{4}\d{5}|NP[A-Z]{2}\d{5})',package):return None
    if index is not None and package.encode() not in index:return None
    if not title or not dir_path:return None
    raw_last=data[base+0x7c:base+0x84]
    return {'title_id':package,'original_title_id':original,'title':title,'dir_path':dir_path,
            'play_count':struct.unpack_from('>I',data,base+0x78)[0],
            'last_played_raw':raw_last.hex(),'last_played_at':_rtc8(raw_last),
            'last_played_source_field':'Common.stat.timeLastUsed',
            'record_marker_offset':marker,'record_base_offset':base,
            'idx_key_offset':index.find(package.encode()) if index is not None else None}

def _decode_game_records(data,index):
    records=[];seen=set()
    for m in re.finditer(re.escape(RECORD_MARKER),data):
        row=_decode_game_record(data,m.start(),index)
        if row and row['title_id'] not in seen:seen.add(row['title_id']);records.append(row)
    return records

def parse_metadata_db_hdd(data:bytes,schema:bytes,index:bytes|None=None):
    schema_info=parse_schema(schema);idx_info={'provided':index is not None,'bytes':len(index) if index is not None else 0};records=_decode_game_records(data,index);occ=[]
    for m in TITLE_ID_RE.finditer(data):occ.append({'title_id':m.group().decode('ascii','replace'),'offset':m.start()})
    unique=sorted({x['title_id'] for x in occ});targets={}
    for tid in sorted(TARGETS):
        hits=[x['offset'] for x in occ if x['title_id']==tid]
        targets[tid]={'title_id':tid,'found':bool(hits),'occurrences':len(hits),'offsets':hits[:20]}
    target_offsets=[off for info in targets.values() for off in info['offsets']]
    core_pages=sorted({off//PAGE_SIZE for off in target_offsets})
    analysis_pages=sorted({p+d for p in core_pages for d in (-1,0,1) if 0<=p+d<len(data)//PAGE_SIZE})
    profiles=[_page_profile(data,p,target_offsets) for p in analysis_pages]
    windows={tid:_target_window(data,tid,info['offsets'][0],TARGET_ORIGINALS.get(tid)) for tid,info in targets.items() if info['offsets']}
    comparisons=_compare_targets(windows)
    return {'records':records,'diagnostics':{
        'parser_mode':'schema_structural_cross_page_analyzer','bytes':len(data),'index':idx_info,'id_occurrences':len(occ),'unique_ids':len(unique),
        'schema':{'mode':schema_info['mode'],'classes':schema_info['classes'],'required_game_fields':schema_info['required_game_fields'],
                  'all_required_fields_present':schema_info['all_required_fields_present'],'field_count':len(schema_info['fields'])},
        'targets':targets,'page_analysis':{'page_size':PAGE_SIZE,'total_pages':len(data)//PAGE_SIZE,
          'aligned_bytes':(len(data)//PAGE_SIZE)*PAGE_SIZE,'tail_bytes':len(data)%PAGE_SIZE,
          'target_pages':{tid:sorted({off//PAGE_SIZE for off in info['offsets']}) for tid,info in targets.items()},
          'analysis_pages':analysis_pages,'profiles':profiles},
        'cross_page_windows':windows,'layout_comparisons':comparisons,
        'records_decoded':len(records),'status':'schema/record-slot decoding active; IDX keys validated'
    }}

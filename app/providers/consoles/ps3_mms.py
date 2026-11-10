import re, struct

TITLE_ID_RE=re.compile(rb'(?:NP[A-Z]{2}|[BNSU][A-Z]{3}|SC[A-Z]{2}|SL[A-Z]{2})\d{5}')
TARGETS={'NPUI94240','NPUI94451','SLES54819'}
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
    start=page_no*PAGE_SIZE;page=data[start:start+PAGE_SIZE]
    strings=_ascii_strings(page)
    ids=[{'value':m.group().decode('ascii','replace'),'offset_in_page':m.start(),'absolute_offset':start+m.start()} for m in TITLE_ID_RE.finditer(page)]
    u16=[struct.unpack_from('<H',page,i)[0] for i in range(0,min(64,len(page)-1),2)]
    u32=[struct.unpack_from('<I',page,i)[0] for i in range(0,min(64,len(page)-3),4)]
    nonzero=sum(1 for b in page if b);zero=len(page)-nonzero
    return {'page':page_no,'start_offset':start,'bytes':len(page),'header_hex':page[:64].hex(),
            'header_u16':u16,'header_u32':u32,'nonzero_bytes':nonzero,'zero_bytes':zero,
            'ascii_string_count':len(strings),'title_ids':ids,
            'target_offsets_in_page':[o-start for o in target_offsets if start<=o<start+PAGE_SIZE],
            'first_strings':[{'offset_in_page':o,'value':v} for o,v in strings[:30]]}

def parse_metadata_db_hdd(data:bytes,schema:bytes):
    schema_info=parse_schema(schema);occ=[]
    for m in TITLE_ID_RE.finditer(data):occ.append({'title_id':m.group().decode('ascii','replace'),'offset':m.start()})
    unique=sorted({x['title_id'] for x in occ});targets={}
    for tid in sorted(TARGETS):
        hits=[x['offset'] for x in occ if x['title_id']==tid]
        targets[tid]={'title_id':tid,'found':bool(hits),'occurrences':len(hits),'offsets':hits[:20]}
    pages=sorted({off//PAGE_SIZE for info in targets.values() for off in info['offsets']})
    target_offsets=[off for info in targets.values() for off in info['offsets']]
    profiles=[_page_profile(data,p,target_offsets) for p in pages]
    return {'records':[],'diagnostics':{
        'parser_mode':'schema_structural_page_analyzer','bytes':len(data),'id_occurrences':len(occ),'unique_ids':len(unique),
        'schema':{'mode':schema_info['mode'],'classes':schema_info['classes'],'required_game_fields':schema_info['required_game_fields'],
                  'all_required_fields_present':schema_info['all_required_fields_present'],'field_count':len(schema_info['fields'])},
        'targets':targets,'page_analysis':{'page_size':PAGE_SIZE,'total_pages':len(data)//PAGE_SIZE,
          'aligned_bytes':(len(data)//PAGE_SIZE)*PAGE_SIZE,'tail_bytes':len(data)%PAGE_SIZE,
          'target_pages':{tid:sorted({off//PAGE_SIZE for off in info['offsets']}) for tid,info in targets.items()},
          'profiles':profiles},
        'records_decoded':0,'status':'schema loaded; target page headers profiled; record-slot decoding pending'
    }}

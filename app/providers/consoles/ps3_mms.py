import re

TITLE_ID_RE=re.compile(rb'(?:NP[A-Z]{2}|[BNSU][A-Z]{3}|SC[A-Z]{2}|SL[A-Z]{2})\d{5}')
TARGETS={'NPUI94240','NPUI94451','SLES54819'}
REQUIRED_GAME_FIELDS=(
    'Common.title','Common.titleForSort','Common.fileName','Common.dirPath',
    'Common.timeCreated','Common.timeModified','Common.stat.timeLastUsed',
    'Game.titleId','Game.subTitleId','Game.version','Game.category',
    'Game.gameCategory','Game.timeModified'
)

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
    strings=_ascii_strings(schema)
    fields=[]
    seen=set()
    for offset,value in strings:
        if '.' not in value:continue
        value=value.lstrip(';,|abcdefghijklmnopqrstuvwxyz') if not value.startswith(('Common.','Game.')) else value
        m=re.search(r'(Common|Game)\.[A-Za-z0-9_.]+',value)
        if not m:continue
        name=m.group(0).rstrip('.')
        if name not in seen:
            seen.add(name);fields.append({'name':name,'schema_offset':offset})
    available={x['name'] for x in fields}
    return {
        'mode':'schema_structural',
        'classes':sorted({x['name'].split('.',1)[0] for x in fields}),
        'fields':fields,
        'required_game_fields':{name:name in available for name in REQUIRED_GAME_FIELDS},
        'all_required_fields_present':all(name in available for name in REQUIRED_GAME_FIELDS),
    }

def parse_metadata_db_hdd(data:bytes,schema:bytes):
    schema_info=parse_schema(schema)
    occurrences=[]
    for m in TITLE_ID_RE.finditer(data):
        occurrences.append({'title_id':m.group().decode('ascii','replace'),'offset':m.start()})
    unique=sorted({x['title_id'] for x in occurrences})
    targets={}
    for tid in sorted(TARGETS):
        hits=[x['offset'] for x in occurrences if x['title_id']==tid]
        targets[tid]={'title_id':tid,'found':bool(hits),'occurrences':len(hits),'offsets':hits[:20]}
    # dev27 intentionally does not infer titles, relations, paths or versions from nearby strings.
    # Those values must only be emitted after page/region/object layouts from md_schema.scm are decoded.
    return {'records':[],'diagnostics':{
        'parser_mode':'schema_structural','bytes':len(data),
        'id_occurrences':len(occurrences),'unique_ids':len(unique),
        'schema':schema_info,'targets':targets,
        'records_decoded':0,
        'status':'schema loaded; unsafe proximity heuristics disabled; object-page decoding required'
    }}

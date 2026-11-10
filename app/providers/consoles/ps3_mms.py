import re, struct

TITLE_ID_RE=re.compile(rb'(?:NP[A-Z]{2}|[BNSU][A-Z]{3}|SC[A-Z]{2}|SL[A-Z]{2})\d{5}')
TARGETS={'NPUI94240','NPUI94451','SLES54819'}

def _strings(blob, minimum=3):
    out=[];start=None
    for i,b in enumerate(blob+b'\x00'):
        if 32 <= b <= 126:
            if start is None:start=i
        elif start is not None:
            if i-start>=minimum:out.append((start,blob[start:i].decode('ascii','replace')))
            start=None
    return out

def _near_strings(data, offset, before=1700, after=2400):
    lo=max(0,offset-before);hi=min(len(data),offset+after)
    return [(lo+o,s) for o,s in _strings(data[lo:hi])]

def _looks_id(s):return bool(re.fullmatch(r'[A-Z]{4}\d{5}',s or ''))
def _clean(s):
    s=re.sub(r'^[^A-Za-z0-9]+','',s or '').strip()
    return s

def _looks_title(s):
    s=_clean(s)
    if not s or len(s)<2 or len(s)>180:return False
    if _looks_id(s) or s.startswith(('/', '_INST_', '_GDATA_','00')):return False
    if re.fullmatch(r'[0-9.]+',s):return False
    return any(c.isalpha() for c in s) and not s.lower().endswith(('.sprx','.self','.edat'))

def parse_metadata_db_hdd(data:bytes):
    ids=[]
    for m in TITLE_ID_RE.finditer(data):
        tid=m.group().decode('ascii','replace')
        ids.append((m.start(),tid))
    unique={};records=[]
    for off,tid in ids:
        near=_near_strings(data,off)
        # The proprietary MMS record keeps related printable fields close together.
        # This is deliberately diagnostic/heuristic in dev25, not an authoritative import parser.
        prev=[(p,s) for p,s in near if p<off]
        nxt=[(p,s) for p,s in near if p>off]
        original=next((s for p,s in reversed(prev) if _looks_id(s) and s!=tid),None)
        if original is None:original=next((s for p,s in nxt[:20] if _looks_id(s) and s!=tid),None)
        path=next((s for p,s in nxt if s.startswith('/dev_')),None)
        versions=[s for p,s in prev[-20:]+nxt[:20] if re.fullmatch(r'\d{1,3}(?:\.\d{1,4})+',s)]
        title=None
        # Prefer repeated title strings after dirPath; these are common in Game records.
        candidates=[_clean(s) for p,s in nxt if _looks_title(s)]
        for s in candidates:
            if sum(1 for _,x in nxt if x==s)>=2:title=s;break
        if title is None:title=next(iter(candidates),None)
        rec={'title_id':tid,'offset':off,'title':title,'original_id':original,'dir_path':path,'versions':versions[:4]}
        old=unique.get(tid)
        score=lambda r:sum(bool(r.get(k)) for k in ('title','original_id','dir_path'))
        if old is None or score(rec)>score(old):unique[tid]=rec
    records=list(unique.values())
    return {'records':records,'diagnostics':{
        'bytes':len(data),'id_occurrences':len(ids),'unique_ids':len(records),
        'with_title':sum(bool(x.get('title')) for x in records),'with_original_id':sum(bool(x.get('original_id')) for x in records),
        'with_dir_path':sum(bool(x.get('dir_path')) for x in records),
        'targets':{t:next((x for x in records if x['title_id']==t),{'title_id':t,'found':False}) for t in sorted(TARGETS)}
    }}

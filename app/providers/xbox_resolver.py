import json, os, re, threading, time, requests
from urllib.parse import quote

TIMEOUT=int(os.getenv('METADATA_TIMEOUT','20'))
UA={'User-Agent':'GameVault/1.6.0-dev8 (+https://github.com/domhit/GameVault)'}
X360_INDEX='https://raw.githubusercontent.com/xenia-manager/x360db/main/games.json'
MOBcat_API='https://mobcat.zip/XboxIDs/api.php'
CACHE_TTL=max(300,int(os.getenv('XBOX_RESOLVER_CACHE_SECONDS','21600')))
_lock=threading.RLock();_x360={'rows':None,'by_id':{},'loaded_at':0.0,'error':None}

def normalize_title_id(value):
 value=re.sub(r'[^0-9A-F]','',str(value or '').upper())
 return value if re.fullmatch(r'[0-9A-F]{8}',value) else None

def _text(value):
 value=' '.join(str(value or '').replace('®','').replace('™','').split())
 return value or None

def _fetch_json(url,params=None):
 r=requests.get(url,params=params,headers=UA,timeout=TIMEOUT);r.raise_for_status();return r.json()

def x360_catalog(force=False):
 now=time.time()
 with _lock:
  if not force and _x360['rows'] is not None and now-_x360['loaded_at']<CACHE_TTL:return _x360['rows']
 try:
  raw=_fetch_json(X360_INDEX);rows=raw.get('games',raw) if isinstance(raw,dict) else raw
  if not isinstance(rows,list):raise ValueError('x360db games.json is not a list')
  by_id={}
  for row in rows:
   if not isinstance(row,dict):continue
   ids=[row.get('id')]+list(row.get('alternative_id') or [])
   for value in ids:
    tid=normalize_title_id(value)
    if tid and tid not in by_id:by_id[tid]=row
  with _lock:_x360.update({'rows':rows,'by_id':by_id,'loaded_at':now,'error':None})
  return rows
 except Exception as e:
  with _lock:_x360['error']=f'{type(e).__name__}: {e}'
  raise

def resolve_x360(title_id,fallback=None):
 tid=normalize_title_id(title_id)
 if not tid:return {'ok':False,'platform':'Xbox 360','title_id':title_id,'name':fallback,'source':'console','error':'invalid Xbox Title ID'}
 try:
  x360_catalog()
  with _lock:row=_x360['by_id'].get(tid)
  if not row:return {'ok':False,'platform':'Xbox 360','title_id':tid,'name':fallback,'source':'console','error':'not found in x360db'}
  name=_text(row.get('title') or row.get('name'))
  return {'ok':bool(name),'platform':'Xbox 360','title_id':tid,'name':name or fallback,'source':'x360db','record':row,'error':None if name else 'record has no canonical title'}
 except Exception as e:return {'ok':False,'platform':'Xbox 360','title_id':tid,'name':fallback,'source':'console','error':f'{type(e).__name__}: {e}'}

def _mobcat_name(row):
 if not isinstance(row,dict):return None
 # The API/DB has used both SQL-style and presentation-style keys over time.
 for key in ('Full_Name','Full Name','full_name','Filename','Game_Name','Game Name','game_name','Title','title','Title_Name','Title Name','title_name','XBE_Description','XBE Description'):
  name=_text(row.get(key))
  if name:return name
 return None

def resolve_classic(title_id,fallback=None):
 tid=normalize_title_id(title_id)
 if not tid:return {'ok':False,'platform':'Xbox Classic','title_id':title_id,'name':fallback,'source':'console','error':'invalid Xbox Title ID'}
 try:
  raw=_fetch_json(MOBcat_API,{'id':tid})
  rows=raw if isinstance(raw,list) else (raw.get('results') or raw.get('data') or [raw] if isinstance(raw,dict) else [])
  candidates=[]
  for row in rows:
   name=_mobcat_name(row)
   if name:candidates.append((name,row))
  if not candidates:return {'ok':False,'platform':'Xbox Classic','title_id':tid,'name':fallback,'source':'console','error':'not found in MobCat Xbox IDs'}
  # One Title ID can have several regional discs. Prefer the most frequent canonical full name.
  counts={}
  for name,row in candidates:counts[name]=counts.get(name,0)+1
  name=sorted(counts,key=lambda x:(-counts[x],len(x),x.casefold()))[0]
  regions=[]
  for _,row in candidates:
   for key in ('Region','region','Region_Name','Region Name'):
    value=_text(row.get(key))
    if value and value not in regions:regions.append(value)
  return {'ok':True,'platform':'Xbox Classic','title_id':tid,'name':name,'source':'MobCat Xbox IDs','records':len(candidates),'regions':regions,'record':candidates[0][1],'error':None}
 except Exception as e:return {'ok':False,'platform':'Xbox Classic','title_id':tid,'name':fallback,'source':'console','error':f'{type(e).__name__}: {e}'}

def resolve_name(platform,title_id,fallback=None):
 if platform=='Xbox 360':return resolve_x360(title_id,fallback)
 if platform=='Xbox Classic':return resolve_classic(title_id,fallback)
 return {'ok':False,'platform':platform,'title_id':title_id,'name':fallback,'source':'console','error':'not applicable'}

def status():
 with _lock:return {'x360db':{'catalog_cached':_x360['rows'] is not None,'entries':len(_x360['rows'] or []),'indexed_title_ids':len(_x360['by_id']),'loaded_at':_x360['loaded_at'] or None,'error':_x360['error'],'url':X360_INDEX},'mobcat':{'cached':False,'mode':'per Title ID','url':MOBcat_API},'cache_ttl_seconds':CACHE_TTL}

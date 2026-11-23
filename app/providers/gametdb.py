import os,re,threading,time,requests
TIMEOUT=int(os.getenv('METADATA_TIMEOUT','20'))
UA={'User-Agent':'GameVault/1.6.0-dev8 (+https://github.com/domhit/GameVault)'}
WII_TITLES='https://www.gametdb.com/wiitdb.txt?LANG=EN'
CACHE_TTL=max(300,int(os.getenv('GAMETDB_CACHE_SECONDS','21600')))
_lock=threading.RLock();_cache={'rows':None,'loaded_at':0.0,'error':None}
def normalize_wii_id(value):
 value=re.sub(r'[^A-Z0-9]','',str(value or '').upper())
 return value if re.fullmatch(r'[A-Z0-9]{6}',value) else None
def _parse_titles(text):
 out={}
 for raw in str(text or '').splitlines():
  line=raw.strip().lstrip('\ufeff')
  if not line or line.startswith(('#',';')):continue
  m=re.match(r'^([A-Za-z0-9]{6})\s*=\s*(.+?)\s*$',line)
  if not m:continue
  gid=normalize_wii_id(m.group(1));title=' '.join(m.group(2).replace('®','').replace('™','').split())
  if gid and title and gid not in out:out[gid]=title
 return out
def catalog(force=False):
 now=time.time()
 with _lock:
  if not force and _cache['rows'] is not None and now-_cache['loaded_at']<CACHE_TTL:return _cache['rows']
 try:
  r=requests.get(WII_TITLES,headers=UA,timeout=TIMEOUT);r.raise_for_status();rows=_parse_titles(r.text)
  if len(rows)<100:raise ValueError(f'GameTDB Wii title list unexpectedly small: {len(rows)}')
  with _lock:_cache.update({'rows':rows,'loaded_at':now,'error':None})
  return rows
 except Exception as e:
  with _lock:_cache['error']=f'{type(e).__name__}: {e}'
  raise
def resolve_wii(game_id,fallback=None):
 gid=normalize_wii_id(game_id)
 if not gid:return {'ok':False,'game_id':game_id,'name':fallback,'source':'console','error':'invalid Wii Game ID'}
 try:
  name=catalog().get(gid)
  if not name:return {'ok':False,'game_id':gid,'name':fallback,'source':'console','error':'not found in GameTDB'}
  return {'ok':True,'game_id':gid,'name':name,'source':'GameTDB','error':None}
 except Exception as e:return {'ok':False,'game_id':gid,'name':fallback,'source':'console','error':f'{type(e).__name__}: {e}'}
def status():
 with _lock:return {'cached':_cache['rows'] is not None,'entries':len(_cache['rows'] or {}),'loaded_at':_cache['loaded_at'] or None,'error':_cache['error'],'url':WII_TITLES,'cache_ttl_seconds':CACHE_TTL}

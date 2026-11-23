import os,re,requests
from urllib.parse import quote
TIMEOUT=int(os.getenv('METADATA_TIMEOUT','20'))
BASE='https://api.serialstation.com/v1'
UA={'User-Agent':'GameVault/1.6.0-dev6 (+https://github.com/domhit/GameVault)'}
PS_PLATFORMS={'PlayStation 1','PlayStation 2','PlayStation Portable','PlayStation Vita','PlayStation 3','PlayStation 4'}
def normalize_title_id(v):
 s=re.sub(r'[^A-Z0-9]','',str(v or '').upper())
 return s if len(s)==9 else None
def _name_from(obj):
 if not isinstance(obj,dict):return None
 # The API may expose the game as an object or the resolved title directly.
 for k in ('name','game_name','title'):
  v=obj.get(k)
  if isinstance(v,str) and v.strip():return v.strip()
 game=obj.get('game')
 if isinstance(game,dict):
  v=game.get('name') or game.get('title')
  if v:return str(v).strip()
 games=obj.get('games')
 if isinstance(games,list) and len(games)==1 and isinstance(games[0],dict):
  v=games[0].get('name') or games[0].get('title')
  if v:return str(v).strip()
 return None
def resolve_title_id(title_id):
 tid=normalize_title_id(title_id)
 if not tid:return {'ok':False,'title_id':title_id,'error':'unsupported/non-9-char PlayStation Title ID'}
 try:
  r=requests.get(f'{BASE}/title-ids/{quote(tid)}',headers=UA,timeout=TIMEOUT)
  if r.status_code==404:return {'ok':False,'title_id':tid,'error':'not found'}
  r.raise_for_status();obj=r.json();name=_name_from(obj)
  return {'ok':bool(name),'title_id':tid,'name':name,'raw':obj,'error':None if name else 'response contains no canonical game name'}
 except Exception as e:return {'ok':False,'title_id':tid,'error':f'{type(e).__name__}: {e}'}
def resolve_name(platform,title_id,fallback=None):
 if platform not in PS_PLATFORMS or not title_id:return {'ok':False,'name':fallback,'source':'console','error':'not applicable'}
 r=resolve_title_id(title_id)
 if r.get('ok'):return {'ok':True,'name':r['name'],'source':'SerialStation','title_id':r['title_id']}
 return {'ok':False,'name':fallback,'source':'console','title_id':normalize_title_id(title_id),'error':r.get('error')}

import os, time, requests
from difflib import SequenceMatcher
from datetime import datetime, timezone
from pathlib import Path
CLIENT_ID=os.getenv('IGDB_CLIENT_ID','')
CLIENT_SECRET=os.getenv('IGDB_CLIENT_SECRET','')
TIMEOUT=int(os.getenv('METADATA_TIMEOUT','20'))
TOKEN_URL='https://id.twitch.tv/oauth2/token'
API='https://api.igdb.com/v4'
PLATFORMS={'PlayStation 2':8,'PlayStation 3':9,'PlayStation 4':48,'Xbox 360':12}
_token=None

def configured(): return bool(CLIENT_ID and CLIENT_SECRET)
def token():
 global _token
 if _token and _token[1]>time.time()+60:return _token[0]
 if not configured():raise RuntimeError('IGDB_CLIENT_ID/IGDB_CLIENT_SECRET fehlen')
 r=requests.post(TOKEN_URL,params={'client_id':CLIENT_ID,'client_secret':CLIENT_SECRET,'grant_type':'client_credentials'},timeout=TIMEOUT);r.raise_for_status()
 j=r.json();_token=(j['access_token'],time.time()+int(j.get('expires_in',3600)));return _token[0]
def post(endpoint,body):
 r=requests.post(f'{API}/{endpoint}',headers={'Client-ID':CLIENT_ID,'Authorization':f'Bearer {token()}'},data=body.encode(),timeout=TIMEOUT);r.raise_for_status();return r.json()
def esc(s):return (s or '').replace('\\','\\\\').replace('"','\\"')
def norm(s):return ''.join(c for c in (s or '').casefold() if c.isalnum())
def _score(rows,title):
 nt=norm(title);seen={}
 for r in rows:
  if not r.get('id'):continue
  base=SequenceMatcher(None,nt,norm(r.get('name',''))).ratio();exact=1 if nt==norm(r.get('name','')) else 0
  r['_confidence']=round(min(1.0,base+0.04*exact),3);seen[r['id']]=r
 return sorted(seen.values(),key=lambda x:x['_confidence'],reverse=True)

def search(title,platform,limit=8):
 pid=PLATFORMS.get(platform)
 fields='name,summary,first_release_date,cover.image_id,genres.name,game_modes.name,player_perspectives.name,themes.name,franchises.name,game_engines.name,multiplayer_modes.offlinecoop,multiplayer_modes.offlinemax,multiplayer_modes.onlinecoop,multiplayer_modes.onlinecoopmax,multiplayer_modes.onlinemax,multiplayer_modes.lancoop,multiplayer_modes.splitscreen,multiplayer_modes.splitscreenonline,multiplayer_modes.campaigncoop,multiplayer_modes.dropin,involved_companies.company.name,involved_companies.developer,involved_companies.publisher,platforms.name'
 rows=[]
 if pid:
  rows=post('games',f'search \"{esc(title)}\"; fields {fields}; where platforms = ({pid}); limit {limit};')
 if not rows:
  rows=post('games',f'search \"{esc(title)}\"; fields {fields}; limit {limit};')
 return _score(rows,title)

def get_by_id(igdb_id):
 fields='name,summary,first_release_date,cover.image_id,genres.name,game_modes.name,player_perspectives.name,themes.name,franchises.name,game_engines.name,multiplayer_modes.offlinecoop,multiplayer_modes.offlinemax,multiplayer_modes.onlinecoop,multiplayer_modes.onlinecoopmax,multiplayer_modes.onlinemax,multiplayer_modes.lancoop,multiplayer_modes.splitscreen,multiplayer_modes.splitscreenonline,multiplayer_modes.campaigncoop,multiplayer_modes.dropin,involved_companies.company.name,involved_companies.developer,involved_companies.publisher,platforms.name'
 rows=post('games',f'fields {fields}; where id = {int(igdb_id)}; limit 1;')
 if not rows:return None
 rows[0]['_confidence']=1.0
 return map_record(rows[0])

def map_record(r):
 companies=r.get('involved_companies') or []
 pubs=[x.get('company',{}).get('name') for x in companies if x.get('publisher')]
 devs=[x.get('company',{}).get('name') for x in companies if x.get('developer')]
 cover=r.get('cover',{}).get('image_id')
 return {'igdb_id':r.get('id'),'title':r.get('name'),'description':r.get('summary'),'release_date':datetime.fromtimestamp(r['first_release_date'],timezone.utc).date().isoformat() if r.get('first_release_date') else None,'genres':', '.join(x.get('name','') for x in r.get('genres',[]) if x.get('name')) or None,'publisher':', '.join(filter(None,pubs)) or None,'developer':', '.join(filter(None,devs)) or None,'cover_url':f'https://images.igdb.com/igdb/image/upload/t_cover_big_2x/{cover}.jpg' if cover else None,'game_modes':', '.join(x.get('name','') for x in r.get('game_modes',[]) if x.get('name')) or None,'perspectives':', '.join(x.get('name','') for x in r.get('player_perspectives',[]) if x.get('name')) or None,'themes':', '.join(x.get('name','') for x in r.get('themes',[]) if x.get('name')) or None,'franchises':', '.join(x.get('name','') for x in r.get('franchises',[]) if x.get('name')) or None,'engines':', '.join(x.get('name','') for x in r.get('game_engines',[]) if x.get('name')) or None,'multiplayer_modes':r.get('multiplayer_modes') or [],'confidence':r.get('_confidence',0)}
def download_cover(url,game_id,data_dir):
 if not url:return None
 r=requests.get(url,timeout=TIMEOUT,headers={'User-Agent':'GameVault/0.6.2'});r.raise_for_status()
 if len(r.content)<1000:return None
 p=Path(data_dir)/'covers'/f'{game_id}-igdb.jpg';p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(r.content);return f'/covers/{p.name}'

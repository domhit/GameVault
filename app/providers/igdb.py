import os, time, requests, re
from difflib import SequenceMatcher
from datetime import datetime, timezone
from pathlib import Path
CLIENT_ID=os.getenv('IGDB_CLIENT_ID','')
CLIENT_SECRET=os.getenv('IGDB_CLIENT_SECRET','')
TIMEOUT=int(os.getenv('METADATA_TIMEOUT','20'))
TOKEN_URL='https://id.twitch.tv/oauth2/token'
API='https://api.igdb.com/v4'
PLATFORMS={'PlayStation Vita':46,'PlayStation 1':7,'PlayStation Portable':38,'PlayStation 2':8,'PlayStation 3':9,'PlayStation 4':48,'Xbox 360':12,'Xbox Classic':11,'Wii U':41,'Wii':5,'Nintendo 3DS':37,'Nintendo 64':4,'Super Nintendo':19,'Game Boy':33,'Game Boy Color':22,'Game Boy Advance':24,'Nintendo Entertainment System':18}
PLATFORM_NAMES={v:k for k,v in PLATFORMS.items()}
ORIGINAL_RELEASE_WINDOW_DAYS=365
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

def search_title(title):
 title=(title or '').replace('®','').replace('™','')
 return ' '.join(title.split())
def norm(s):return ''.join(c for c in (s or '').casefold() if c.isalnum())
def search_variants(title):
 title=search_title(title);variants=[]
 def add(v):
  v=' '.join(str(v or '').split()).strip(' -:')
  if v and v.lower() not in {x.lower() for x in variants}:variants.append(v)
 add(title)
 # No-Intro article suffix: "Addams Family, The" -> "The Addams Family".
 m=re.match(r'^(.*),\s*(The|A|An)$',title,re.I)
 if m:add(f'{m.group(2)} {m.group(1)}')
 # Common ROM-set punctuation and apostrophe normalization.
 cleaned=title.replace('_s',"'s")
 for underscore in (' & ',' and ',' '):
  candidate=cleaned.replace(' _ ',underscore)
  add(candidate);add(candidate.replace(' - ',': '));add(candidate.replace(': ',' - '));add(re.sub(r'\s*[-:]\s*',' ',candidate))
 # Trailing German articles, e.g. 'Wilden Fussball-Kerle, Die'.
 m=re.match(r'^(.*),\s*(Die|Der|Das|Ein|Eine)(\s*[-:].*)?$',title,re.I)
 if m:add(f'{m.group(2)} {m.group(1)}{m.group(3) or ""}')
 # Orthographic variants that commonly occur in localized ROM sets.
 for current in list(variants):
  add(re.sub(r'\bPokemon\b','Pokémon',current,flags=re.I));add(re.sub(r'\bFussball\b','Fußball',current,flags=re.I))
 # Repeat after article movement because that transformation can add a new title variant.
 for current in list(variants):
  add(re.sub(r'\bPokemon\b','Pokémon',current,flags=re.I));add(re.sub(r'\bFussball\b','Fußball',current,flags=re.I))
 # Leading licence/series numbers often appear with or without punctuation in IGDB.
 add(re.sub(r'^(\d{3,4})\s*-\s*',r'\1: ',title))
 # Small, reviewed aliases for localized names observed in the real collection.
 aliases={
  'pokemon - feuerrote edition':['Pokémon FireRed Version','Pokémon FireRed'],
  'pokemon feuerrote edition':['Pokémon FireRed Version','Pokémon FireRed'],
 }
 for alias in aliases.get(title.casefold(),[]):add(alias)
 return variants
RETRO_MATCH_PLATFORMS={'Game Boy','Game Boy Color','Game Boy Advance','Nintendo Entertainment System','Super Nintendo'}
MATCH_STOPWORDS={'the','a','an','of','and','or','to','in','on','for','de','der','die','das','ein','eine','le','la','les','el','los','las'}
def match_tokens(value):
 return [x for x in re.findall(r'[a-z0-9]+',str(value or '').casefold().replace('ß','ss')) if x not in MATCH_STOPWORDS]
def smart_auto_accept(source,candidate,confidence,platform):
 if confidence>=.90:return True,'confidence>=90%'
 if platform not in RETRO_MATCH_PLATFORMS or confidence<.75:return False,'below conservative retro threshold'
 src=match_tokens(source);dst=match_tokens(candidate)
 if len(src)<2:return False,'single informative token'
 if str(source or '').casefold().startswith('double game'):return False,'compilation/multiple-title marker'
 src_nums={x for x in src if x.isdigit()};dst_nums={x for x in dst if x.isdigit()}
 if src_nums and dst_nums and src_nums!=dst_nums:return False,'conflicting numbers'
 overlap=set(src)&set(dst)
 if len(overlap)<2:return False,'fewer than two informative shared tokens'
 shorter=set(src) if len(set(src))<=len(set(dst)) else set(dst)
 if not shorter.issubset(overlap):return False,'shorter title not contained in longer title'
 return True,'retro token containment>=75%'
def _score(rows,variants):
 variants=[v for v in variants if v];norms=[norm(v) for v in variants if norm(v)];seen={}
 for r in rows:
  if not r.get('id'):continue
  names=[r.get('name','')]+[x.get('name','') for x in (r.get('alternative_names') or []) if isinstance(x,dict)]
  best=0.0;matched=None
  for query in norms:
   for name in names:
    nn=norm(name)
    if not nn:continue
    ratio=SequenceMatcher(None,query,nn).ratio();exact=query==nn
    containment=(min(len(query),len(nn))/max(len(query),len(nn))) if query in nn or nn in query else 0
    score=max(ratio,containment)+(0.04 if exact else 0)
    if score>best:best=score;matched=name
  row=dict(r);row['_confidence']=round(min(1.0,best),3);row['_matched_name']=matched
  old=seen.get(row['id'])
  if not old or row['_confidence']>old.get('_confidence',0):seen[row['id']]=row
 return sorted(seen.values(),key=lambda x:x['_confidence'],reverse=True)
def search(title,platform,limit=8):
 title=search_title(title);aliases=search_variants(title);pid=PLATFORMS.get(platform)
 fields='name,alternative_names.name,summary,first_release_date,rating,rating_count,aggregated_rating,aggregated_rating_count,cover.image_id,genres.name,game_modes.name,player_perspectives.name,themes.name,franchises.name,game_engines.name,multiplayer_modes.offlinecoop,multiplayer_modes.offlinemax,multiplayer_modes.onlinecoop,multiplayer_modes.onlinecoopmax,multiplayer_modes.onlinemax,multiplayer_modes.lancoop,multiplayer_modes.splitscreen,multiplayer_modes.splitscreenonline,multiplayer_modes.campaigncoop,multiplayer_modes.dropin,involved_companies.company.name,involved_companies.developer,involved_companies.publisher,platforms.name,release_dates.date,release_dates.platform'
 rows=[]
 if pid:
  for alias in aliases:
   rows+=post('games',f'search "{esc(alias)}"; fields {fields}; where platforms = ({pid}); limit {limit};')
 # Broad fallback only after all platform-constrained variants fail.
 if not rows:
  for alias in aliases:rows+=post('games',f'search "{esc(alias)}"; fields {fields}; limit {limit};')
 for row in rows:row['_requested_platform']=platform
 return _score(rows,aliases)
def get_by_id(igdb_id,platform=None):
 fields='name,alternative_names.name,summary,first_release_date,rating,rating_count,aggregated_rating,aggregated_rating_count,cover.image_id,genres.name,game_modes.name,player_perspectives.name,themes.name,franchises.name,game_engines.name,multiplayer_modes.offlinecoop,multiplayer_modes.offlinemax,multiplayer_modes.onlinecoop,multiplayer_modes.onlinecoopmax,multiplayer_modes.onlinemax,multiplayer_modes.lancoop,multiplayer_modes.splitscreen,multiplayer_modes.splitscreenonline,multiplayer_modes.campaigncoop,multiplayer_modes.dropin,involved_companies.company.name,involved_companies.developer,involved_companies.publisher,platforms.name,release_dates.date,release_dates.platform'
 rows=post('games',f'fields {fields}; where id = {int(igdb_id)}; limit 1;')
 if not rows:return None
 rows[0]['_confidence']=1.0
 rows[0]['_requested_platform']=platform
 return map_record(rows[0],platform)

def map_record(r,platform=None):
 platform=platform or r.get('_requested_platform')
 companies=r.get('involved_companies') or []
 pubs=[x.get('company',{}).get('name') for x in companies if x.get('publisher')]
 devs=[x.get('company',{}).get('name') for x in companies if x.get('developer')]
 cover=r.get('cover',{}).get('image_id')
 platform_id=PLATFORMS.get(platform) if platform else None
 def release_platform_id(row):
  value=row.get('platform')
  if isinstance(value,dict):value=value.get('id')
  try:return int(value) if value is not None else None
  except (TypeError,ValueError):return None
 by_platform={}
 for row in (r.get('release_dates') or []):
  pid=release_platform_id(row);stamp=row.get('date')
  if pid is None or not stamp:continue
  try:stamp=int(stamp)
  except (TypeError,ValueError):continue
  by_platform[pid]=min(stamp,by_platform.get(pid,stamp))
 earliest=min(by_platform.values()) if by_platform else (int(r.get('first_release_date')) if r.get('first_release_date') else None)
 cutoff=earliest+ORIGINAL_RELEASE_WINDOW_DAYS*86400 if earliest is not None else None
 original_ids=sorted((pid for pid,stamp in by_platform.items() if cutoff is not None and stamp<=cutoff),key=lambda pid:(by_platform[pid],PLATFORM_NAMES.get(pid,str(pid))))
 original_platforms=[PLATFORM_NAMES[pid] for pid in original_ids if pid in PLATFORM_NAMES]
 platform_stamp=by_platform.get(platform_id) if platform_id is not None else None
 iso=lambda stamp:datetime.fromtimestamp(stamp,timezone.utc).date().isoformat() if stamp else None
 return {'igdb_id':r.get('id'),'title':r.get('name'),'description':r.get('summary'),'release_date':iso(earliest),'platform_release_date':iso(platform_stamp),'original_platforms':original_platforms,'release_dates_by_platform':{PLATFORM_NAMES.get(pid,str(pid)):iso(stamp) for pid,stamp in sorted(by_platform.items(),key=lambda x:x[1])},'genres':', '.join(x.get('name','') for x in r.get('genres',[]) if x.get('name')) or None,'publisher':', '.join(filter(None,pubs)) or None,'developer':', '.join(filter(None,devs)) or None,'cover_url':f'https://images.igdb.com/igdb/image/upload/t_cover_big_2x/{cover}.jpg' if cover else None,'game_modes':', '.join(x.get('name','') for x in r.get('game_modes',[]) if x.get('name')) or None,'perspectives':', '.join(x.get('name','') for x in r.get('player_perspectives',[]) if x.get('name')) or None,'themes':', '.join(x.get('name','') for x in r.get('themes',[]) if x.get('name')) or None,'franchises':', '.join(x.get('name','') for x in r.get('franchises',[]) if x.get('name')) or None,'engines':', '.join(x.get('name','') for x in r.get('game_engines',[]) if x.get('name')) or None,'multiplayer_modes':r.get('multiplayer_modes') or [],'user_rating':round(float(r['rating']),1) if r.get('rating') is not None else None,'user_rating_count':int(r.get('rating_count') or 0) if r.get('rating_count') is not None else None,'critic_rating':round(float(r['aggregated_rating']),1) if r.get('aggregated_rating') is not None else None,'critic_rating_count':int(r.get('aggregated_rating_count') or 0) if r.get('aggregated_rating_count') is not None else None,'confidence':r.get('_confidence',0)}
def download_cover(url,game_id,data_dir):
 if not url:return None
 r=requests.get(url,timeout=TIMEOUT,headers={'User-Agent':'GameVault/1.6.0-dev14'});r.raise_for_status()
 if len(r.content)<1000:return None
 p=Path(data_dir)/'covers'/f'{game_id}-igdb.jpg';p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(r.content);return f'/covers/{p.name}'

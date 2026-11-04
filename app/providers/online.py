import csv, io, json, os, re, requests
from pathlib import Path
TIMEOUT=int(os.getenv('METADATA_TIMEOUT','20'))
UA={'User-Agent':'GameVault/0.4.0 (+https://github.com/domhit/GameVault)'}
X360_INDEX='https://raw.githubusercontent.com/xenia-manager/x360db/main/games.json'
PS4_TITLES='https://raw.githubusercontent.com/Axekinn/ps4-scraper/main/ps4_titles.csv'
PS4_UPDATES='https://raw.githubusercontent.com/Axekinn/ps4-scraper/main/ps4_titles_updates/ps4_titles_update_summary.csv'

def get(url, binary=False):
 r=requests.get(url,headers=UA,timeout=TIMEOUT); r.raise_for_status(); return r.content if binary else r.text

def norm(s): return re.sub(r'[^a-z0-9]','',(s or '').casefold())
def pick(d,*names):
 for n in names:
  for k,v in d.items():
   if norm(k)==norm(n) and v not in (None,''): return v
 return None

def ps4_catalog():
 return list(csv.DictReader(io.StringIO(get(PS4_TITLES))))
def ps4_updates():
 return list(csv.DictReader(io.StringIO(get(PS4_UPDATES))))
def x360_catalog(): return json.loads(get(X360_INDEX))

def ps4_match(rows,title_id,title):
 tid=(title_id or '').upper(); nt=norm(title)
 for r in rows:
  rid=str(pick(r,'title_id','title id','cusa','id') or '').upper()
  if tid and tid==rid:return r
 best=[r for r in rows if nt and norm(str(pick(r,'title','name') or ''))==nt]
 return best[0] if len(best)==1 else None

def update_match(rows,title_id):
 tid=(title_id or '').upper()
 for r in rows:
  if str(pick(r,'title_id','title id','cusa','id') or '').upper()==tid:return r
 return None

def x360_match(rows,title_id,title):
 tid=(title_id or '').upper(); nt=norm(title)
 for r in rows:
  if tid and str(r.get('id','')).upper()==tid:return r
 best=[r for r in rows if nt and norm(r.get('title',''))==nt]
 return best[0] if len(best)==1 else None

def cover_candidate(platform,title_id,record=None):
 tid=(title_id or '').upper()
 if platform=='PlayStation 2' and tid:
  return f'https://raw.githubusercontent.com/xlenore/ps2-covers/main/covers/default/{tid}.jpg'
 if platform=='PlayStation 3' and tid:
  return f'https://raw.githubusercontent.com/st-alves/ps3-covers/main/covers/default/{tid}.jpg'
 if platform=='Xbox 360' and record:
  return record.get('boxart')
 return None

def save_cover(url,game_id,data_dir):
 if not url:return None
 try:
  b=get(url,True)
  if len(b)<1000:return None
  ext='.png' if b[:8]==b'\x89PNG\r\n\x1a\n' else '.jpg'
  p=Path(data_dir)/'covers'/f'{game_id}{ext}'; p.parent.mkdir(parents=True,exist_ok=True); p.write_bytes(b)
  return f'/covers/{p.name}'
 except Exception:return None

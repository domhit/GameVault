import json, os, re, requests
from pathlib import Path
TIMEOUT=int(os.getenv('METADATA_TIMEOUT','20'))
UA={'User-Agent':'GameVault/0.4.1 (+https://github.com/domhit/GameVault)'}
PS4_CATALOG='https://raw.githubusercontent.com/Dinos17/FPKGi-Catalog-Hub/main/ps4/games.json'

def norm_id(v): return re.sub(r'[^A-Z0-9]','',str(v or '').upper())
def serial_variants(v):
 s=norm_id(v)
 m=re.match(r'([A-Z]+)(\d+)$',s)
 if not m:return [str(v or '').upper()]
 a,n=m.groups();return [f'{a}-{n}',f'{a}_{n}',f'{a}{n}']
def get(url,binary=False):
 r=requests.get(url,headers=UA,timeout=TIMEOUT);r.raise_for_status();return r.content if binary else r.text
def load_ps4_catalog():
 raw=json.loads(get(PS4_CATALOG));data=raw.get('DATA',raw);out={}
 values=data.values() if isinstance(data,dict) else data
 for row in values:
  if not isinstance(row,dict):continue
  tid=norm_id(row.get('title_id'))
  if tid and tid not in out:out[tid]=row
 return out
def ps4_candidates(title_id,catalog):
 row=catalog.get(norm_id(title_id))
 return [(row.get('cover_url'),'FPKGi cover catalog')] if row and row.get('cover_url') else []
def ps3_candidates(title_id):
 out=[]
 for s in serial_variants(title_id):
  out += [(f'https://raw.githubusercontent.com/gauss77/Multiman-Resources/master/COV/{s}.JPG','multiMAN Resources'),(f'https://raw.githubusercontent.com/gauss77/Multiman-Resources/main/COV/{s}.JPG','multiMAN Resources'),(f'https://raw.githubusercontent.com/st-alves/ps3-covers/main/covers/default/{s}.jpg','st-alves PS3 Covers')]
 return out
def ps2_candidates(title_id):
 return [(f'https://raw.githubusercontent.com/xlenore/ps2-covers/main/covers/default/{s}.jpg','xlenore PS2 Covers') for s in serial_variants(title_id)]
def candidates(platform,title_id,catalog):
 if not title_id:return []
 if platform=='PlayStation 4':return ps4_candidates(title_id,catalog)
 if platform=='PlayStation 3':return ps3_candidates(title_id)
 if platform=='PlayStation 2':return ps2_candidates(title_id)
 return []
def save_first(items,game_id,data_dir):
 errors=[]
 for url,source in items:
  try:
   b=get(url,True)
   ctype=''
   if len(b)<1000:raise ValueError('response too small')
   ext='.png' if b[:8]==b'\x89PNG\r\n\x1a\n' else '.jpg'
   p=Path(data_dir)/'covers'/f'{game_id}{ext}';p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
   return f'/covers/{p.name}',source,url,errors
  except Exception as e:errors.append(f'{source}: {type(e).__name__}')
 return None,None,None,errors

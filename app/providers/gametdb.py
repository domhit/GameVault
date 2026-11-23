import os,re,threading,time,requests
from bs4 import BeautifulSoup
from pathlib import Path
TIMEOUT=int(os.getenv('METADATA_TIMEOUT','20'))
UA={'User-Agent':'GameVault/1.6.0-dev13 (+https://github.com/domhit/GameVault)'}
WII_TITLES='https://www.gametdb.com/wiitdb.txt?LANG=EN'
WII_GAME='https://www.gametdb.com/Wii/{game_id}'
WIIU_TITLES='https://www.gametdb.com/wiiutdb.txt?LANG=EN'
CACHE_TTL=max(300,int(os.getenv('GAMETDB_CACHE_SECONDS','21600')))
_lock=threading.RLock();_cache={'rows':None,'loaded_at':0.0,'error':None};_wiiu_cache={'rows':None,'loaded_at':0.0,'error':None,'status_code':None,'content_type':None,'bytes':None,'first_ids':[],'last_ids':[]};_details={}
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
def wiiu_catalog(force=False):
 now=time.time()
 with _lock:
  if not force and _wiiu_cache['rows'] is not None and now-_wiiu_cache['loaded_at']<CACHE_TTL:return _wiiu_cache['rows']
 try:
  r=requests.get(WIIU_TITLES,headers=UA,timeout=TIMEOUT);r.raise_for_status();rows=_parse_titles(r.text)
  if not rows:raise ValueError('GameTDB Wii U title list parsed zero entries')
  ids=sorted(rows);with_data={'rows':rows,'loaded_at':now,'error':None,'status_code':r.status_code,'content_type':r.headers.get('content-type'),'bytes':len(r.content),'first_ids':ids[:5],'last_ids':ids[-5:]};
  with _lock:_wiiu_cache.update(with_data)
  return rows
 except Exception as e:
  with _lock:_wiiu_cache['error']=f'{type(e).__name__}: {e}'
  raise
def wiiu_id_candidates(product_code,company_code=None):
 # Wii U Product Codes look like WUP-P-ABAP: the final four characters are
 # already GameTDB's region-specific product token. GameTDB then appends the
 # two-character Nintendo company code (0001 -> 01, 0008 -> 08, 0052 -> 52).
 raw=''.join(str(product_code or '').upper().split())
 m=re.fullmatch(r'WUP-[A-Z0-9]-([A-Z0-9]{4})',raw)
 product=m.group(1) if m else None
 company=re.sub(r'[^A-Z0-9]','',str(company_code or '').upper())
 company_suffix=company[-2:] if len(company)>=2 else None
 out=[]
 def add(v):
  v=re.sub(r'[^A-Z0-9]','',str(v or '').upper())
  if re.fullmatch(r'[A-Z0-9]{4,6}',v) and v not in out:out.append(v)
 if product and company_suffix:add(product+company_suffix)
 if product:add(product) # some eShop entries in GameTDB intentionally have only four chars
 return out
def diagnose_wiiu(product_code,company_code=None):
 candidates=wiiu_id_candidates(product_code,company_code);rows=wiiu_catalog();hits=[{'id':x,'title':rows[x]} for x in candidates if x in rows]
 return {'product_code':product_code,'company_code':company_code,'candidate_ids':candidates,'hits':hits,'ok':bool(hits)}
def resolve_wii(game_id,fallback=None):
 gid=normalize_wii_id(game_id)
 if not gid:return {'ok':False,'game_id':game_id,'name':fallback,'source':'console','error':'invalid Wii Game ID'}
 try:
  name=catalog().get(gid)
  if not name:return {'ok':False,'game_id':gid,'name':fallback,'source':'console','error':'not found in GameTDB'}
  return {'ok':True,'game_id':gid,'name':name,'source':'GameTDB','error':None}
 except Exception as e:return {'ok':False,'game_id':gid,'name':fallback,'source':'console','error':f'{type(e).__name__}: {e}'}
def status():
 with _lock:return {'cached':_cache['rows'] is not None,'entries':len(_cache['rows'] or {}),'loaded_at':_cache['loaded_at'] or None,'error':_cache['error'],'url':WII_TITLES,'cache_ttl_seconds':CACHE_TTL,'detail_cache_entries':len(_details),'wiiu_cached':_wiiu_cache['rows'] is not None,'wiiu_entries':len(_wiiu_cache['rows'] or {}),'wiiu_error':_wiiu_cache['error'],'wiiu_url':WIIU_TITLES,'wiiu_status_code':_wiiu_cache.get('status_code'),'wiiu_content_type':_wiiu_cache.get('content_type'),'wiiu_bytes':_wiiu_cache.get('bytes'),'wiiu_first_ids':_wiiu_cache.get('first_ids') or [],'wiiu_last_ids':_wiiu_cache.get('last_ids') or []}

_DETAIL_LABELS={
 'id','region','type','languages','title','synopsis','developer','publisher','release date','genre','rating','players','online players',
 'accessories','required accessories','optional accessories','wi-fi players','wifi players','case color','rom','version','size','crc','md5','sha-1','sha1'
}
def _label_key(value):
 value=' '.join(str(value or '').split()).strip().casefold().rstrip(':')
 value=re.sub(r'\s*\([a-z]{2}(?:[-_][a-z]{2})?\)\s*$','',value).strip()
 return value
def _is_detail_label(value):
 key=_label_key(value)
 return key in _DETAIL_LABELS or bool(re.fullmatch(r'(?:title|synopsis)\s*\([a-z]{2}(?:[-_][a-z]{2})?\)',key))
def _next_value(lines,label):
 target=_label_key(label)
 for i,value in enumerate(lines):
  key=_label_key(value)
  if key==target:
   if i+1>=len(lines) or _is_detail_label(lines[i+1]):return None
   return lines[i+1].strip()
  prefix=target+' '
  if key.startswith(prefix):
   candidate=' '.join(str(value).split())[len(target):].strip(' :')
   return candidate if candidate and not _is_detail_label(candidate) else None
 return None
def _valid_text(value):
 value=' '.join(str(value or '').split()).strip()
 return value if value and not _is_detail_label(value) else None
def _valid_date(value):
 value=_valid_text(value)
 if not value:return None
 m=re.fullmatch(r'(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})',value)
 if not m:return None
 y,mo,d=map(int,m.groups())
 if not (1970<=y<=2100 and 1<=mo<=12 and 1<=d<=31):return None
 return f'{y:04d}-{mo:02d}-{d:02d}'
def _valid_players(value):
 value=_valid_text(value)
 if not value:return None
 m=re.fullmatch(r'(\d{1,2})(?:\s*[-–]\s*(\d{1,2}))?',value)
 if not m:return None
 lo=int(m.group(1));hi=int(m.group(2) or lo)
 return value if 1<=lo<=hi<=64 else None
def _parse_detail_html(html,game_id):
 soup=BeautifulSoup(html,'html.parser');lines=[' '.join(x.split()) for x in soup.stripped_strings if ' '.join(x.split())]
 game_type=(_valid_text(_next_value(lines,'type')) or '').upper() or None
 title=_valid_text(_next_value(lines,'title (EN)')) or _valid_text(_next_value(lines,'title'))
 synopsis=_valid_text(_next_value(lines,'synopsis (EN)')) or _valid_text(_next_value(lines,'synopsis'))
 developer=_valid_text(_next_value(lines,'developer'));publisher=_valid_text(_next_value(lines,'publisher'))
 release=_valid_date(_next_value(lines,'release date'));genre=_valid_text(_next_value(lines,'genre'));region=_valid_text(_next_value(lines,'region'));languages=_valid_text(_next_value(lines,'languages'))
 players=_valid_players(_next_value(lines,'players'));online=_valid_players(_next_value(lines,'online players')) or _valid_players(_next_value(lines,'wi-fi players')) or _valid_players(_next_value(lines,'wifi players'))
 images=[]
 for img in soup.find_all('img',src=True):
  url=requests.compat.urljoin('https://www.gametdb.com',img.get('src'))
  low=url.casefold()
  if game_id.casefold() in low and any(x in low for x in ('cover','box','case')) and url not in images:images.append(url)
 return {'game_id':game_id,'type':game_type,'title':title,'synopsis':synopsis,'developer':developer,'publisher':publisher,'release_date':release,'genre':genre,'region':region,'languages':languages,'players':players,'online_players':online,'cover_urls':images,'source_url':WII_GAME.format(game_id=game_id)}
def detail(game_id,force=False):
 gid=normalize_wii_id(game_id)
 if not gid:return {'ok':False,'game_id':game_id,'error':'invalid Wii Game ID'}
 now=time.time()
 with _lock:
  row=_details.get(gid)
  if row and not force and now-row.get('_loaded_at',0)<CACHE_TTL:return dict(row)
 try:
  r=requests.get(WII_GAME.format(game_id=gid),headers=UA,timeout=TIMEOUT)
  if r.status_code==404:return {'ok':False,'game_id':gid,'error':'not found in GameTDB detail'}
  r.raise_for_status();row=_parse_detail_html(r.text,gid);row.update({'ok':True,'_loaded_at':now,'error':None})
  with _lock:_details[gid]=row
  return dict(row)
 except Exception as e:return {'ok':False,'game_id':gid,'error':f'{type(e).__name__}: {e}'}
def custom_detail(game_id,force=False):
 row=detail(game_id,force=force)
 row['custom']=bool(row.get('ok') and str(row.get('type') or '').upper()=='CUSTOM')
 return row
def save_custom_cover(row,game_id,data_dir):
 urls=list(row.get('cover_urls') or []);gid=row.get('game_id')
 # Standard GameTDB artwork endpoints are best-effort fallbacks when the detail page did not expose an image URL.
 if gid:
  for region in ('EN','US','EU','DE'):
   for kind in ('cover3D','cover','coverfull'):
    u=f'https://art.gametdb.com/wii/{kind}/{region}/{gid}.png'
    if u not in urls:urls.append(u)
 for url in urls:
  try:
   r=requests.get(url,headers=UA,timeout=TIMEOUT);r.raise_for_status()
   if len(r.content)<1000:continue
   ctype=(r.headers.get('content-type') or '').casefold();ext='.png' if 'png' in ctype or r.content[:8]==b'\x89PNG\r\n\x1a\n' else '.jpg'
   p=Path(data_dir)/'covers'/f'{game_id}-gametdb{ext}';p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(r.content);return f'/covers/{p.name}',url
  except Exception:continue
 return None,None

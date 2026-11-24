import io,os,re,threading,time,zipfile,requests
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from pathlib import Path
TIMEOUT=int(os.getenv('METADATA_TIMEOUT','20'))
UA={'User-Agent':'GameVault/1.6.0-dev22 (+https://github.com/domhit/GameVault)'}
WII_TITLES='https://www.gametdb.com/wiitdb.txt?LANG=EN'
WII_GAME='https://www.gametdb.com/Wii/{game_id}'
WIIU_TITLES='https://www.gametdb.com/wiiutdb.txt?LANG=DE'
WIIU_XML_ZIP=os.getenv('GAMETDB_WIIU_URL','https://www.gametdb.com/wiiutdb.zip?LANG=DE')
GAMETDB_CACHE_DIR=Path(os.getenv('GAMETDB_CACHE_DIR','/data/provider-cache/gametdb'))
WIIU_CACHE_FILE=GAMETDB_CACHE_DIR/'wiiutdb-DE.zip'
CACHE_TTL=max(300,int(os.getenv('GAMETDB_CACHE_SECONDS','21600')))
_lock=threading.RLock();_cache={'rows':None,'loaded_at':0.0,'error':None};_wiiu_cache={'rows':None,'records':{},'loaded_at':0.0,'error':None,'status_code':None,'content_type':None,'bytes':None,'first_ids':[],'last_ids':[],'source':None,'cache_file':str(WIIU_CACHE_FILE),'downloaded_at':None};_details={}
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
def _xml_text(node,path):
 x=node.find(path) if node is not None else None
 return ' '.join((x.text or '').split()) if x is not None and x.text else None

def _wiiu_xml_records(raw):
 if raw[:2]==b'PK':
  with zipfile.ZipFile(io.BytesIO(raw)) as z:
   names=[n for n in z.namelist() if n.lower().endswith('.xml')]
   if not names:raise ValueError('GameTDB Wii U ZIP contains no XML')
   preferred=next((n for n in names if 'wiiutdb' in n.lower()),names[0]);raw=z.read(preferred)
 root=ET.fromstring(raw);out={}
 for game in root.findall('.//game'):
  gid=str(game.get('id') or _xml_text(game,'id') or '').strip().upper()
  if not re.fullmatch(r'[A-Z0-9]{4,6}',gid):continue
  english=original=first=None
  direct=_xml_text(game,'title')
  if direct:original=first=direct
  for loc in game.findall('.//locale'):
   lang=str(loc.get('lang') or loc.get('language') or '').upper();title=_xml_text(loc,'title')
   if title and not first:first=title
   if title and lang in ('EN','ENG','ENGLISH') and not english:english=title
  for node in game.findall('.//title'):
   title=' '.join((node.text or '').split()) if node.text else None;lang=str(node.get('lang') or node.get('language') or '').upper()
   if title and not first:first=title
   if title and lang in ('EN','ENG','ENGLISH') and not english:english=title
  title=english or original or first or gid
  date=game.find('date');release=None
  if date is not None and date.get('year'):
   try:release=f"{int(date.get('year')):04d}-{int(date.get('month') or 1):02d}-{int(date.get('day') or 1):02d}"
   except:release=str(date.get('year'))
  out[gid]={'id':gid,'title':title,'title_en':english,'title_original':original,'region':_xml_text(game,'region'),'type':_xml_text(game,'type'),'developer':_xml_text(game,'developer'),'publisher':_xml_text(game,'publisher'),'release_date':release,'genre':_xml_text(game,'genre'),'synopsis_en':next((_xml_text(loc,'synopsis') for loc in game.findall('.//locale') if str(loc.get('lang') or '').upper()=='EN' and _xml_text(loc,'synopsis')),None)}
 if not out:raise ValueError('GameTDB Wii U XML parsed zero games')
 return out

def _read_wiiu_cache_file():
 if not WIIU_CACHE_FILE.exists():return None
 raw=WIIU_CACHE_FILE.read_bytes();records=_wiiu_xml_records(raw);return raw,records

def refresh_wiiu_catalog(force_download=False):
 now=time.time()
 with _lock:
  if not force_download and _wiiu_cache['records']:return _wiiu_cache['records']
 try:
  cached=None if force_download else _read_wiiu_cache_file()
  if cached:
   raw,records=cached;source='persistent-cache';status=None;ctype='application/zip';downloaded_at=WIIU_CACHE_FILE.stat().st_mtime
  else:
   r=requests.get(WIIU_XML_ZIP,headers=UA,timeout=TIMEOUT);r.raise_for_status();raw=r.content;records=_wiiu_xml_records(raw);source='download';status=r.status_code;ctype=r.headers.get('content-type');downloaded_at=now
   GAMETDB_CACHE_DIR.mkdir(parents=True,exist_ok=True);tmp=WIIU_CACHE_FILE.with_suffix('.tmp');tmp.write_bytes(raw);tmp.replace(WIIU_CACHE_FILE)
  ids=sorted(records);titles={k:v['title'] for k,v in records.items()}
  with _lock:_wiiu_cache.update({'rows':titles,'records':records,'loaded_at':now,'error':None,'status_code':status,'content_type':ctype,'bytes':len(raw),'first_ids':ids[:5],'last_ids':ids[-5:],'source':source,'downloaded_at':downloaded_at})
  return records
 except Exception as e:
  with _lock:_wiiu_cache['error']=f'{type(e).__name__}: {e}'
  raise

def wiiu_catalog(force=False):
 records=refresh_wiiu_catalog(force_download=force)
 return {k:v['title'] for k,v in records.items()}
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
 candidates=wiiu_id_candidates(product_code,company_code);records=refresh_wiiu_catalog();hits=[records[x] for x in candidates if x in records]
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
 with _lock:return {'cached':_cache['rows'] is not None,'entries':len(_cache['rows'] or {}),'loaded_at':_cache['loaded_at'] or None,'error':_cache['error'],'url':WII_TITLES,'cache_ttl_seconds':CACHE_TTL,'detail_cache_entries':len(_details),'wiiu_cached':_wiiu_cache['rows'] is not None,'wiiu_entries':len(_wiiu_cache['rows'] or {}),'wiiu_error':_wiiu_cache['error'],'wiiu_url':WIIU_XML_ZIP,'wiiu_status_code':_wiiu_cache.get('status_code'),'wiiu_content_type':_wiiu_cache.get('content_type'),'wiiu_bytes':_wiiu_cache.get('bytes'),'wiiu_first_ids':_wiiu_cache.get('first_ids') or [],'wiiu_last_ids':_wiiu_cache.get('last_ids') or [],'wiiu_source':_wiiu_cache.get('source'),'wiiu_cache_file':_wiiu_cache.get('cache_file'),'wiiu_downloaded_at':_wiiu_cache.get('downloaded_at')}

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

# Generic persistent XML catalogs for additional Nintendo platforms. These are downloaded
# once and then reused from /data across container restarts.
NINTENDO_XML_SOURCES={
 'Wii':os.getenv('GAMETDB_WII_URL_FULL','https://www.gametdb.com/wiitdb.zip?LANG=DE&WIIWARE=1&GAMECUBE=1'),
 'Nintendo 3DS':os.getenv('GAMETDB_3DS_URL','https://www.gametdb.com/3dstdb.zip?LANG=DE'),
 'Nintendo Switch':os.getenv('GAMETDB_SWITCH_URL','https://www.gametdb.com/switchtdb.zip?LANG=DE'),
}
_NINTENDO_FILES={'Wii':GAMETDB_CACHE_DIR/'wiitdb-DE-full.zip','Nintendo 3DS':GAMETDB_CACHE_DIR/'3dstdb-DE.zip','Nintendo Switch':GAMETDB_CACHE_DIR/'switchtdb-DE.zip'}
_nintendo={p:{'records':{},'loaded_at':None,'source':None,'error':None,'bytes':None,'cache_file':str(_NINTENDO_FILES[p])} for p in NINTENDO_XML_SOURCES}
def _generic_xml_records(raw):
 if raw[:2]==b'PK':
  with zipfile.ZipFile(io.BytesIO(raw)) as z:
   names=[n for n in z.namelist() if n.lower().endswith('.xml')]
   if not names:raise ValueError('GameTDB ZIP contains no XML')
   raw=z.read(names[0])
 root=ET.fromstring(raw);out={}
 for game in root.findall('.//game'):
  gid=str(game.get('id') or _xml_text(game,'id') or '').strip().upper()
  if not gid:continue
  english=original=first=None;direct=_xml_text(game,'title')
  if direct:original=first=direct
  for loc in game.findall('.//locale'):
   lang=str(loc.get('lang') or loc.get('language') or '').upper();title=_xml_text(loc,'title')
   if title and not first:first=title
   if title and lang in ('EN','ENG','ENGLISH') and not english:english=title
  for node in game.findall('.//title'):
   title=' '.join((node.text or '').split()) if node.text else None;lang=str(node.get('lang') or node.get('language') or '').upper()
   if title and not first:first=title
   if title and lang in ('EN','ENG','ENGLISH') and not english:english=title
  title=english or original or first or gid
  out[gid]={'id':gid,'title':title,'title_en':english,'title_original':original,'region':_xml_text(game,'region'),'type':_xml_text(game,'type'),'developer':_xml_text(game,'developer'),'publisher':_xml_text(game,'publisher'),'genre':_xml_text(game,'genre')}
 if not out:raise ValueError('GameTDB XML parsed zero games')
 return out
def nintendo_catalog(platform,force_download=False):
 state=_nintendo[platform];path=_NINTENDO_FILES[platform];url=NINTENDO_XML_SOURCES[platform]
 with _lock:
  if state['records'] and not force_download:return state['records']
 try:
  if path.exists() and not force_download:raw=path.read_bytes();source='persistent-cache'
  else:
   r=requests.get(url,headers=UA,timeout=TIMEOUT);r.raise_for_status();raw=r.content;GAMETDB_CACHE_DIR.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix('.tmp');tmp.write_bytes(raw);tmp.replace(path);source='download'
  records=_generic_xml_records(raw)
  with _lock:state.update({'records':records,'loaded_at':time.time(),'source':source,'error':None,'bytes':len(raw)})
  return records
 except Exception as e:
  with _lock:state['error']=f'{type(e).__name__}: {e}'
  raise
def resolve_wii_full(game_id,fallback=None):
 gid=normalize_wii_id(game_id)
 if not gid:return {'ok':False,'name':fallback,'source':'console','error':'invalid Wii Game ID'}
 try:
  row=nintendo_catalog('Wii').get(gid)
  return {'ok':bool(row),'name':row['title'] if row else fallback,'source':'GameTDB Wii XML' if row else 'console','record':row,'error':None if row else 'not found'}
 except Exception as e:return {'ok':False,'name':fallback,'source':'console','error':str(e)}
def resolve_wiiu(product_code,company_code,fallback=None):
 try:
  r=diagnose_wiiu(product_code,company_code);row=r['hits'][0] if r.get('hits') else None
  return {'ok':bool(row),'name':row['title'] if row else fallback,'source':'GameTDB Wii U XML' if row else 'console','record':row,'candidate_ids':r.get('candidate_ids') or [],'error':None if row else 'not found'}
 except Exception as e:return {'ok':False,'name':fallback,'source':'console','error':str(e)}
def n3ds_id_candidates(product_code):
 raw=''.join(str(product_code or '').upper().split())
 out=[]
 def add(v):
  v=re.sub(r'[^A-Z0-9]','',str(v or '').upper())
  if re.fullmatch(r'[A-Z0-9]{4,8}',v) and v not in out:out.append(v)
 # libctru Product Codes use CTR-/KTR- prefixes; GameTDB uses the trailing game code, e.g. AMKP.
 m=re.fullmatch(r'(?:CTR|KTR)-[A-Z0-9]-([A-Z0-9]{4,8})',raw)
 if m:add(m.group(1))
 # Keep already-normalized exporter values usable without guessing from TitleID.
 if re.fullmatch(r'[A-Z0-9]{4}',raw):add(raw)
 return out

def resolve_3ds(product_code,fallback=None):
 candidates=n3ds_id_candidates(product_code)
 if not candidates:return {'ok':False,'name':fallback,'source':'console','candidate_ids':[],'error':'unsupported 3DS ProductCode format'}
 try:
  records=nintendo_catalog('Nintendo 3DS');hits=[records[x] for x in candidates if x in records];row=hits[0] if hits else None
  return {'ok':bool(row),'name':row['title'] if row else fallback,'source':'GameTDB Nintendo 3DS XML' if row else 'console','record':row,'hits':hits,'candidate_ids':candidates,'error':None if row else 'not found'}
 except Exception as e:return {'ok':False,'name':fallback,'source':'console','candidate_ids':candidates,'error':f'{type(e).__name__}: {e}'}

def resolve_generic(platform,identifier,fallback=None):
 # Product-code driven resolver for 3DS/Switch once exporters provide the GameTDB key.
 key=re.sub(r'[^A-Z0-9]','',str(identifier or '').upper())
 if not key:return {'ok':False,'name':fallback,'source':'console','error':'identifier/product code missing'}
 try:
  row=nintendo_catalog(platform).get(key)
  return {'ok':bool(row),'name':row['title'] if row else fallback,'source':f'GameTDB {platform} XML' if row else 'console','record':row,'error':None if row else 'not found'}
 except Exception as e:return {'ok':False,'name':fallback,'source':'console','error':str(e)}
def nintendo_status():
 with _lock:return {p:{'entries':len(v['records']),'loaded_at':v['loaded_at'],'source':v['source'],'error':v['error'],'bytes':v['bytes'],'cache_file':v['cache_file'],'url':NINTENDO_XML_SOURCES[p]} for p,v in _nintendo.items()}

from ftplib import FTP
from io import BytesIO
import os, re, sqlite3, tempfile, requests
from .base import ConsoleProvider, InstalledTitle

TITLE_ID_RE=re.compile(r'(?i)\b[0-9a-f]{8}\b')
DB_CANDIDATES=(
 '/Hdd1/Aurora/Data/Databases/content.db','/Hdd1/Aurora/Data/Databases/settings.db',
 '/Hdd1/Apps/Aurora/Data/Databases/content.db','/Hdd1/Apps/Aurora/Data/Databases/settings.db',
 '/Usb0/Aurora/Data/Databases/content.db','/Usb0/Aurora/Data/Databases/settings.db')
SYSTEM_NAMES={'aurora','flash','hdd1','hddx','sysext','system','xbox360'}

def norm_tid(v):
 s=re.sub(r'[^0-9A-F]','',str(v or '').upper())
 return s if re.fullmatch(r'[0-9A-F]{8}',s) else None

def pick(row,*names):
 lower={str(k).casefold():v for k,v in row.items()}
 for n in names:
  for k,v in lower.items():
   if k==n.casefold() or n.casefold() in k:
    if v not in (None,''):return v
 return None

def classify(table,row,path):
 text=(' '.join([str(table),str(path)]+[str(v) for v in row.values() if v is not None])).casefold()
 if any(x in text for x in ('title update','titleupdate','tu_version','tu version')):return 'Title Update'
 if any(x in text for x in ('downloadable content',' dlc ','addon','add-on')):return 'DLC'
 if any(x in text for x in ('xbox live arcade','xbla')):return 'XBLA'
 if any(x in text for x in ('xbox classic','xbox1','xbox original')):return 'Xbox Classic'
 return 'Xbox 360 Game'

class AuroraProvider(ConsoleProvider):
 provider_name='xbox360_aurora'
 def __init__(self,host,ftp_port=21,ftp_username='xboxftp',ftp_password='xboxftp',nova_url=None,nova_username='xboxhttp',nova_password='xboxhttp',timeout=20):
  self.host=host;self.ftp_port=int(ftp_port or 21);self.ftp_username=ftp_username or 'xboxftp';self.ftp_password=ftp_password or 'xboxftp';self.nova_url=(nova_url or f'http://{host}:9999').rstrip('/');self.nova_username=nova_username or 'xboxhttp';self.nova_password=nova_password or 'xboxhttp';self.timeout=int(timeout)
 def connect(self):
  ftp=FTP();ftp.connect(self.host,self.ftp_port,timeout=self.timeout);ftp.login(self.ftp_username,self.ftp_password);ftp.set_pasv(True);return ftp
 def health(self):
  out={'provider':self.provider_name,'ftp':{'ok':False},'nova':{'ok':False,'optional':True}}
  try:
   with self.connect() as ftp:out['ftp']={'ok':True,'welcome':ftp.getwelcome(),'pwd':ftp.pwd()}
  except Exception as e:out['ftp']={'ok':False,'error':f'{type(e).__name__}: {e}'}
  try:
   r=requests.get(self.nova_url+'/',timeout=min(self.timeout,10),auth=(self.nova_username,self.nova_password));out['nova']={'ok':r.status_code<500,'status_code':r.status_code,'url':r.url}
  except Exception as e:out['nova']={'ok':False,'optional':True,'error':f'{type(e).__name__}: {e}'}
  out['ok']=out['ftp']['ok'];return out
 def _read(self,ftp,path):
  b=BytesIO();ftp.retrbinary('RETR '+path,b.write);return b.getvalue()
 def _exists(self,ftp,path):
  try:ftp.size(path);return True
  except Exception:
   try:
    parent,name=path.rsplit('/',1);return name in [os.path.basename(x.rstrip('/')) for x in ftp.nlst(parent)]
   except Exception:return False
 def _discover_dbs(self,ftp):return [p for p in DB_CANDIDATES if self._exists(ftp,p)]
 def _rows(self,data):
  fd,path=tempfile.mkstemp(suffix='.db');os.close(fd)
  try:
   open(path,'wb').write(data);con=sqlite3.connect(path);con.row_factory=sqlite3.Row;out=[];schema={}
   tables=[r[0] for r in con.execute("select name from sqlite_master where type='table' and name not like 'sqlite_%'")]
   for table in tables:
    cols=[r[1] for r in con.execute(f'pragma table_info("{table}")')];schema[table]=cols
    if not any(any(token in c.casefold() for token in ('title','name','path','content','version')) for c in cols):continue
    try:
     for row in con.execute(f'select * from "{table}" limit 20000'):out.append((table,dict(row)))
    except Exception:pass
   con.close();return out,schema
  finally:
   try:os.unlink(path)
   except Exception:pass
 def scan(self):
  raw=[];diagnostics={'databases':[],'schemas':{},'errors':[],'rows_examined':0,'rows_rejected':0,'content_counts':{}}
  with self.connect() as ftp:
   dbs=self._discover_dbs(ftp);diagnostics['databases']=dbs
   for dbpath in dbs:
    if not dbpath.lower().endswith('content.db'):continue
    try:rows,schema=self._rows(self._read(ftp,dbpath));diagnostics['schemas'][dbpath]=schema;diagnostics['rows_examined']+=len(rows)
    except Exception as e:diagnostics['errors'].append(f'{dbpath}: {type(e).__name__}: {e}');continue
    for table,row in rows:
     rawid=pick(row,'titleid','title_id','title id')
     if isinstance(rawid,int):tid=f'{rawid & 0xFFFFFFFF:08X}'
     else:
      m=TITLE_ID_RE.search(str(rawid or ''));tid=norm_tid(m.group(0)) if m else None
     title=str(pick(row,'title','name','displayname','display_name') or '').strip()
     path=str(pick(row,'path','file','location','root') or '').strip()
     if not tid:
      m=TITLE_ID_RE.search(' '.join(str(v) for v in row.values() if v is not None));tid=norm_tid(m.group(0)) if m else None
     kind=classify(table,row,path)
     # Reject Aurora/system filesystem pseudo rows and numeric database values.
     if not tid or not title or title.casefold() in SYSTEM_NAMES or title.isdigit() or ('\\Xbox360\\System\\' in path):diagnostics['rows_rejected']+=1;continue
     version=pick(row,'version','tu_version','titleupdate','title_update','media_version')
     content_id=pick(row,'contentid','content_id','mediaid','media_id')
     diagnostics['content_counts'][kind]=diagnostics['content_counts'].get(kind,0)+1
     raw.append(InstalledTitle('Xbox 360',tid,title,str(version) if version not in (None,'') else None,kind,'Aurora content.db',path or dbpath,str(content_id) if content_id not in (None,'') else None,kind,(path.split(':',1)[0] if ':' in path else path.strip('\\/').split('\\',1)[0].split('/',1)[0] or 'Aurora')).to_dict())
  # Games are unique by TitleID+kind; TU/DLC may have multiple versions/content IDs.
  merged={}
  for item in raw:
   kind=item.get('category') or item.get('content_type')
   extra=item.get('content_id') or item.get('installed_version') or item.get('path') if kind in ('DLC','Title Update') else ''
   k=(item.get('identifier'),kind,extra)
   if k not in merged:merged[k]=item;continue
   old=merged[k]
   for f in ('title','installed_version','path','storage','content_id'):
    if not old.get(f) and item.get(f):old[f]=item[f]
  diagnostics['deduplicated_items']=len(merged)
  return {'items':list(merged.values()),'diagnostics':diagnostics}

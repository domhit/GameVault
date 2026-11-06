from ftplib import FTP
from io import BytesIO
import os, re, sqlite3, tempfile, requests
from .base import ConsoleProvider, InstalledTitle

TITLE_ID_RE=re.compile(r'(?i)\b[0-9a-f]{8}\b')
DB_CANDIDATES=(
 '/Hdd1/Aurora/Data/Databases/content.db',
 '/Hdd1/Aurora/Data/Databases/settings.db',
 '/Hdd1/Apps/Aurora/Data/Databases/content.db',
 '/Hdd1/Apps/Aurora/Data/Databases/settings.db',
 '/Usb0/Aurora/Data/Databases/content.db',
 '/Usb0/Aurora/Data/Databases/settings.db',
)

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
 def _discover_dbs(self,ftp):
  return [p for p in DB_CANDIDATES if self._exists(ftp,p)]
 def _rows(self,data):
  fd,path=tempfile.mkstemp(suffix='.db');os.close(fd)
  try:
   open(path,'wb').write(data);con=sqlite3.connect(path);con.row_factory=sqlite3.Row;out=[];schema={}
   tables=[r[0] for r in con.execute("select name from sqlite_master where type='table' and name not like 'sqlite_%'")]
   for table in tables:
    cols=[r[1] for r in con.execute(f'pragma table_info("{table}")')];schema[table]=cols
    if not any(any(token in c.casefold() for token in ('title','name','path','content')) for c in cols):continue
    try:
     for row in con.execute(f'select * from "{table}" limit 10000'):out.append((table,dict(row)))
    except Exception:pass
   con.close();return out,schema
  finally:
   try:os.unlink(path)
   except Exception:pass
 def scan(self):
  items=[];diagnostics={'databases':[],'schemas':{},'errors':[],'rows_examined':0}
  with self.connect() as ftp:
   dbs=self._discover_dbs(ftp);diagnostics['databases']=dbs
   for dbpath in dbs:
    if not dbpath.lower().endswith('content.db'):continue
    try:rows,schema=self._rows(self._read(ftp,dbpath));diagnostics['schemas'][dbpath]=schema;diagnostics['rows_examined']+=len(rows)
    except Exception as e:diagnostics['errors'].append(f'{dbpath}: {type(e).__name__}: {e}');continue
    for table,row in rows:
     rawid=pick(row,'titleid','title_id','title id','contentid','content_id')
     if isinstance(rawid,int):tid=f'{rawid:08X}'
     else:
      m=TITLE_ID_RE.search(str(rawid or ''));tid=norm_tid(m.group(0)) if m else None
     title=str(pick(row,'title','name','displayname','display_name') or '').strip()
     path=str(pick(row,'path','file','location','root') or '').strip()
     if not tid:
      m=TITLE_ID_RE.search(' '.join(str(v) for v in row.values() if v is not None));tid=norm_tid(m.group(0)) if m else None
     if not title and not tid:continue
     version=pick(row,'version','tu_version','titleupdate','title_update')
     source_type=str(pick(row,'contenttype','content_type','type') or 'Aurora Content')
     items.append(InstalledTitle('Xbox 360',tid,title or tid,str(version) if version not in (None,'') else None,source_type,'Aurora content.db',path or dbpath,storage=(path.split(':',1)[0] if ':' in path else path.strip('/').split('/',1)[0] or 'Aurora')).to_dict())
  # Deduplicate by TitleID; fall back to normalized title/path.
  merged={}
  for item in items:
   k=item.get('identifier') or (re.sub(r'[^a-z0-9]','',item.get('title','').casefold()),item.get('path'))
   if k not in merged:merged[k]=item;continue
   old=merged[k]
   for f in ('title','installed_version','path','storage'):
    if not old.get(f) and item.get(f):old[f]=item[f]
  return {'items':list(merged.values()),'diagnostics':diagnostics}

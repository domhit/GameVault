from ftplib import FTP
from io import BytesIO
import os, sqlite3, tempfile, requests
from .base import ConsoleProvider, InstalledTitle

DB_CANDIDATES=(
 '/Hdd1/Aurora/Data/Databases/content.db','/Hdd1/Aurora/Data/Databases/settings.db',
 '/Hdd1/Apps/Aurora/Data/Databases/content.db','/Hdd1/Apps/Aurora/Data/Databases/settings.db',
 '/Usb0/Aurora/Data/Databases/content.db','/Usb0/Aurora/Data/Databases/settings.db')
GROUP_NAMES={1:'Xbox 360 Game',2:'XBLA',4:'Xbox Classic',5:'Homebrew'}

def tid_hex(v):
 try:return f'{int(v) & 0xFFFFFFFF:08X}'
 except:return None

def version_text(base,version=None):
 try:
  if version is not None:return f'TU{int(version)}'
  return str(int(base)) if base not in (None,'') else None
 except:return str(version if version is not None else base or '') or None

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
 def _open_db(self,data):
  fd,path=tempfile.mkstemp(suffix='.db');os.close(fd);open(path,'wb').write(data)
  con=sqlite3.connect(path);con.row_factory=sqlite3.Row
  return con,path
 def _storage(self,directory):
  p=str(directory or '').strip('\\/')
  return p.split('\\',1)[0].split('/',1)[0] or 'Aurora'
 def scan(self):
  items=[];diag={'databases':[],'errors':[],'content_items':0,'title_updates':0,'scan_paths':[],'content_counts':{},'ignored_homebrew':0}
  with self.connect() as ftp:
   dbs=self._discover_dbs(ftp);diag['databases']=dbs
   for dbpath in dbs:
    try:con,tmp=self._open_db(self._read(ftp,dbpath))
    except Exception as e:diag['errors'].append(f'{dbpath}: {type(e).__name__}: {e}');continue
    try:
     tables={r[0] for r in con.execute("select name from sqlite_master where type='table'")}
     if dbpath.lower().endswith('content.db') and 'ContentItems' in tables:
      rows=con.execute('select Id,Directory,TitleId,MediaId,BaseVersion,TitleName,Description,Publisher,Developer,ContentType,ContentGroup,FileType,ScanPathId from ContentItems').fetchall();diag['content_items']+=len(rows)
      # One game row per TitleID/group. Multi-disc rows are collapsed, while their paths remain visible.
      games={}
      for r in rows:
       group=int(r['ContentGroup'] or 0);kind=GROUP_NAMES.get(group)
       if kind=='Homebrew' or kind is None:diag['ignored_homebrew']+=1;continue
       tid=tid_hex(r['TitleId']);title=str(r['TitleName'] or '').strip()
       if not tid or not title:continue
       k=(tid,kind);path=str(r['Directory'] or '')
       if k not in games:
        games[k]={'platform':'Xbox Classic' if kind=='Xbox Classic' else 'Xbox 360','identifier':tid,'title':title,'installed_version':version_text(r['BaseVersion']),'content_type':kind,'source':'Aurora ContentItems','path':path,'content_id':tid_hex(r['MediaId']),'category':kind,'storage':self._storage(path),'paths':[path] if path else []}
       elif path and path not in games[k]['paths']:games[k]['paths'].append(path)
      for g in games.values():
       if len(g['paths'])>1:g['path']=' | '.join(g['paths'])
       g.pop('paths',None);items.append(InstalledTitle(**g).to_dict());diag['content_counts'][g['category']]=diag['content_counts'].get(g['category'],0)+1
     if dbpath.lower().endswith('content.db') and 'TitleUpdates' in tables:
      rows=con.execute('select Id,DisplayName,FileName,LivePath,TitleId,MediaId,BaseVersion,Version,BackupPath,FileSize from TitleUpdates').fetchall();diag['title_updates']+=len(rows)
      for r in rows:
       tid=tid_hex(r['TitleId']);title=str(r['DisplayName'] or f'{tid} Title Update').strip();path=str(r['LivePath'] or r['BackupPath'] or r['FileName'] or '')
       if not tid:continue
       items.append(InstalledTitle('Xbox 360',tid,title,version_text(r['BaseVersion'],r['Version']),'Title Update','Aurora TitleUpdates',path,tid_hex(r['MediaId']),'Title Update',self._storage(path)).to_dict())
      diag['content_counts']['Title Update']=len(rows)
     if dbpath.lower().endswith('settings.db') and 'ScanPaths' in tables:
      diag['scan_paths']=[dict(x) for x in con.execute('select Id,Path,Depth,ScriptData,OptionsFlag from ScanPaths order by Id').fetchall()]
    except Exception as e:diag['errors'].append(f'{dbpath}: {type(e).__name__}: {e}')
    finally:
     con.close()
     try:os.unlink(tmp)
     except Exception:pass
  diag['deduplicated_items']=len(items)
  return {'items':items,'diagnostics':diag}

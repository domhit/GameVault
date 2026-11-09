from ftplib import FTP
from io import BytesIO
import os, sqlite3, tempfile
from .base import ConsoleProvider, InstalledTitle

DEFAULT_DB=r'/E/XBMC4Gamers/system/UserData/profiles/Dominic/Database/MyPrograms6.db'

def tid_hex(v):
 try:return f'{int(v) & 0xFFFFFFFF:08X}'
 except:return None

class XBMC4GamersProvider(ConsoleProvider):
 provider_name='xboxclassic_xbmc4gamers'
 def __init__(self,host,port=21,username='xbox',password='xbox',database_path=DEFAULT_DB,timeout=20):
  self.host=host;self.port=int(port or 21);self.username=username or 'xbox';self.password=password or 'xbox';self.database_path=database_path or DEFAULT_DB;self.timeout=int(timeout)
 def connect(self):
  ftp=FTP();ftp.connect(self.host,self.port,timeout=self.timeout);ftp.login(self.username,self.password);ftp.set_pasv(True);return ftp
 def health(self):
  try:
   with self.connect() as ftp:
    b=BytesIO();ftp.retrbinary('RETR '+self.database_path,b.write,blocksize=4096,rest=None)
   return {'ok':b.getvalue()[:16].startswith(b'SQLite format 3'),'provider':self.provider_name,'database_path':self.database_path,'database_bytes':len(b.getvalue())}
  except Exception as e:return {'ok':False,'provider':self.provider_name,'database_path':self.database_path,'error':f'{type(e).__name__}: {e}'}
 def scan(self):
  with self.connect() as ftp:
   b=BytesIO();ftp.retrbinary('RETR '+self.database_path,b.write)
  fd,path=tempfile.mkstemp(suffix='.db');os.close(fd);open(path,'wb').write(b.getvalue())
  items=[];diag={'database_path':self.database_path,'rows':0,'games':0,'apps_ignored':0,'errors':[]}
  try:
   con=sqlite3.connect(path);con.row_factory=sqlite3.Row
   tables={r[0] for r in con.execute("select name from sqlite_master where type='table'")}
   if 'files' not in tables:raise RuntimeError('files table missing')
   rows=con.execute('select idFile,strFilename,titleId,xbedescription,iSize,altname,developer,publisher,genre,release_date,year,platform,title_id,synopsis,features_general,features_online from files').fetchall();diag['rows']=len(rows)
   for r in rows:
    fn=str(r['strFilename'] or '');low=fn.casefold().replace('/','\\')
    # In the supplied DB actual games live under F:\Games\; E:\Apps are applications/tools.
    if '\\games\\' not in low:diag['apps_ignored']+=1;continue
    title=str(r['altname'] or r['xbedescription'] or '').strip()
    tid=str(r['title_id'] or '').strip().upper() or tid_hex(r['titleId'])
    if not title or not tid:continue
    size=int(r['iSize'] or 0) if str(r['iSize'] or '').lstrip('-').isdigit() else None
    item=InstalledTitle('Xbox Classic',tid,title,None,'Xbox Classic','XBMC4Gamers MyPrograms',fn,category='Xbox Classic',storage=(fn.split(':',1)[0] if ':' in fn else 'Xbox'),file_size=None).to_dict()
    item['installed_size_bytes']=size;item['metadata_hint']={'developer':r['developer'],'publisher':r['publisher'],'genres':r['genre'],'release_date':r['release_date'],'description':r['synopsis'],'features_general':r['features_general'],'features_online':r['features_online']}
    items.append(item);diag['games']+=1
   con.close()
  except Exception as e:diag['errors'].append(f'{type(e).__name__}: {e}')
  finally:
   try:os.unlink(path)
   except Exception:pass
  return {'items':items,'diagnostics':diag}

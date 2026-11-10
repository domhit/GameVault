from ftplib import FTP
from io import BytesIO
import os,re,sqlite3,tempfile
from .base import ConsoleProvider,InstalledTitle
APP_DB='/system_data/priv/mms/app.db'
ADDCONT_DB='/system_data/priv/mms/addcont.db'
CUSA_RE=re.compile(r'^CUSA\d{5}$',re.I)
class PS4GoldHENProvider(ConsoleProvider):
 provider_name='ps4_goldhen'
 def __init__(self,host,port=2121,username='anonymous',password='',database_path=APP_DB,timeout=20):
  self.host=host;self.port=int(port or 2121);self.username=username or 'anonymous';self.password=password or '';self.database_path=database_path or APP_DB;self.timeout=int(timeout)
 def connect(self):
  ftp=FTP();ftp.connect(self.host,self.port,timeout=self.timeout);ftp.login(self.username,self.password);ftp.set_pasv(True);return ftp
 def _read(self,ftp,path):b=BytesIO();ftp.retrbinary('RETR '+path,b.write);return b.getvalue()
 def health(self):
  out={'provider':self.provider_name,'ftp':{'ok':False},'app_db':{'ok':False},'addcont_db':{'ok':False,'optional':True}}
  try:
   with self.connect() as ftp:
    out['ftp']={'ok':True,'welcome':ftp.getwelcome(),'pwd':ftp.pwd()}
    for path,key in ((self.database_path,'app_db'),(ADDCONT_DB,'addcont_db')):
     try:d=self._read(ftp,path);out[key]={'ok':d[:16].startswith(b'SQLite format 3'),'path':path,'bytes':len(d)}
     except Exception as e:out[key]={'ok':False,'path':path,'optional':key=='addcont_db','error':f'{type(e).__name__}: {e}'}
  except Exception as e:out['ftp']={'ok':False,'error':f'{type(e).__name__}: {e}'}
  out['ok']=out['ftp']['ok'] and out['app_db']['ok'];return out
 def _db(self,data):
  fd,p=tempfile.mkstemp(suffix='.db');os.close(fd);open(p,'wb').write(data);c=sqlite3.connect(p);c.row_factory=sqlite3.Row;return c,p
 def scan(self):
  items=[];diag={'app_db':{},'addcont_db':{},'errors':[],'games':0,'dlc':0,'ignored':0}
  with self.connect() as ftp:
   appdata=self._read(ftp,self.database_path)
   try:adddata=self._read(ftp,ADDCONT_DB)
   except Exception as e:adddata=None;diag['errors'].append(f'addcont.db: {type(e).__name__}: {e}')
  c,p=self._db(appdata)
  try:
   tables=[r[0] for r in c.execute("select name from sqlite_master where type='table' and name like 'tbl_appbrowse_%'")]
   if not tables:raise RuntimeError('tbl_appbrowse_* fehlt')
   # Prefer populated/current table with most rows.
   table=max(tables,key=lambda t:c.execute(f'select count(*) from "{t}"').fetchone()[0]);rows=c.execute(f'select titleId,contentId,titleName,metaDataPath,category,uiCategory,contentSize,installDate,externalHddAppStatus,hddLocation,visible from "{table}"').fetchall();diag['app_db']={'table':table,'rows':len(rows)}
   info={}
   if 'tbl_appinfo' in {r[0] for r in c.execute("select name from sqlite_master where type='table'")}:
    for r in c.execute("select titleId,key,val from tbl_appinfo where key in ('APP_VER','VERSION','TITLE','CONTENT_ID','#_size','_size_other_hdd')"):
     info.setdefault(r['titleId'],{})[r['key']]=r['val']
   seen=set()
   for r in rows:
    tid=str(r['titleId'] or '').upper();ui=str(r['uiCategory'] or '').lower();cat=str(r['category'] or '')
    if not CUSA_RE.fullmatch(tid) or ui!='game':diag['ignored']+=1;continue
    if tid in seen:continue
    seen.add(tid);inf=info.get(tid,{});title=str(inf.get('TITLE') or r['titleName'] or tid).strip();ver=str(inf.get('APP_VER') or inf.get('VERSION') or '').strip() or None;size=r['contentSize']
    try:size=int(size) if size is not None else int(inf.get('#_size') or 0) or None
    except:size=None
    external=bool(r['externalHddAppStatus']);storage='Externe HDD' if external else 'Interne HDD';path=str(r['metaDataPath'] or f'/user/app/{tid}')
    item=InstalledTitle('PlayStation 4',tid,title,ver,'PS4 Game','PS4 app.db',path,str(r['contentId'] or inf.get('CONTENT_ID') or '') or None,'PS4 Game',storage).to_dict();item['installed_size_bytes']=size;item['base_version']=str(inf.get('VERSION') or '') or None;item['install_date']=r['installDate'];items.append(item);diag['games']+=1
  finally:c.close();os.unlink(p)
  if adddata:
   c,p=self._db(adddata)
   try:
    rows=c.execute('select title_id,dir_name,content_id,title,version,attribute,status,titles_GERMAN,titles_ENGLISH_US from addcont').fetchall();diag['addcont_db']={'rows':len(rows)}
    for r in rows:
     tid=str(r['title_id'] or '').upper()
     if not CUSA_RE.fullmatch(tid):continue
     title=str(r['titles_GERMAN'] or r['titles_ENGLISH_US'] or r['title'] or r['dir_name'] or r['content_id']).strip();ver=str(r['attribute'] or '').strip() or None
     items.append(InstalledTitle('PlayStation 4',tid,title,ver,'DLC','PS4 addcont.db',str(r['dir_name'] or ''),str(r['content_id'] or '') or None,'DLC','PS4').to_dict());diag['dlc']+=1
   finally:c.close();os.unlink(p)
  return {'items':items,'diagnostics':diag}

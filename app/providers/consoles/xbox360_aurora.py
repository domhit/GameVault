from ftplib import FTP
from io import BytesIO
import os, re, sqlite3, tempfile, requests
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
 def _listing_name(self,value):
  raw=str(value or '').rstrip('/\r\n')
  if not raw:return ''
  # Preserve the filename exactly, including repeated spaces. Strip only the 8 Unix LIST metadata fields.
  m=re.match(r'^[dl-][rwx-]{9}\s+\d+\s+\S+\s+\S+\s+\d+\s+\S+\s+\d+\s+\S+\s+(.*)$',raw)
  if m:return m.group(1).rstrip('/')
  m=re.match(r'^\S+\s+\S+\s+(?:<DIR>|\d+)\s+(.*)$',raw,re.I)
  if m:return m.group(1).rstrip('/')
  return raw.rsplit('/',1)[-1]
 def _entries_here(self,ftp):
  raw=ftp.nlst()
  return [self._listing_name(x) for x in raw if self._listing_name(x)]
 def _cwd_ci(self,ftp,wanted):
  names=self._entries_here(ftp);actual=next((n for n in names if n.casefold()==str(wanted).casefold()),None)
  if not actual:return {'ok':False,'wanted':wanted,'actual':None,'available_sample':names[:30],'error':f'component not found: {wanted}'}
  try:ftp.cwd(actual);return {'ok':True,'wanted':wanted,'actual':actual,'pwd':ftp.pwd(),'error':None}
  except Exception as e:return {'ok':False,'wanted':wanted,'actual':actual,'available_sample':names[:30],'error':f'CWD {actual}: {type(e).__name__}: {e}'}
 def _resolve_by_cwd(self,ftp,db_path):
  start=ftp.pwd();steps=[]
  try:
   ftp.cwd('/')
   first=self._cwd_ci(ftp,'Hdd1');steps.append(first)
   if not first['ok']:return {'ok':False,'path':None,'steps':steps,'error':first['error']}
   for wanted in [x for x in str(db_path or '').replace('\\','/').split('/') if x and x.casefold()!='hdd1']:
    step=self._cwd_ci(ftp,wanted);steps.append(step)
    if not step['ok']:return {'ok':False,'path':None,'steps':steps,'error':step['error']}
   return {'ok':True,'path':ftp.pwd().rstrip('/') or '/','steps':steps,'error':None}
  finally:
   try:ftp.cwd(start)
   except Exception:pass
 def _walk_current_size(self,ftp,seen=None):
  seen=seen or set();pwd=ftp.pwd()
  if pwd in seen:return {'ok':False,'bytes':0,'status':'cycle','files':0,'dirs':0,'method':'CWD+NLST','errors':[]}
  seen.add(pwd);total=files=dirs=0;errors=[]
  try:raw=ftp.nlst()
  except Exception as e:return {'ok':False,'bytes':0,'status':'list_failed','files':0,'dirs':0,'method':'CWD+NLST','errors':[f'{type(e).__name__}: {e}']}
  entries=[]
  for line in raw:
   name=self._listing_name(line)
   if name and name not in ('.','..'):entries.append((name,str(line).lstrip().startswith('d')))
  for name,is_dir_hint in entries:
   if is_dir_hint:
    before=ftp.pwd()
    try:
     ftp.cwd(name);result=self._walk_current_size(ftp,seen);total+=result['bytes'];files+=result['files'];dirs+=1+result['dirs'];errors.extend(result['errors']);ftp.cwd(before);continue
    except Exception as e:
     try:ftp.cwd(before)
     except Exception:pass
   try:
    size=ftp.size(name)
    if size is not None:total+=int(size);files+=1;continue
   except Exception as e:errors.append(f'{pwd}/{name}: {type(e).__name__}: {e}')
  return {'ok':True,'bytes':total,'status':'empty' if not entries else ('partial' if errors else 'directory'),'files':files,'dirs':dirs,'method':'CWD+NLST/SIZE','errors':errors[:30]}
 def calculate_sizes(self,records,progress=None):
  results=[]
  with self.connect() as ftp:
   ftp.cwd('/');roots=self._entries_here(ftp)
   for i,rec in enumerate(records,1):
    source=str(rec.get('path') or '');parts=[x.strip() for x in source.split(' | ') if x.strip()];attempts=[];total=0;all_ok=bool(parts)
    for part in parts:
     resolved=self._resolve_by_cwd(ftp,part)
     if not resolved['ok']:
      attempts.append({'source':part,'candidate':'/Hdd1/'+part.replace('\\','/').strip('/'),'resolved':None,'ok':False,'status':'cwd_resolve_failed','method':'CWD','files':0,'dirs':0,'steps':resolved['steps'],'errors':[resolved['error']]});all_ok=False;continue
     old=ftp.pwd()
     try:
      ftp.cwd(resolved['path']);size=self._walk_current_size(ftp,set());total+=size['bytes'];attempts.append({'source':part,'candidate':'/Hdd1/'+part.replace('\\','/').strip('/'),'resolved':resolved['path'],'ok':size['ok'],'status':size['status'],'method':size['method'],'files':size['files'],'dirs':size['dirs'],'steps':resolved['steps'],'errors':size['errors']});all_ok=all_ok and size['ok']
     finally:
      try:ftp.cwd(old)
      except Exception:pass
    row={'id':rec.get('id'),'source_path':source,'size_bytes':total,'ok':all_ok,'status':'ok' if all_ok else 'path_error','ftp_roots':roots,'attempts':attempts,'error':'; '.join(e for a in attempts for e in a.get('errors',[]))[:500] or None};results.append(row)
    if progress:progress(i,len(records),row)
  return results
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
       tu=InstalledTitle('Xbox 360',tid,title,version_text(r['BaseVersion'],r['Version']),'Title Update','Aurora TitleUpdates',path,tid_hex(r['MediaId']),'Title Update',self._storage(path)).to_dict();tu['file_size']=str(r['FileSize'] or '') or None;items.append(tu)
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

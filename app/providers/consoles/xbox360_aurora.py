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
 def _root_names(self,ftp):
  try:return sorted({str(x).strip('/').split('/')[-1] for x in ftp.nlst('/') if str(x).strip('/')})
  except Exception:return []
 def _resolve_case_path(self,ftp,path):
  parts=[x for x in str(path or '').replace('\\','/').split('/') if x];current='';steps=[]
  if not parts:return {'ok':False,'path':None,'steps':[],'error':'empty path'}
  for wanted in parts:
   parent=current or '/'
   try:names=self._root_names(ftp) if parent=='/' else [str(x).rstrip('/').rsplit('/',1)[-1] for x in ftp.nlst(parent)]
   except Exception as e:return {'ok':False,'path':None,'steps':steps,'error':f'listing {parent}: {type(e).__name__}: {e}'}
   match=next((n for n in names if n.casefold()==wanted.casefold()),None)
   if not match:return {'ok':False,'path':None,'steps':steps+[{'parent':parent,'wanted':wanted,'available_sample':names[:20]}],'error':f'component not found: {wanted}'}
   current=(current.rstrip('/')+'/'+match) if current else '/'+match;steps.append({'parent':parent,'wanted':wanted,'actual':match})
  return {'ok':True,'path':current,'steps':steps,'error':None}
 def _aurora_paths(self,ftp,path):
  raw=str(path or '').strip().replace('\\','/')
  if not raw:return []
  parts=[x.strip() for x in raw.split(' | ') if x.strip()];out=[]
  for part in parts:
   clean='/'+part.strip('/');candidate=clean if clean.casefold().startswith('/hdd1/') else '/Hdd1'+clean
   resolved=self._resolve_case_path(ftp,candidate);out.append({'source':part,'candidate':candidate,'resolved':resolved.get('path'),'ok':resolved.get('ok'),'steps':resolved.get('steps',[]),'error':resolved.get('error')})
  return out
 def _list_dir(self,ftp,path):
  errors=[]
  try:return list(ftp.mlsd(path)),'MLSD',errors
  except Exception as e:errors.append(f'MLSD {type(e).__name__}: {e}')
  try:
   rows=[]
   for item in ftp.nlst(path):
    name=str(item).rstrip('/').rsplit('/',1)[-1]
    if name in ('','.','..'):continue
    child=path.rstrip('/')+'/'+name
    try:size=ftp.size(child);rows.append((name,{'type':'file','size':str(int(size))}))
    except Exception:rows.append((name,{'type':'unknown'}))
   return rows,'NLST',errors
  except Exception as e:return None,None,errors+[f'NLST {type(e).__name__}: {e}']
 def _size_path(self,ftp,path,seen=None):
  seen=seen or set()
  if not path or path in seen:return {'ok':False,'bytes':0,'status':'cycle','files':0,'dirs':0,'method':None,'errors':[]}
  seen.add(path)
  try:
   size=ftp.size(path)
   if size is not None:return {'ok':True,'bytes':int(size),'status':'file','files':1,'dirs':0,'method':'SIZE','errors':[]}
  except Exception:pass
  entries,method,errors=self._list_dir(ftp,path)
  if entries is None:return {'ok':False,'bytes':0,'status':'not_found_or_unlistable','files':0,'dirs':0,'method':method,'errors':errors}
  total=files=dirs=0;child_errors=[]
  for name,facts in entries:
   child=path.rstrip('/')+'/'+name;typ=(facts.get('type') or '').lower()
   if typ=='file':total+=int(facts.get('size') or 0);files+=1;continue
   result=self._size_path(ftp,child,seen);dirs+=1;total+=result['bytes'];files+=result['files'];dirs+=result['dirs']
   if not result['ok']:child_errors.extend(result['errors'] or [result['status']+' '+child])
  return {'ok':True,'bytes':total,'status':'empty' if not entries else ('partial' if child_errors else 'directory'),'files':files,'dirs':dirs,'method':method,'errors':errors+child_errors[:20]}
 def calculate_sizes(self,records,progress=None):
  results=[]
  with self.connect() as ftp:
   roots=self._root_names(ftp)
   for i,rec in enumerate(records,1):
    infos=self._aurora_paths(ftp,rec.get('path'));attempts=[];total=0;ok=True
    for info in infos:
     if not info['ok']:
      attempts.append({'source':info['source'],'candidate':info['candidate'],'resolved':None,'ok':False,'status':'case_resolve_failed','steps':info['steps'],'errors':[info['error']]});ok=False;continue
     result=self._size_path(ftp,info['resolved'],set());total+=result['bytes'];attempts.append({'source':info['source'],'candidate':info['candidate'],'resolved':info['resolved'],'ok':result['ok'],'status':result['status'],'method':result['method'],'files':result['files'],'dirs':result['dirs'],'steps':info['steps'],'errors':result['errors']});ok=ok and result['ok']
    results.append({'id':rec.get('id'),'source_path':rec.get('path'),'size_bytes':total,'ok':bool(infos) and ok,'status':'ok' if infos and ok else 'path_error','ftp_roots':roots,'attempts':attempts,'error':'; '.join(e for a in attempts for e in a.get('errors',[]))[:500] or None})
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

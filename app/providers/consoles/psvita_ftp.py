from ftplib import FTP
from io import BytesIO
import os,re,sqlite3,tempfile
from .base import ConsoleProvider,InstalledTitle
from .ps3_sfo import parse_sfo
APP_DB='/ur0:/shell/db/app.db'
VITA_ID_RE=re.compile(r'^(?:PCS[A-Z]\d{5}|NP[A-Z]{2}\d{5})$',re.I)
HOMEBREW_IDS={'ARKSPSPHB','DOOM0000','PSPEMUCFW','TFCARDPLO','UPDATBLOC','VHBB00001','VITASHELL'}
HOMEBREW_HINTS=('adrenaline','vita shell','vitashell','homebrew browser','retroarch','tf card plugin','update blocker')
MOUNTS=('/ux0:','/uma0:','/imc0:','/ur0:')
class PSVitaFTPProvider(ConsoleProvider):
 provider_name='psvita_ftp'
 def __init__(self,host,port=1337,username='anonymous',password='',database_path=APP_DB,timeout=20):
  self.host=host;self.port=int(port or 1337);self.username=username or 'anonymous';self.password=password or '';self.database_path=database_path or APP_DB;self.timeout=int(timeout or 20)
 def connect(self):
  ftp=FTP();ftp.connect(self.host,self.port,timeout=self.timeout);ftp.login(self.username,self.password);ftp.set_pasv(True);return ftp
 def _read(self,ftp,path):
  b=BytesIO();ftp.retrbinary('RETR '+path,b.write);return b.getvalue()
 def _names(self,ftp,path,errors=None):
  # FTPVita exposes RETR/CWD but may not implement NLST or MLSD. Try a classic
  # LIST data transfer only where child enumeration is unavoidable (addcont).
  previous=None
  try:
   try:previous=ftp.pwd()
   except:previous='/'
   ftp.cwd(path);lines=[];ftp.retrlines('LIST',lines.append);names=[]
   for line in lines:
    line=str(line or '').strip()
    if not line:continue
    # Unix-like FTP listings: permissions ... name. Preserve names containing spaces.
    parts=line.split(None,8);name=parts[8] if len(parts)>=9 else line.split()[-1]
    if name not in ('','.','..'):names.append(name.rstrip('/'))
   return sorted(set(names))
  except Exception as e:
   if errors is not None:errors.append(f'{path}: LIST {type(e).__name__}: {e}')
   return []
  finally:
   if previous is not None:
    try:ftp.cwd(previous)
    except:
     try:ftp.cwd('/')
     except:pass
 def _exists(self,ftp,path):
  try:self._read(ftp,path);return True
  except:return False
 def _sfo(self,ftp,path):
  try:return parse_sfo(self._read(ftp,path))
  except:return None
 def _open_db(self,data):
  fd,p=tempfile.mkstemp(suffix='.db');os.close(fd);open(p,'wb').write(data);c=sqlite3.connect(p);c.row_factory=sqlite3.Row;return c,p
 def health(self):
  out={'provider':self.provider_name,'ftp':{'ok':False},'app_db':{'ok':False},'database_path':self.database_path}
  try:
   with self.connect() as ftp:
    out['ftp']={'ok':True,'welcome':ftp.getwelcome(),'pwd':ftp.pwd()};raw=self._read(ftp,self.database_path)
   c,p=self._open_db(raw)
   try:
    tables={x[0] for x in c.execute("select name from sqlite_master where type='table'")};rows=c.execute('select count(*) from tbl_appinfo_icon').fetchone()[0] if 'tbl_appinfo_icon' in tables else 0
    out['app_db']={'ok':'tbl_appinfo_icon' in tables,'bytes':len(raw),'bubble_rows':rows,'tables':sorted(tables)}
   finally:c.close();os.unlink(p)
  except Exception as e:out['error']=f'{type(e).__name__}: {e}'
  out['ok']=out['ftp']['ok'] and out['app_db']['ok'];return out
 def scan(self):
  diag={'database_path':self.database_path,'directory_method':'app.db Title IDs + direct PARAM.SFO RETR; LIST only for DLC children','bubble_rows':0,'native_candidates':0,'games':0,'updates':0,'dlc':0,'system_ignored':0,'homebrew_ignored':0,'pspemu_ignored':0,'missing_app_sfo':0,'mounts':{},'errors':[]};items=[]
  with self.connect() as ftp:
   raw=self._read(ftp,self.database_path);c,p=self._open_db(raw)
   try:
    rows=c.execute('select titleId,title from tbl_appinfo_icon order by title').fetchall();diag['bubble_rows']=len(rows)
   finally:c.close();os.unlink(p)
   bubbles={str(r['titleId'] or '').upper():str(r['title'] or '').strip() for r in rows}
   # File system is installation truth; app.db supplies the Vita shell title/bubble inventory.
   # app.db provides known Title IDs. Probe each exact PARAM.SFO directly on
   # every mount; RETR is supported by FTPVita and avoids unsupported directory lists.
   apps={};probe_counts={mount:0 for mount in MOUNTS}
   for tid in bubbles:
    for mount in MOUNTS:
     path=f'{mount}/app/{tid}/sce_sys/param.sfo'
     if self._exists(ftp,path):apps.setdefault(tid,[]).append(mount);probe_counts[mount]+=1
   for mount in MOUNTS:
    diag['mounts'][mount.strip('/')]={'path':f'{mount}/app','method':'direct PARAM.SFO probe','app_dirs':probe_counts[mount]}
   for tid,title in bubbles.items():
    if tid.startswith('NPXS'):diag['system_ignored']+=1;continue
    if tid in HOMEBREW_IDS or any(h in title.casefold() for h in HOMEBREW_HINTS):diag['homebrew_ignored']+=1;continue
    if re.fullmatch(r'(?:SLES|SCES|SCUS|SLUS)\d{5}',tid):diag['pspemu_ignored']+=1;continue
    if not VITA_ID_RE.fullmatch(tid):continue
    installed_mounts=apps.get(tid,[])
    if not installed_mounts:continue
    diag['native_candidates']+=1
    mount=installed_mounts[0];sfo_path=f'{mount}/app/{tid}/sce_sys/param.sfo';sfo=self._sfo(ftp,sfo_path)
    if not sfo:diag['missing_app_sfo']+=1;sfo={}
    cat=str(sfo.get('CATEGORY') or '').lower();name=str(sfo.get('TITLE') or title or tid).replace('®','').replace('™','').strip();content_id=str(sfo.get('CONTENT_ID') or '').strip() or None;base_ver=str(sfo.get('APP_VER') or sfo.get('VERSION') or '').strip() or None
    if cat and cat!='gd':continue
    patch_path=f'{mount}/patch/{tid}/sce_sys/param.sfo';patch=self._sfo(ftp,patch_path);installed_ver=base_ver
    if patch and str(patch.get('CATEGORY') or '').lower()=='gp':
     installed_ver=str(patch.get('APP_VER') or patch.get('VERSION') or '').strip() or base_ver
     up=InstalledTitle('PlayStation Vita',tid,f'{name} Update',installed_ver,'Title Update','PS Vita FTP PARAM.SFO',patch_path,str(patch.get('CONTENT_ID') or content_id or '').strip() or None,'Title Update',mount.strip('/').rstrip(':')).to_dict();up['source_parent_present']=True;items.append(up);diag['updates']+=1
    game=InstalledTitle('PlayStation Vita',tid,name,installed_ver,'PS Vita Game','PS Vita app.db + PARAM.SFO',f'{mount}/app/{tid}',content_id,'PS Vita Game',mount.strip('/').rstrip(':')).to_dict();game['history_raw_json']={'psvita_metadata':{'base_version':base_ver,'installed_version':installed_ver,'category':cat or None,'content_id':content_id,'np_communication_id':sfo.get('NP_COMMUNICATION_ID'),'psp2_disp_ver':sfo.get('PSP2_DISP_VER'),'psp2_system_ver':sfo.get('PSP2_SYSTEM_VER'),'pubtoolinfo':sfo.get('PUBTOOLINFO'),'app_mount':mount.strip('/'),'shell_title':title}};items.append(game);diag['games']+=1
    # Add-on folders are child content. Each SFO exposes CATEGORY=ac, parent TITLE_ID and a unique CONTENT_ID/title.
    add_root=f'{mount}/addcont/{tid}'
    dlc_folders=self._names(ftp,add_root,None)
    if dlc_folders:diag.setdefault('addcont_parents',{})[tid]=len(dlc_folders)
    for folder in dlc_folders:
     dsfo_path=f'{add_root}/{folder}/sce_sys/param.sfo';dsfo=self._sfo(ftp,dsfo_path)
     if not dsfo or str(dsfo.get('CATEGORY') or '').lower()!='ac':continue
     parent=str(dsfo.get('TITLE_ID') or tid).upper();dtitle=str(dsfo.get('TITLE') or folder).replace('®','').replace('™','').strip();dver=str(dsfo.get('APP_VER') or dsfo.get('VERSION') or '').strip() or None;dcid=str(dsfo.get('CONTENT_ID') or '').strip() or None
     dlc=InstalledTitle('PlayStation Vita',parent,dtitle,dver,'DLC','PS Vita FTP addcont PARAM.SFO',f'{add_root}/{folder}',dcid,'DLC',mount.strip('/').rstrip(':')).to_dict();dlc['source_parent_present']=parent in bubbles;items.append(dlc);diag['dlc']+=1
  diag['items']=len(items);return {'items':items,'diagnostics':diag}

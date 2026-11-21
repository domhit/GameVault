from ftplib import FTP
from io import BytesIO
import os,re,sqlite3,tempfile
from .base import ConsoleProvider,InstalledTitle
from .ps3_sfo import parse_sfo
APP_DB='/ur0:/shell/db/app.db'
VITA_ID_RE=re.compile(r'^PCS[A-Z]\d{5}$',re.I)
PSPEMU_ID_RE=re.compile(r'^(?:SLES|SCES|SCUS|SLUS)\d{5}$',re.I)
HOMEBREW_IDS={'ARKSPSPHB','AUTOPLUG2','DOOM00000','PKGJ00000','PSPEMUCFW','SKGTLSE12','TFCARDPL0','UPDATBLOC','VHBB00001','VITADBDLD','VITASHELL'}
HOMEBREW_HINTS=('adrenaline','vita shell','vitashell','homebrew browser','autoplugin','itls-enso','pkgj','vitadb downloader','tf card plugin','update blocker')
FANPORT_IDS={'SOSR00001','SOSR00002','THEXTECH0'}
PSM_IDS={'NPOA00025'}
MOUNTS=('/ux0:','/uma0:','/imc0:','/ur0:')
RETROARCH_ROOT='/ux0:/data/retroarch/roms'
RETROARCH_SYSTEMS={
 'gb':{'platform':'Game Boy','extensions':{'.gb'}},
 'gbc':{'platform':'Game Boy Color','extensions':{'.gbc'}},
 'gba':{'platform':'Game Boy Advance','extensions':{'.gba'}},
 'nes':{'platform':'Nintendo Entertainment System','extensions':{'.nes'}},
 'snes':{'platform':'Super Nintendo','extensions':{'.sfc'}},
}
RETRO_LANG_RE=re.compile(r'^(?:[A-Z][a-z]?(?:,[A-Z][a-z]?)+|[A-Z][a-z]?)$')
def parse_retro_rom_name(filename):
 name=os.path.basename(str(filename or ''));stem,ext=os.path.splitext(name);title=stem.split(' (',1)[0].strip()
 values=[g.strip() for g in re.findall(r'\(([^()]*)\)',stem[len(title):])]
 region=values[0] if values else None;languages=[];extras=[];revision=None
 for value in values[1:]:
  if re.fullmatch(r'(?:[A-Z][a-z]?(?:,[A-Z][a-z]?)+)',value):languages=[x.strip() for x in value.split(',') if x.strip()]
  elif re.fullmatch(r'Rev(?:ision)?\s+[A-Za-z0-9.]+',value,re.I):revision=value
  else:extras.append(value)
 return {'filename':name,'title':title or stem,'extension':ext.lower(),'region':region,'languages':languages,'revision':revision,'extras':extras}
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
 def _probe(self,ftp,path):
  try:
   raw=self._read(ftp,path);return {'ok':True,'bytes':len(raw),'error':None}
  except Exception as e:return {'ok':False,'bytes':0,'error':f'{type(e).__name__}: {e}'}
 def _exists(self,ftp,path):return self._probe(ftp,path)['ok']
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
 def _list_details(self,ftp,path):
  previous=None;rows=[]
  try:
   try:previous=ftp.pwd()
   except:previous='/'
   ftp.cwd(path);lines=[];ftp.retrlines('LIST',lines.append)
   for line in lines:
    line=str(line or '').strip()
    if not line:continue
    parts=line.split(None,8);name=parts[8] if len(parts)>=9 else line.split()[-1]
    if name in ('','.','..'):continue
    is_dir=line.startswith('d');size=None
    if len(parts)>=5 and str(parts[4]).isdigit():size=int(parts[4])
    rows.append({'name':name.rstrip('/'),'is_dir':is_dir,'size':size})
   return rows,None
  except Exception as e:return [],f'{type(e).__name__}: {e}'
  finally:
   if previous is not None:
    try:ftp.cwd(previous)
    except:
     try:ftp.cwd('/')
     except:pass
 def _tree_size(self,ftp,path,seen=None):
  seen=seen or set()
  if path in seen:return {'ok':False,'bytes':0,'files':0,'dirs':0,'error':'cycle'}
  seen.add(path);rows,error=self._list_details(ftp,path)
  if error:return {'ok':False,'bytes':0,'files':0,'dirs':0,'error':error}
  total=files=dirs=0;errors=[]
  for row in rows:
   child=path.rstrip('/')+'/'+row['name']
   if row['is_dir']:
    r=self._tree_size(ftp,child,seen);total+=r['bytes'];files+=r['files'];dirs+=1+r['dirs']
    if not r['ok'] and r.get('error'):errors.append(r['error'])
   else:
    size=row['size']
    if size is None:
     try:size=ftp.size(child)
     except Exception as e:errors.append(f'{child}: {type(e).__name__}: {e}');size=0
    total+=int(size or 0);files+=1
  return {'ok':not errors or total>0,'bytes':total,'files':files,'dirs':dirs,'error':'; '.join(errors[:10]) or None}
 def calculate_sizes(self,records):
  results=[]
  with self.connect() as ftp:
   for rec in records:
    path=str(rec.get('path') or '')
    if path.lower().endswith('/sce_sys/param.sfo'):path=path[:-len('/sce_sys/param.sfo')]
    r=self._tree_size(ftp,path,set());results.append({'id':rec.get('id'),'path':path,'ok':r['ok'],'size_bytes':r['bytes'],'files':r['files'],'dirs':r['dirs'],'error':r['error']})
  return results
 def discover_retroarch(self,sample_limit=8):
  diag={'root':RETROARCH_ROOT,'systems':{},'totals':{'files':0,'parsed':0,'unexpected_extension':0,'unique_normalized_titles':0},'errors':[]};all_titles=set()
  with self.connect() as ftp:
   for folder,cfg in RETROARCH_SYSTEMS.items():
    path=f'{RETROARCH_ROOT}/{folder}';rows,error=self._list_details(ftp,path);files=[r for r in rows if not r['is_dir']]
    if error:diag['errors'].append(f'{path}: {error}')
    parsed=[];unexpected=[];regions={};revisions=protos=unlicensed=sgb=gbcompatible=0
    titles=set()
    for row in files:
     meta=parse_retro_rom_name(row['name']);meta['size_bytes']=row.get('size');meta['path']=f'{path}/{row["name"]}';ok=meta['extension'] in cfg['extensions'];meta['extension_ok']=ok
     if not ok:unexpected.append(meta['filename'])
     else:
      parsed.append(meta);titles.add(meta['title'].casefold());all_titles.add((cfg['platform'],meta['title'].casefold()));regions[meta['region'] or 'Unknown']=regions.get(meta['region'] or 'Unknown',0)+1
      values=[x.casefold() for x in ([meta['revision']] if meta['revision'] else [])+meta['extras']]
      revisions+=1 if meta['revision'] else 0;protos+=sum('proto' in x for x in values);unlicensed+=sum(x in ('unl','unlicensed') for x in values);sgb+=sum('sgb enhanced' in x for x in values);gbcompatible+=sum('gb compatible' in x for x in values)
    diag['systems'][folder]={'platform':cfg['platform'],'path':path,'files':len(files),'parsed':len(parsed),'unique_normalized_titles':len(titles),'regions':regions,'revisions':revisions,'proto':protos,'unlicensed':unlicensed,'sgb_enhanced':sgb,'gb_compatible':gbcompatible,'unexpected_extension':len(unexpected),'unexpected_examples':unexpected[:sample_limit],'examples':parsed[:sample_limit]}
    diag['totals']['files']+=len(files);diag['totals']['parsed']+=len(parsed);diag['totals']['unexpected_extension']+=len(unexpected)
  diag['totals']['unique_normalized_titles']=len(all_titles);return diag
 def scan(self):
  diag={'database_path':self.database_path,'directory_method':'app.db ID-family routing + direct PCS* PARAM.SFO RETR; LIST only for DLC children','bubble_rows':0,'native_candidates':0,'games':0,'updates':0,'dlc':0,'system_ignored':0,'homebrew_ignored':0,'pspemu_ignored':0,'missing_app_sfo':0,'mounts':{},'errors':[]};items=[]
  with self.connect() as ftp:
   raw=self._read(ftp,self.database_path);c,p=self._open_db(raw)
   try:
    rows=c.execute('select titleId,title from tbl_appinfo_icon order by title').fetchall();diag['bubble_rows']=len(rows)
   finally:c.close();os.unlink(p)
   bubbles={str(r['titleId'] or '').upper():str(r['title'] or '').strip() for r in rows}
   pspemu_present={}
   for tid,title in bubbles.items():
    if not PSPEMU_ID_RE.fullmatch(tid):continue
    path=f'/ux0:/pspemu/PSP/GAME/{tid}'
    names=self._names(ftp,path,None)
    if names:pspemu_present[tid]={'path':path,'entries':len(names),'sample':names[:5]}
   diag['pspemu_present']=pspemu_present;diag['pspemu_nonempty']=len(pspemu_present);diag['pspemu_empty_or_missing']=sum(1 for tid in bubbles if PSPEMU_ID_RE.fullmatch(tid) and tid not in pspemu_present)
   # File system is installation truth; app.db supplies the Vita shell title/bubble inventory.
   # Hardware-validated routing:
   # PCS* -> /ux0:/app/<TITLE_ID>/sce_sys/param.sfo
   # known homebrew IDs -> /imc0:/app (excluded here)
   # SLES/SCES/SCUS/SLUS -> /ux0:/pspemu/PSP/GAME/<ID> (no PARAM.SFO)
   # NPXS* -> /vs0:/app system applications (excluded here)
   apps={};native_ids=[];failed=[];unknown_ids=[]
   diag['id_classes']={'native_pcs':0,'system_npxs':0,'homebrew':0,'pspemu':0,'fanport':0,'playstation_mobile':0,'other':0}
   for tid,title in bubbles.items():
    if tid.startswith('NPXS'):diag['id_classes']['system_npxs']+=1;continue
    if tid in HOMEBREW_IDS or any(h in title.casefold() for h in HOMEBREW_HINTS):diag['id_classes']['homebrew']+=1;continue
    if PSPEMU_ID_RE.fullmatch(tid):diag['id_classes']['pspemu']+=1;continue
    if tid in FANPORT_IDS:diag['id_classes']['fanport']+=1;continue
    if tid in PSM_IDS:diag['id_classes']['playstation_mobile']+=1;continue
    if VITA_ID_RE.fullmatch(tid):
     diag['id_classes']['native_pcs']+=1;native_ids.append(tid);path=f'/ux0:/app/{tid}/sce_sys/param.sfo';probe=self._probe(ftp,path)
     if probe['ok']:apps[tid]=['/ux0:']
     elif len(failed)<20:failed.append({'title_id':tid,'title':title,'path':path,'error':probe['error']})
     continue
    diag['id_classes']['other']+=1
    if len(unknown_ids)<20:unknown_ids.append({'title_id':tid,'title':title})
   diag['native_pcs_ids']=native_ids
   diag['native_probe_success']=len(apps);diag['native_probe_failed']=len(native_ids)-len(apps);diag['native_probe_failure_examples']=failed;diag['other_id_examples']=unknown_ids
   diag['mounts']={'ux0:':{'path':'/ux0:/app','method':'app.db PCS* direct PARAM.SFO RETR','app_dirs':len(apps)},'imc0:':{'path':'/imc0:/app','method':'known homebrew IDs excluded before probe','app_dirs':0},'vs0:':{'path':'/vs0:/app','method':'NPXS system apps excluded before probe','app_dirs':0},'pspemu':{'path':'/ux0:/pspemu/PSP/GAME','method':'SLES/SCES family deferred; no PARAM.SFO expected','app_dirs':0}}
   for tid,title in bubbles.items():
    if tid.startswith('NPXS'):diag['system_ignored']+=1;continue
    if tid in HOMEBREW_IDS or any(h in title.casefold() for h in HOMEBREW_HINTS):diag['homebrew_ignored']+=1;continue
    if PSPEMU_ID_RE.fullmatch(tid):
     if tid in pspemu_present:
      item=InstalledTitle('PlayStation 1',tid,title,None,'PS1 Classic on Vita','PS Vita app.db + PSPemu',pspemu_present[tid]['path'],tid,'PS1 Classic on Vita','ux0').to_dict();item['history_raw_json']={'psvita_pspemu':{'host_platform':'PlayStation Vita','runtime':'PSPemu','app_db_title':title,**pspemu_present[tid]}};item['metadata_hint']={'media_format':'Digital','storefront':'PS1 Classic / PSPemu','host_platform':'PlayStation Vita'};items.append(item);diag.setdefault('pspemu_games',0);diag['pspemu_games']+=1
     else:diag['pspemu_ignored']+=1
     continue
    if tid in FANPORT_IDS or tid in PSM_IDS:continue
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
     patch_root=f'{mount}/patch/{tid}';up=InstalledTitle('PlayStation Vita',tid,f'{name} Update',installed_ver,'Title Update','PS Vita FTP PARAM.SFO',patch_root,str(patch.get('CONTENT_ID') or content_id or '').strip() or None,'Title Update',mount.strip('/').rstrip(':')).to_dict();up['history_raw_json']={'psvita_patch':{'param_sfo_path':patch_path,'category':'gp','content_id':str(patch.get('CONTENT_ID') or content_id or '').strip() or None}};up['source_parent_present']=True;items.append(up);diag['updates']+=1
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

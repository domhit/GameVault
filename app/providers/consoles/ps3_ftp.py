from ftplib import FTP, error_perm
from io import BytesIO
import os, re
from .base import ConsoleProvider, InstalledTitle
from .ps3_sfo import parse_sfo
from .ps3_mms import parse_metadata_db_hdd

GAME_CATEGORIES={'HG','DG','GD','1P','2P','MN','PE'}
PLAYABLE_CATEGORIES={'HG','DG','1P','2P','MN','PE'}
NON_GAME_CATEGORIES={'GD','SF'}
HOMEBREW_HINTS=('webman','multiman','irisman','apollo save','prepiso','openps3ftp','rebug toolbox','psnpatch','sen enabler','movian')
CATEGORY_NAMES={'HG':'HDD Game','DG':'Disc Game','GD':'Game Data / Patch / DLC','2P':'PS2 Classic','1P':'PS1 Classic','MN':'PSP Mini','PE':'PSP Remaster','AP':'Application'}
CATEGORY_PLATFORMS={'1P':'PlayStation 1','2P':'PlayStation 2','MN':'PlayStation Portable','PE':'PlayStation Portable'}
MMS_DB_ROOT='/dev_hdd0/mms/db'

class PS3FTPProvider(ConsoleProvider):
    provider_name='ps3_ftp'
    def __init__(self,host,port=21,username='anonymous',password='',timeout=15):
        self.host=host;self.port=int(port or 21);self.username=username or 'anonymous';self.password=password or '';self.timeout=int(timeout or 15)
    def connect(self):
        ftp=FTP();ftp.connect(self.host,self.port,timeout=self.timeout);ftp.login(self.username,self.password);ftp.set_pasv(True);return ftp
    def health(self):
        try:
            with self.connect() as ftp:
                welcome=ftp.getwelcome();pwd=ftp.pwd()
            return {'ok':True,'provider':self.provider_name,'welcome':welcome,'pwd':pwd}
        except Exception as e:return {'ok':False,'provider':self.provider_name,'error':f'{type(e).__name__}: {e}'}
    def _names(self,ftp,path):
        try:return [os.path.basename(x.rstrip('/')) for x in ftp.nlst(path) if os.path.basename(x.rstrip('/'))]
        except Exception:return []
    def _read(self,ftp,path):
        b=BytesIO();ftp.retrbinary('RETR '+path,b.write);return b.getvalue()
    def _sfo_title_diag(self,ftp,path,source):
        diag={'path':path,'found':False,'parsed':False}
        try:
            raw=self._read(ftp,path);diag['found']=True;diag['bytes']=len(raw)
            sfo=parse_sfo(raw);diag['parsed']=True
        except Exception as e:
            diag['error']=f'{type(e).__name__}: {e}'
            return None,diag
        cat=str(sfo.get('CATEGORY') or '').strip().upper()
        ident=str(sfo.get('TITLE_ID') or sfo.get('TITLEID') or '').strip().upper() or None
        title=str(sfo.get('TITLE') or ident or os.path.basename(os.path.dirname(path))).strip()
        title=re.sub(r'[®™©]+','',title).strip()
        title=re.sub(r'(?i)(filter)(2)$',r'\1 2',title)
        ver=str(sfo.get('APP_VER') or sfo.get('VERSION') or '').strip() or None
        cid=str(sfo.get('CONTENT_ID') or '').strip() or None
        install_folder=os.path.basename(os.path.dirname(path)).strip()
        package_id=install_folder.upper() if re.fullmatch(r'[A-Z0-9]{9,12}',install_folder.upper()) else None
        if package_id and package_id != ident: cid=cid or package_id
        is_homebrew=any(x in title.casefold() for x in HOMEBREW_HINTS)
        diag.update({'title':title,'title_id':ident,'package_id':package_id,'category':cat or None,'content_id':cid,'version':ver,'playable_category':cat in PLAYABLE_CATEGORIES and not is_homebrew,'homebrew_hint':is_homebrew})
        platform=CATEGORY_PLATFORMS.get(cat,'PlayStation 3')
        return InstalledTitle(platform,ident,title,ver,CATEGORY_NAMES.get(cat,cat or 'Unknown'),source,os.path.dirname(path),cid,cat,path.split('/')[1] if path.startswith('/dev_') else None),diag
    def _sfo_title(self,ftp,path,source):
        return self._sfo_title_diag(ftp,path,source)[0]
    def _size_tree(self,ftp,path,seen=None):
        seen=seen or set()
        if path in seen:return {'ok':False,'bytes':0,'files':0,'dirs':0,'error':'cycle'}
        seen.add(path)
        try:
            size=ftp.size(path)
            if size is not None:return {'ok':True,'bytes':int(size),'files':1,'dirs':0,'error':None}
        except Exception:pass
        try:names=ftp.nlst(path)
        except Exception as e:return {'ok':False,'bytes':0,'files':0,'dirs':0,'error':f'{type(e).__name__}: {e}'}
        total=files=dirs=0;errors=[]
        for raw in names:
            child=str(raw)
            if child.rstrip('/')==path.rstrip('/') or child.rstrip('/').rsplit('/',1)[-1] in ('.','..'):continue
            try:
                size=ftp.size(child)
                if size is not None:total+=int(size);files+=1;continue
            except Exception:pass
            r=self._size_tree(ftp,child,seen);total+=r['bytes'];files+=r['files'];dirs+=1+r['dirs']
            if not r['ok']:errors.append(r['error'])
        return {'ok':not errors or total>0,'bytes':total,'files':files,'dirs':dirs,'error':'; '.join(x for x in errors if x)[:400] or None}
    def calculate_sizes(self,records):
        results=[]
        with self.connect() as ftp:
            for rec in records:
                path=str(rec.get('path') or '')
                if path.startswith('/net'):
                    results.append({'id':rec.get('id'),'path':path,'ok':False,'remote':True,'bytes':0,'error':'webMAN Netzwerkpfad ist nicht über PS3 FTP messbar'});continue
                # Local ISO is a file; folder/JB content is recursively summed.
                r=self._size_tree(ftp,path,set());results.append({'id':rec.get('id'),'path':path,'ok':r['ok'],'remote':False,'bytes':r['bytes'],'files':r['files'],'dirs':r['dirs'],'error':r['error']})
        return results
    def scan(self):
        found=[]
        diagnostics={'paths':{},'errors':[],'categories':{},'platforms':{},'mms_db':{'path':MMS_DB_ROOT,'files':[],'metadata_db_hdd':{'parsed':False}}}
        with self.connect() as ftp:
            # Inventory the proprietary XMB/MMS databases for diagnostics only.
            for name in self._names(ftp,MMS_DB_ROOT):
                full=f'{MMS_DB_ROOT}/{name}'
                try:size=ftp.size(full)
                except Exception:size=None
                
                if name not in ('.','..'):diagnostics['mms_db']['files'].append({'name':name,'bytes':size})

            # dev25: read and diagnostically parse only metadata_db_hdd. plus/system are intentionally ignored.
            try:
                mms_raw=self._read(ftp,f'{MMS_DB_ROOT}/metadata_db_hdd')
                schema_raw=self._read(ftp,f'{MMS_DB_ROOT}/md_schema.scm')
                mms=parse_metadata_db_hdd(mms_raw,schema_raw)
                diagnostics['mms_db']['metadata_db_hdd']={'parsed':True,**mms['diagnostics']}
                diagnostics['mms_db']['metadata_db_hdd']['sample_records']=mms['records'][:20]
            except Exception as e:
                diagnostics['mms_db']['metadata_db_hdd']={'parsed':False,'error':f'{type(e).__name__}: {e}'}

            # Installed package content, including PS1/PS2 Classics and PSP packages.
            root='/dev_hdd0/game';names=self._names(ftp,root);diagnostics['paths'][root]=len(names)
            targets={'NPUI94240','NPUI94451','SLES54819'}
            diagnostics['hdd_game']={'folders':len(names),'sfo_parsed':0,'sfo_failed':0,'failed_sfo':[],'target_ids':{},'category_counts':{}}
            for name in names:
                sfo_path=f'{root}/{name}/PARAM.SFO'
                item,diag=self._sfo_title_diag(ftp,sfo_path,'FTP HDD')
                if diag.get('parsed'):
                    diagnostics['hdd_game']['sfo_parsed']+=1
                    cat=diag.get('category') or 'Unknown';diagnostics['hdd_game']['category_counts'][cat]=diagnostics['hdd_game']['category_counts'].get(cat,0)+1
                else:
                    diagnostics['hdd_game']['sfo_failed']+=1
                    diagnostics['hdd_game']['failed_sfo'].append({'folder':name,'path':sfo_path,'error':diag.get('error')})
                keys={name.upper(),str(diag.get('title_id') or '').upper()}
                hit=targets.intersection(keys)
                for tid in hit:diagnostics['hdd_game']['target_ids'][tid]=diag
                if item:found.append(item)
            for tid in sorted(targets):
                if tid not in diagnostics['hdd_game']['target_ids']:
                    diagnostics['hdd_game']['target_ids'][tid]={'folder_seen':tid in {x.upper() for x in names},'found':False,'parsed':False,'note':'Kein passender, geparster PARAM.SFO-Eintrag im FTP-Scan'}

            # Extracted/JB games expose PS3_GAME/PARAM.SFO.
            for root in ('/dev_hdd0/GAMES','/dev_hdd0/GAMEZ'):
                names=self._names(ftp,root);diagnostics['paths'][root]=len(names)
                for name in names:
                    item=self._sfo_title(ftp,f'{root}/{name}/PS3_GAME/PARAM.SFO','FTP Folder Game')
                    if item:found.append(item)

            # ISO names are inventory hints; webMAN can enrich IDs/versions.
            root='/dev_hdd0/PS3ISO';names=[x for x in self._names(ftp,root) if re.search(r'\.iso(?:\.\d+)?$',x,re.I)];diagnostics['paths'][root]=len(names)
            for name in names:
                title=re.sub(r'\.iso(?:\.\d+)?$','',name,flags=re.I)
                m=re.search(r'([A-Z]{4}[\-_]?\d{5})',name,re.I);ident=re.sub(r'[^A-Z0-9]','',m.group(1).upper()) if m else None
                found.append(InstalledTitle('PlayStation 3',ident,title,None,'PS3 ISO','FTP ISO',f'{root}/{name}',storage='dev_hdd0'))

        for item in found:
            diagnostics['categories'][item.category or item.content_type or 'Unknown']=diagnostics['categories'].get(item.category or item.content_type or 'Unknown',0)+1
            diagnostics['platforms'][item.platform]=diagnostics['platforms'].get(item.platform,0)+1
        diagnostics['mms_db']['files'].sort(key=lambda x:x['name'].casefold())
        return {'items':[x.to_dict() for x in found],'diagnostics':diagnostics}

from ftplib import FTP, error_perm
from io import BytesIO
import os, re
from .base import ConsoleProvider, InstalledTitle
from .ps3_sfo import parse_sfo

GAME_CATEGORIES={'HG','DG','GD'}
PLAYABLE_CATEGORIES={'HG','DG'}
CATEGORY_NAMES={'HG':'HDD Game','DG':'Disc Game','GD':'Game Data / Patch / DLC','2P':'PS2 Classics','1P':'PS1 Classics','MN':'PSP Minis','PE':'PSP Remaster','AP':'Application'}

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
    def _sfo_title(self,ftp,path,source):
        try:sfo=parse_sfo(self._read(ftp,path))
        except Exception:return None
        cat=str(sfo.get('CATEGORY') or '')
        ident=str(sfo.get('TITLE_ID') or sfo.get('TITLEID') or '').strip().upper() or None
        title=str(sfo.get('TITLE') or ident or os.path.basename(os.path.dirname(path))).strip()
        ver=str(sfo.get('APP_VER') or sfo.get('VERSION') or '').strip() or None
        cid=str(sfo.get('CONTENT_ID') or '').strip() or None
        return InstalledTitle('PlayStation 3',ident,title,ver,CATEGORY_NAMES.get(cat,cat or 'Unknown'),source,os.path.dirname(path),cid,cat,path.split('/')[1] if path.startswith('/dev_') else None)
    def scan(self):
        found=[];diagnostics={'paths':{},'errors':[]}
        with self.connect() as ftp:
            # Installed HDD content. Keep all categories for diagnostics; only playable categories auto-match as games.
            root='/dev_hdd0/game';names=self._names(ftp,root);diagnostics['paths'][root]=len(names)
            for name in names:
                item=self._sfo_title(ftp,f'{root}/{name}/PARAM.SFO','FTP HDD')
                if item:found.append(item)
            # Extracted/JB games expose PS3_GAME/PARAM.SFO.
            for root in ('/dev_hdd0/GAMES','/dev_hdd0/GAMEZ'):
                names=self._names(ftp,root);diagnostics['paths'][root]=len(names)
                for name in names:
                    item=self._sfo_title(ftp,f'{root}/{name}/PS3_GAME/PARAM.SFO','FTP Folder Game')
                    if item:found.append(item)
            # ISO names are inventory hints only in dev1; webMAN can enrich IDs/versions.
            root='/dev_hdd0/PS3ISO';names=[x for x in self._names(ftp,root) if re.search(r'\.iso(?:\.\d+)?$',x,re.I)];diagnostics['paths'][root]=len(names)
            for name in names:
                title=re.sub(r'\.iso(?:\.\d+)?$','',name,flags=re.I)
                m=re.search(r'([A-Z]{4}[\-_]?\d{5})',name,re.I);ident=re.sub(r'[^A-Z0-9]','',m.group(1).upper()) if m else None
                found.append(InstalledTitle('PlayStation 3',ident,title,None,'PS3 ISO','FTP ISO',f'{root}/{name}',storage='dev_hdd0'))
        return {'items':[x.to_dict() for x in found],'diagnostics':diagnostics}

from ftplib import FTP
from io import BytesIO
import json,re
from .base import ConsoleProvider, InstalledTitle
DEFAULT_EXPORT_PATH='/fs/vol/external01/wiiu/apps/GameVault-WiiU-Exporter/wii_usbloadergx.json'
GAME_ID_RE=re.compile(r'^[A-Z0-9]{6}$')

class WiiGameVaultProvider(ConsoleProvider):
    provider_name='wii_gamevault'
    def __init__(self,host,port=21,username='anonymous',password='',database_path=DEFAULT_EXPORT_PATH,timeout=20):
        self.host=host;self.port=int(port or 21);self.username=username or 'anonymous';self.password=password or '';self.database_path=database_path or DEFAULT_EXPORT_PATH;self.timeout=int(timeout or 20)
    def connect(self):
        ftp=FTP();ftp.connect(self.host,self.port,timeout=self.timeout);ftp.login(self.username,self.password);ftp.set_pasv(True);return ftp
    def _read(self,ftp):
        b=BytesIO();ftp.retrbinary('RETR '+self.database_path,b.write);return b.getvalue()
    def _doc(self,raw):
        d=json.loads(raw.decode('utf-8-sig'))
        if int(d.get('schemaVersion') or 0)!=1:raise ValueError(f"Unsupported schemaVersion: {d.get('schemaVersion')}")
        if str(d.get('platform') or '').upper()!='WII':raise ValueError('Not a Wii export')
        if not isinstance(d.get('games'),list):raise ValueError('games array missing')
        return d
    def health(self):
        out={'provider':self.provider_name,'database_path':self.database_path,'ftp':{'ok':False},'export':{'ok':False}}
        try:
            with self.connect() as ftp:out['ftp']={'ok':True,'welcome':ftp.getwelcome(),'pwd':ftp.pwd()};raw=self._read(ftp)
            d=self._doc(raw);out['export']={'ok':True,'bytes':len(raw),'schema_version':d.get('schemaVersion'),'exporter_version':d.get('exporterVersion'),'source':d.get('source'),'game_count_declared':d.get('gameCount'),'game_count':len(d['games']),'cache_version':d.get('cacheVersion'),'cache_found':d.get('cacheFound')};out['ok']=True
        except Exception as e:out['error']=f'{type(e).__name__}: {e}';out['ok']=False
        return out
    def scan(self):
        with self.connect() as ftp:raw=self._read(ftp)
        d=self._doc(raw);items=[];diag={'database_path':self.database_path,'schema_version':d.get('schemaVersion'),'exporter_version':d.get('exporterVersion'),'source':d.get('source'),'cache_found':d.get('cacheFound'),'cache_version':d.get('cacheVersion'),'source_rows':len(d['games']),'valid_games':0,'invalid_games':0,'wbfs':0,'iso':0,'other_format':0,'with_play_count':0,'invalid_examples':[]}
        seen=set()
        for row in d['games']:
            gid=str(row.get('gameId') or '').upper().strip();title=' '.join(str(row.get('title') or gid).split());path=str(row.get('path') or '');fmt=str(row.get('format') or 'UNKNOWN').upper();play=row.get('playCount')
            if not GAME_ID_RE.fullmatch(gid) or not title or not path:
                diag['invalid_games']+=1
                if len(diag['invalid_examples'])<10:diag['invalid_examples'].append({'gameId':gid,'title':title,'path':path})
                continue
            if gid in seen:continue
            seen.add(gid);diag['valid_games']+=1
            if fmt=='WBFS':diag['wbfs']+=1
            elif fmt=='ISO':diag['iso']+=1
            else:diag['other_format']+=1
            if play is not None and int(play or 0)>0:diag['with_play_count']+=1
            item=InstalledTitle('Wii',gid,title,None,'Wii Game','GameVault Wii U Exporter / USB Loader GX',path,gid,'Wii Game','usb1').to_dict()
            item['play_count']=int(play or 0) if play is not None else None;item['history_source']='USB Loader GX GXGameStatistics.cfg' if item['play_count'] is not None else None
            item['history_raw_json']={'usbloadergx':{'format':fmt,'cache_version':d.get('cacheVersion'),'cache_path':d.get('cachePath'),'statistics_path':d.get('statisticsPath')}}
            item['metadata_hint']={'media_format':fmt}
            items.append(item)
        diag['unique_game_ids']=len(seen);return {'items':items,'diagnostics':diag}

from ftplib import FTP
from io import BytesIO
import json
import re
from .base import ConsoleProvider, InstalledTitle

DEFAULT_EXPORT_PATH='/fs/vol/external01/wiiu/apps/GameVault-WiiU-Exporter/installed_titles.json'
TITLE_ID_RE=re.compile(r'^[0-9A-F]{16}$')
KIND_CATEGORY={'GAME':'Wii U Game','UPDATE':'Title Update','DLC':'DLC'}


def normalize_title_id(value):
    value=re.sub(r'[^0-9A-F]','',str(value or '').upper())
    return value if TITLE_ID_RE.fullmatch(value) else None


def parent_title_id(title_id):
    title_id=normalize_title_id(title_id)
    if not title_id:return None
    return '00050000'+title_id[8:]


class WiiUGameVaultProvider(ConsoleProvider):
    provider_name='wiiu_gamevault'
    def __init__(self,host,port=21,username='anonymous',password='',database_path=DEFAULT_EXPORT_PATH,timeout=20):
        self.host=host;self.port=int(port or 21);self.username=username or 'anonymous';self.password=password or ''
        self.database_path=database_path or DEFAULT_EXPORT_PATH;self.timeout=int(timeout or 20)
    def connect(self):
        ftp=FTP();ftp.connect(self.host,self.port,timeout=self.timeout);ftp.login(self.username,self.password);ftp.set_pasv(True);return ftp
    def _read(self,ftp):
        data=BytesIO();ftp.retrbinary('RETR '+self.database_path,data.write);return data.getvalue()
    def _document(self,raw):
        doc=json.loads(raw.decode('utf-8-sig'))
        if not isinstance(doc,dict):raise ValueError('Export root must be an object')
        if int(doc.get('schemaVersion') or 0)!=1:raise ValueError(f"Unsupported schemaVersion: {doc.get('schemaVersion')}")
        if str(doc.get('platform') or '').upper()!='WII_U':raise ValueError('Not a Wii U export')
        if not isinstance(doc.get('titles'),list):raise ValueError('titles array missing')
        return doc
    def health(self):
        out={'provider':self.provider_name,'database_path':self.database_path,'ftp':{'ok':False},'export':{'ok':False}}
        try:
            with self.connect() as ftp:
                out['ftp']={'ok':True,'welcome':ftp.getwelcome(),'pwd':ftp.pwd()};raw=self._read(ftp)
            doc=self._document(raw);titles=doc['titles']
            out['export']={'ok':True,'bytes':len(raw),'schema_version':doc.get('schemaVersion'),'exporter':doc.get('exporter'),'exporter_version':doc.get('exporterVersion'),'generated_at':doc.get('generatedAt'),'title_count_declared':doc.get('titleCount'),'title_count':len(titles)}
            out['ok']=True
        except Exception as e:
            out['error']=f'{type(e).__name__}: {e}';out['ok']=False
        return out
    def scan(self):
        with self.connect() as ftp:raw=self._read(ftp)
        doc=self._document(raw);rows=doc['titles'];items=[]
        diag={'database_path':self.database_path,'schema_version':doc.get('schemaVersion'),'exporter':doc.get('exporter'),'exporter_version':doc.get('exporterVersion'),'generated_at':doc.get('generatedAt'),'declared_title_count':doc.get('titleCount'),'source_rows':len(rows),'valid_rows':0,'invalid_rows':0,'games':0,'updates':0,'dlc':0,'system_or_other_ignored':0,'storage':{},'duplicate_installations':0,'unique_title_ids':0,'parent_groups':0,'orphan_children':0,'invalid_examples':[]}
        valid=[];seen_keys=set();all_ids=set()
        for row in rows:
            tid=normalize_title_id(row.get('titleId'));kind=str(row.get('kind') or '').upper();storage=str(row.get('storage') or 'UNKNOWN').upper()
            if not tid or kind not in ('GAME','UPDATE','DLC'):
                if kind not in ('GAME','UPDATE','DLC'):diag['system_or_other_ignored']+=1
                else:diag['invalid_rows']+=1
                if len(diag['invalid_examples'])<10:diag['invalid_examples'].append({'titleId':row.get('titleId'),'kind':kind,'name':row.get('name')})
                continue
            diag['valid_rows']+=1;diag['storage'][storage]=diag['storage'].get(storage,0)+1;all_ids.add(tid)
            install_key=(tid,storage,str(row.get('path') or ''))
            if install_key in seen_keys:diag['duplicate_installations']+=1
            seen_keys.add(install_key);valid.append((row,tid,kind,storage))
        diag['unique_title_ids']=len(all_ids)
        parent_ids={tid for _,tid,kind,_ in valid if kind=='GAME'};diag['parent_groups']=len(parent_ids)
        for row,tid,kind,storage in valid:
            parent_id=parent_title_id(tid);title=re.sub(r'\s+',' ',str(row.get('name') or tid)).strip();version=row.get('installedVersion')
            metadata={'product_code':row.get('productCode'),'publisher':row.get('publisher'),'company_code':row.get('companyCode'),'content_platform':row.get('contentPlatform'),'region':row.get('region'),'xml_title_version':row.get('xmlTitleVersion'),'drc_use':row.get('drcUse'),'network_use':row.get('networkUse'),'online_account_use':row.get('onlineAccountUse'),'group_id':row.get('groupId'),'app_type':row.get('appType'),'os_version':row.get('osVersion'),'sdk_version':row.get('sdkVersion'),'icon_path':row.get('iconPath'),'raw_title_id':tid}
            category=KIND_CATEGORY[kind]
            item=InstalledTitle('Wii U',parent_id,title,str(version) if version is not None else None,category,'GameVault Wii U Exporter',str(row.get('path') or ''),tid,category,storage).to_dict()
            item['history_raw_json']={'wiiu_metadata':metadata,'exporter_version':doc.get('exporterVersion'),'generated_at':doc.get('generatedAt')}
            item['metadata_hint']={'publisher':row.get('publisher'),'region':row.get('region'),'product_code':row.get('productCode')}
            item['source_parent_present']=parent_id in parent_ids
            items.append(item)
            if kind=='GAME':diag['games']+=1
            elif kind=='UPDATE':diag['updates']+=1
            else:diag['dlc']+=1
            if kind!='GAME' and parent_id not in parent_ids:diag['orphan_children']+=1
        return {'items':items,'diagnostics':diag}

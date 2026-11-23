from ftplib import FTP
from io import BytesIO
import json, re
from .base import ConsoleProvider, InstalledTitle

DEFAULT_EXPORT_PATH='/3ds/GameVault-3DS-Exporter/installed_titles.json'
TITLE_ID_RE=re.compile(r'^[0-9A-F]{16}$')
KIND_CATEGORY={'GAME':'Nintendo 3DS Game','UPDATE':'Title Update','DLC':'DLC'}
HOMEBREW_HINTS=(
    'gamevault 3ds exporter','universal-updater','ghosteshop','3hs','ftpd pro',
    'homebrew launcher','fbi','checkpoint','anemone3ds'
)

def normalize_title_id(value):
    value=re.sub(r'[^0-9A-F]','',str(value or '').upper())
    return value if TITLE_ID_RE.fullmatch(value) else None

def clean_text(value):
    return ' '.join(str(value or '').replace('®','').replace('™','').split())

def display_title(row, fallback):
    short=clean_text(row.get('name'))
    long=clean_text(row.get('longDescription'))
    if long and (not short or short.endswith('...') or short.endswith('…') or len(long)>len(short)+5):
        return long
    return short or long or fallback

class Nintendo3DSGameVaultProvider(ConsoleProvider):
    provider_name='n3ds_gamevault'
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
        if int(doc.get('schemaVersion') or 0)!=3:raise ValueError(f"Unsupported schemaVersion: {doc.get('schemaVersion')}")
        if str(doc.get('platform') or '').upper()!='NINTENDO_3DS':raise ValueError('Not a Nintendo 3DS export')
        if not isinstance(doc.get('titles'),list):raise ValueError('titles array missing')
        return doc
    def health(self):
        out={'provider':self.provider_name,'database_path':self.database_path,'ftp':{'ok':False},'export':{'ok':False}}
        try:
            with self.connect() as ftp:
                out['ftp']={'ok':True,'welcome':ftp.getwelcome(),'pwd':ftp.pwd()};raw=self._read(ftp)
            doc=self._document(raw);titles=doc['titles']
            out['export']={'ok':True,'bytes':len(raw),'schema_version':doc.get('schemaVersion'),'exporter':doc.get('exporter'),'exporter_version':doc.get('exporterVersion'),'title_count_declared':doc.get('titleCount'),'title_count':len(titles),'media':doc.get('media'),'smdh':doc.get('smdh')};out['ok']=True
        except Exception as e:out['error']=f'{type(e).__name__}: {e}';out['ok']=False
        return out
    def scan(self):
        with self.connect() as ftp:raw=self._read(ftp)
        doc=self._document(raw);rows=doc['titles'];items=[]
        diag={'database_path':self.database_path,'schema_version':doc.get('schemaVersion'),'exporter':doc.get('exporter'),'exporter_version':doc.get('exporterVersion'),'declared_title_count':doc.get('titleCount'),'source_rows':len(rows),'games':0,'updates':0,'dlc':0,'system_ignored':0,'twl_ignored':0,'homebrew_ignored':0,'invalid_rows':0,'duplicate_rows':0,'orphan_children':0,'storage':{},'smdh':doc.get('smdh'),'media':doc.get('media'),'errors':doc.get('errors') or [],'invalid_examples':[]}
        parent_ids={normalize_title_id(r.get('titleId')) for r in rows if str(r.get('kind') or '').upper()=='GAME'};seen=set()
        for row in rows:
            tid=normalize_title_id(row.get('titleId'));parent=normalize_title_id(row.get('parentTitleId')) or tid;kind=str(row.get('kind') or '').upper();media=str(row.get('mediaType') or 'UNKNOWN').upper()
            if kind=='SYSTEM':diag['system_ignored']+=1;continue
            if kind=='DSIWARE_OR_TWL':diag['twl_ignored']+=1;continue
            if not tid or not parent or kind not in KIND_CATEGORY:
                diag['invalid_rows']+=1
                if len(diag['invalid_examples'])<10:diag['invalid_examples'].append({'titleId':row.get('titleId'),'kind':kind,'name':row.get('name')})
                continue
            title=display_title(row,tid)
            if kind=='GAME' and any(h in (clean_text(row.get('name'))+' '+clean_text(row.get('longDescription'))).casefold() for h in HOMEBREW_HINTS):diag['homebrew_ignored']+=1;continue
            key=(tid,media)
            if key in seen:diag['duplicate_rows']+=1;continue
            seen.add(key);diag['storage'][media]=diag['storage'].get(media,0)+1
            category=KIND_CATEGORY[kind];version=row.get('version');path=f'{media}:{tid}'
            item=InstalledTitle('Nintendo 3DS',parent,title,str(version) if version is not None else None,category,'GameVault Nintendo 3DS Exporter',path,tid,category,media).to_dict()
            item['installed_size_bytes']=int(row.get('installedSizeBytes')) if row.get('installedSizeBytes') is not None else None
            item['source_parent_present']=parent in parent_ids
            item['history_raw_json']={'n3ds_metadata':{'raw_title_id':tid,'parent_title_id':parent,'kind':kind,'subtype':row.get('subtype'),'title_category':row.get('titleCategory'),'unique_id':row.get('uniqueId'),'product_code':row.get('productCode'),'name':row.get('name'),'long_description':row.get('longDescription'),'publisher':row.get('publisher'),'region':row.get('region'),'region_mask':row.get('regionMask'),'smdh_available':row.get('smdhAvailable'),'smdh_result':row.get('smdhResult'),'media_type':media},'exporter_version':doc.get('exporterVersion')}
            item['metadata_hint']={'publisher':row.get('publisher'),'region':row.get('region'),'description':clean_text(row.get('longDescription'))}
            items.append(item)
            if kind=='GAME':diag['games']+=1
            elif kind=='UPDATE':diag['updates']+=1
            else:diag['dlc']+=1
            if kind!='GAME' and parent not in parent_ids:diag['orphan_children']+=1
        diag['unique_items']=len(items);return {'items':items,'diagnostics':diag}

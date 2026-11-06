import re, requests
from urllib.parse import urljoin, unquote, unquote_plus
from bs4 import BeautifulSoup
from .base import ConsoleProvider, InstalledTitle

CONTROL_TITLES={'UNMOUNT GAME','EJECT DISC','REFRESH XML','REFRESH GAMES'}

def normalize_identifier(v):
    s=re.sub(r'[^A-Z0-9]','',str(v or '').upper())
    return s if re.fullmatch(r'[A-Z]{4}\d{5}',s) else None

def canonical_path(href):
    p=unquote(href or '')
    p=re.sub(r'^https?://[^/]+','',p,flags=re.I)
    if p.startswith('/mount.ps3/'):
        p=p[len('/mount.ps3'):]
    p=p.replace('//','/')
    return p

def storage_from_path(path):
    p=(path or '').lstrip('/')
    root=p.split('/',1)[0] if p else None
    labels={'dev_hdd0':'Interne HDD','net0':'Netzwerk net0','net1':'Netzwerk net1','net2':'Netzwerk net2','dev_ntfs':'NTFS'}
    if root and root.startswith('dev_usb'):
        return 'USB '+root.replace('dev_usb','')
    return labels.get(root,root)

def clean_title(label,path):
    label=' '.join(unquote_plus(label or '').split())
    if label.upper() in CONTROL_TITLES:return None
    if label and not re.search(r'\.iso(?:\.\d+)?$',label,re.I):
        return label
    base=(path or '').rsplit('/',1)[-1]
    base=re.sub(r'\.iso(?:\.\d+)?$','',base,flags=re.I)
    base=re.sub(r'\s*\[[A-Z]{4}[-_]?\d{5}\]\s*$','',base,flags=re.I)
    return ' '.join(unquote_plus(base).replace('_',' ').split()) or None

class PS3WebManProvider(ConsoleProvider):
    provider_name='ps3_webman'
    def __init__(self,base_url,timeout=15):
        self.base_url=(base_url or '').rstrip('/')+'/';self.timeout=int(timeout or 15);self.headers={'User-Agent':'GameVault/1.1.0-dev3'}
    def health(self):
        try:
            r=requests.get(urljoin(self.base_url,'index.ps3'),headers=self.headers,timeout=self.timeout)
            return {'ok':r.ok,'provider':self.provider_name,'status_code':r.status_code,'url':r.url}
        except Exception as e:return {'ok':False,'provider':self.provider_name,'error':f'{type(e).__name__}: {e}'}
    def scan(self):
        raw=[];errors=[]
        for endpoint in ('index.ps3','games.ps3'):
            try:
                r=requests.get(urljoin(self.base_url,endpoint),headers=self.headers,timeout=self.timeout);r.raise_for_status();soup=BeautifulSoup(r.text,'html.parser')
                for a in soup.find_all('a',href=True):
                    href=unquote(a.get('href',''));label=' '.join(a.get_text(' ',strip=True).split())
                    up=href.upper()
                    if not any(x in up for x in ('/PS3ISO/','/GAMES/','/GAMEZ/','MOUNT.PS3')):continue
                    if '/UNMOUNT' in up or label.upper() in CONTROL_TITLES:continue
                    path=canonical_path(href)
                    text=f'{label} {path}';m=re.search(r'\b([A-Z]{4}[-_]?\d{5})\b',text,re.I);ident=normalize_identifier(m.group(1)) if m else None
                    title=clean_title(label,path)
                    if not title:continue
                    vm=re.search(r'\b(?:APP[_ ]?VER|VER(?:SION)?|V)\s*[: ]\s*(\d+(?:\.\d+)+)',text,re.I);ver=vm.group(1) if vm else None
                    raw.append({'platform':'PlayStation 3','identifier':ident,'title':title,'installed_version':ver,'content_type':'webMAN Game','source':'webMAN','path':path,'content_id':None,'category':None,'storage':storage_from_path(path),'endpoint':endpoint,'mount_link':href.startswith('/mount.ps3/')})
            except Exception as e:errors.append(f'{endpoint}: {type(e).__name__}: {e}')
        # webMAN exposes both display and /mount.ps3 links. Collapse by TitleID, preferring display title and canonical non-mount path.
        merged={}
        for item in raw:
            k=item['identifier'] or (re.sub(r'[^a-z0-9]','',item['title'].casefold()),item['path'])
            old=merged.get(k)
            if not old:merged[k]=item;continue
            if old.get('mount_link') and not item.get('mount_link'):old,item=item,old;merged[k]=old
            for f in ('identifier','installed_version','content_id','category','storage'):
                if not old.get(f) and item.get(f):old[f]=item[f]
            if (not old.get('title') or re.search(r'\.iso$',old['title'],re.I)) and item.get('title'):old['title']=item['title']
            if old.get('path','').startswith('/mount.ps3/') and not item.get('path','').startswith('/mount.ps3/'):old['path']=item['path']
        items=[]
        for item in merged.values():
            item.pop('endpoint',None);item.pop('mount_link',None);items.append(InstalledTitle(**item).to_dict())
        return {'items':items,'diagnostics':{'endpoints':['index.ps3','games.ps3'],'raw_links':len(raw),'deduplicated_items':len(items),'errors':errors}}

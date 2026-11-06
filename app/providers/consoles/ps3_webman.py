import re, requests
from urllib.parse import urljoin, unquote
from bs4 import BeautifulSoup
from .base import ConsoleProvider, InstalledTitle

class PS3WebManProvider(ConsoleProvider):
    provider_name='ps3_webman'
    def __init__(self,base_url,timeout=15):
        self.base_url=(base_url or '').rstrip('/')+'/';self.timeout=int(timeout or 15);self.headers={'User-Agent':'GameVault/1.1.0-dev1'}
    def health(self):
        try:
            r=requests.get(urljoin(self.base_url,'index.ps3'),headers=self.headers,timeout=self.timeout)
            return {'ok':r.ok,'provider':self.provider_name,'status_code':r.status_code,'url':r.url}
        except Exception as e:return {'ok':False,'provider':self.provider_name,'error':f'{type(e).__name__}: {e}'}
    def scan(self):
        items=[];seen=set();errors=[]
        for endpoint in ('index.ps3','games.ps3'):
            try:
                r=requests.get(urljoin(self.base_url,endpoint),headers=self.headers,timeout=self.timeout);r.raise_for_status();soup=BeautifulSoup(r.text,'html.parser')
                for a in soup.find_all('a',href=True):
                    href=unquote(a.get('href',''));label=' '.join(a.get_text(' ',strip=True).split())
                    if not any(x in href.upper() for x in ('/PS3ISO/','/GAMES/','/GAMEZ/','MOUNT.PS3')):continue
                    text=f'{label} {href}';m=re.search(r'\b([A-Z]{4}[\-_]?\d{5})\b',text,re.I);ident=re.sub(r'[^A-Z0-9]','',m.group(1).upper()) if m else None
                    vm=re.search(r'\b(?:VER(?:SION)?\s*[: ]\s*|V)(\d+(?:\.\d+)+)',text,re.I);ver=vm.group(1) if vm else None
                    title=label or href.rsplit('/',1)[-1];key=(ident,title,href)
                    if key in seen:continue
                    seen.add(key);items.append(InstalledTitle('PlayStation 3',ident,title,ver,'webMAN Game','webMAN',href,storage='webMAN').to_dict())
            except Exception as e:errors.append(f'{endpoint}: {type(e).__name__}: {e}')
        return {'items':items,'diagnostics':{'endpoints':['index.ps3','games.ps3'],'errors':errors}}

import ast, os, re, requests
from bs4 import BeautifulSoup
TIMEOUT=int(os.getenv('METADATA_TIMEOUT','20'))
BASE='https://orbispatches.com'
UA={'User-Agent':'GameVault/0.9.0 (+https://github.com/domhit/GameVault)'}
def normalize_cusa(v):
 s=re.sub(r'[^A-Z0-9]','',str(v or '').upper())
 return s if re.fullmatch(r'CUSA\d{5}',s) else None
def resolve(cusa):
 cusa=normalize_cusa(cusa)
 if not cusa:return {'ok':False,'error':'invalid CUSA'}
 r=requests.get(f'{BASE}/{cusa}',headers=UA,timeout=TIMEOUT);r.raise_for_status()
 soup=BeautifulSoup(r.text,'html.parser');node=soup.select_one('#dynpatch')
 title=(soup.select_one('h1').get_text(' ',strip=True) if soup.select_one('h1') else None)
 if title:title=re.sub(r'\s*[-|–]\s*ORBISPatches.*$','',title,flags=re.I).strip()
 if not node or not node.get('data-loadparams'):return {'ok':False,'cusa':cusa,'title':title,'error':'load parameters not found'}
 params=ast.literal_eval(node['data-loadparams'])
 pr=requests.post(f'{BASE}/api/internal/loadpatches',json=params,headers=UA,timeout=TIMEOUT);pr.raise_for_status();data=pr.json()
 patches=data.get('patches') or []
 latest=next((p for p in patches if p.get('is_latest')),patches[-1] if patches else None)
 return {'ok':True,'cusa':cusa,'title':title or data.get('title'),'latest':latest,'patch_count':len(patches),'source':'ORBISPatches'}
def health():
 try:
  r=requests.get(BASE,headers=UA,timeout=TIMEOUT);return {'ok':r.ok,'status_code':r.status_code,'source':'ORBISPatches'}
 except Exception as e:return {'ok':False,'error':str(e)[:240],'source':'ORBISPatches'}

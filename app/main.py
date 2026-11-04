from __future__ import annotations
import html, os, re, tempfile, xml.etree.ElementTree as ET
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy import create_engine, String, Text, Float, Integer, Boolean, ForeignKey, select, func, delete
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, Session
from openpyxl import load_workbook

DB=os.getenv("DATABASE_URL","sqlite:////data/gamevault.db")
engine=create_engine(DB,connect_args={"check_same_thread":False} if DB.startswith("sqlite") else {})
class Base(DeclarativeBase): pass
class Game(Base):
 __tablename__='games'
 id:Mapped[int]=mapped_column(primary_key=True)
 gc_id:Mapped[Optional[str]]=mapped_column(String(40),unique=True,nullable=True)
 platform:Mapped[str]=mapped_column(String(80),index=True)
 title:Mapped[str]=mapped_column(String(300),index=True)
 title_id:Mapped[Optional[str]]=mapped_column(String(40),index=True,nullable=True)
 publisher:Mapped[Optional[str]]=mapped_column(String(200),nullable=True)
 developer:Mapped[Optional[str]]=mapped_column(String(200),nullable=True)
 genres:Mapped[Optional[str]]=mapped_column(String(300),nullable=True)
 release_date:Mapped[Optional[str]]=mapped_column(String(30),nullable=True)
 completed:Mapped[bool]=mapped_column(Boolean,default=False)
 collection_status:Mapped[Optional[str]]=mapped_column(String(80),nullable=True)
 completeness:Mapped[Optional[str]]=mapped_column(String(80),nullable=True)
 current_value:Mapped[Optional[str]]=mapped_column(String(50),nullable=True)
 description:Mapped[Optional[str]]=mapped_column(Text,nullable=True)
 cover_source:Mapped[Optional[str]]=mapped_column(Text,nullable=True)
 pricecharting_url:Mapped[Optional[str]]=mapped_column(Text,nullable=True)
 packages:Mapped[list['Package']]=relationship(back_populates='game',cascade='all,delete-orphan')
class Package(Base):
 __tablename__='packages'
 id:Mapped[int]=mapped_column(primary_key=True)
 filename:Mapped[str]=mapped_column(String(600),unique=True,index=True)
 game_id:Mapped[Optional[int]]=mapped_column(ForeignKey('games.id'),nullable=True,index=True)
 title_id:Mapped[Optional[str]]=mapped_column(String(40),index=True,nullable=True)
 name:Mapped[Optional[str]]=mapped_column(String(400),nullable=True)
 version:Mapped[Optional[str]]=mapped_column(String(40),nullable=True)
 pkg_version:Mapped[Optional[str]]=mapped_column(String(40),nullable=True)
 newest_patch:Mapped[Optional[str]]=mapped_column(String(40),nullable=True)
 decision:Mapped[Optional[str]]=mapped_column(String(80),nullable=True)
 location:Mapped[Optional[str]]=mapped_column(String(80),nullable=True)
 category:Mapped[Optional[str]]=mapped_column(String(40),nullable=True)
 size_gb:Mapped[Optional[float]]=mapped_column(Float,nullable=True)
 game:Mapped[Optional[Game]]=relationship(back_populates='packages')
Base.metadata.create_all(engine)
app=FastAPI(title='GameVault',version='0.1.0')

def txt(e,path):
 n=e.find(path); return (n.text or '').strip() if n is not None and n.text else None
def disp(e,path): return txt(e,path+'/displayname') or txt(e,path)
def norm_tid(v):
 if not v:return None
 s=re.sub(r'[^A-Za-z0-9]','',str(v)).upper()
 m=re.fullmatch(r'CUSA(\d+)',s)
 return 'CUSA'+m.group(1).zfill(5) if m else s
def clean_pkg_title(v):
 if not v:return ''
 v=re.sub(r'\s*\[(Game|Update)\]\s*$', '', str(v), flags=re.I)
 return v.replace('_',' ').strip()
def key(v): return re.sub(r'[^a-z0-9]','',clean_pkg_title(v).casefold())
def nfloat(v):
 if v in (None,''):return None
 if isinstance(v,(int,float)):return float(v)
 try:return float(str(v).replace('.','').replace(',','.'))
 except:return None

def import_xml(path):
 root=ET.parse(path).getroot(); nodes=root.findall('./gamelist/game'); added=updated=0
 with Session(engine) as db:
  for e in nodes:
   gc=txt(e,'id'); g=db.scalar(select(Game).where(Game.gc_id==gc))
   vals=dict(platform=disp(e,'platform') or 'Unbekannt',title=txt(e,'title') or 'Ohne Titel',publisher=disp(e,'publisher'),developer=disp(e,'developer'),genres=', '.join(x.text.strip() for x in e.findall('./genres/genre/displayname') if x.text),release_date=txt(e,'releasedate/date'),completed=(e.find('completed') is not None and e.find('completed').attrib.get('boolvalue')=='1'),collection_status=txt(e,'collectionstatus'),completeness=txt(e,'completeness'),current_value=txt(e,'currentvalue'),description=html.unescape(txt(e,'description') or ''),cover_source=txt(e,'coverfront'),pricecharting_url=txt(e,'pricechartingurl'))
   if not g:g=Game(gc_id=gc,**vals);db.add(g);added+=1
   else:
    for k2,v in vals.items():setattr(g,k2,v)
    updated+=1
  db.commit()
 return {'rows':len(nodes),'added':added,'updated':updated}

def import_xlsx(path):
 wb=load_workbook(path,data_only=True,read_only=True); ws=wb[wb.sheetnames[0]]; rows=ws.iter_rows(values_only=True); headers=[str(x).strip() if x else '' for x in next(rows)]; idx={n:i for i,n in enumerate(headers)}
 added=updated=stubs=0
 with Session(engine) as db:
  games=db.scalars(select(Game).where(Game.platform=='PlayStation 4')).all(); byname={key(g.title):g for g in games}
  for r in rows:
   def get(n): return r[idx[n]] if n in idx and idx[n]<len(r) else None
   fn=get('Filename')
   if not fn:continue
   tid=norm_tid(get('Title ID')); nm=clean_pkg_title(get('Name'))
   pkg=db.scalar(select(Package).where(Package.filename==str(fn)))
   game=None
   if pkg and pkg.game:game=pkg.game
   if not game and nm:game=byname.get(key(nm))
   if not game and tid:
    game=db.scalar(select(Game).where(Game.title_id==tid,Game.platform=='PlayStation 4'))
   if not game and (get('Category') in ('Game','Patch')):
    base=nm or re.sub(r'^\[[^]]+\]\s*|\s*\[[^]]+\].*$','',str(fn)).strip()
    game=Game(platform='PlayStation 4',title=base,title_id=tid);db.add(game);db.flush();byname[key(base)]=game;stubs+=1
   vals=dict(game_id=game.id if game else None,title_id=tid,name=nm or None,version=str(get('Version')) if get('Version') is not None else None,pkg_version=str(get('Version pkg')) if get('Version pkg') is not None else None,newest_patch=str(get('Newest Patch')) if get('Newest Patch') is not None else None,decision=str(get('Entscheidung')) if get('Entscheidung') is not None else None,location=str(get('Location')) if get('Location') is not None else None,category=str(get('Category')) if get('Category') is not None else None,size_gb=nfloat(get('Size (GB)')))
   if not pkg: pkg=Package(filename=str(fn),**vals);db.add(pkg);added+=1
   else:
    for k2,v in vals.items():setattr(pkg,k2,v)
    updated+=1
  db.commit()
 return {'added':added,'updated':updated,'stubs':stubs}

@app.get('/api/games')
def games(q:str='',platform:str=''):
 with Session(engine) as db:
  st=select(Game).order_by(Game.title)
  if platform:st=st.where(Game.platform==platform)
  if q:st=st.where(Game.title.ilike(f'%{q}%'))
  gs=db.scalars(st).all()
  return [serialize(g) for g in gs]
def serialize(g):
 return {'id':g.id,'title':g.title,'platform':g.platform,'title_id':g.title_id,'publisher':g.publisher,'developer':g.developer,'genres':g.genres,'release_date':g.release_date,'completed':g.completed,'collection_status':g.collection_status,'completeness':g.completeness,'current_value':g.current_value,'description':g.description,'cover_source':g.cover_source,'pricecharting_url':g.pricecharting_url,'packages':[{'filename':p.filename,'title_id':p.title_id,'name':p.name,'version':p.version,'pkg_version':p.pkg_version,'newest_patch':p.newest_patch,'decision':p.decision,'location':p.location,'category':p.category,'size_gb':p.size_gb} for p in g.packages]}
@app.get('/api/stats')
def stats():
 with Session(engine) as db:
  return {'games':db.scalar(select(func.count(Game.id))) or 0,'packages':db.scalar(select(func.count(Package.id))) or 0,'size_gb':round(db.scalar(select(func.coalesce(func.sum(Package.size_gb),0))) or 0,3),'platforms':dict(db.execute(select(Game.platform,func.count(Game.id)).group_by(Game.platform)).all())}
@app.post('/api/import/gamecollector')
def gc(file:UploadFile=File(...)):
 with tempfile.NamedTemporaryFile(suffix='.xml',delete=False) as f:f.write(file.file.read());p=f.name
 try:return import_xml(p)
 finally:os.unlink(p)
@app.post('/api/import/packages')
def pkgs(file:UploadFile=File(...)):
 if not file.filename.lower().endswith(('.xlsx','.xlsm')):raise HTTPException(400,'Bitte XLSX verwenden.')
 with tempfile.NamedTemporaryFile(suffix='.xlsx',delete=False) as f:f.write(file.file.read());p=f.name
 try:return import_xlsx(p)
 finally:os.unlink(p)
@app.get('/',response_class=HTMLResponse)
def ui():return HTML

HTML=r'''<!doctype html><html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>GameVault</title><style>
*{box-sizing:border-box}body{margin:0;background:#070d1a;color:#e7edf7;font:14px system-ui,Segoe UI,sans-serif}.wrap{max-width:1400px;margin:auto;padding:24px}.top{display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #1f2937;padding:16px 24px}.brand{font-size:22px;font-weight:800}.muted{color:#8996aa}.btn,input,select{border:1px solid #283449;background:#111a2b;color:#eef;padding:10px 12px;border-radius:11px}.btn{cursor:pointer}.blue{background:#2563eb;border-color:#2563eb}.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin:18px 0}.card,.detail,.toolbar{background:#0c1424;border:1px solid #1f2b40;border-radius:18px}.stat{padding:18px}.stat b{display:block;font-size:23px;margin-top:4px}.toolbar{display:flex;gap:9px;padding:12px;margin-bottom:16px}.toolbar input{flex:1}.layout{display:grid;grid-template-columns:1fr 1.35fr;gap:18px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;align-content:start}.card{padding:15px;cursor:pointer;min-height:115px}.card:hover,.card.on{border-color:#3b82f6}.tag{display:inline-block;padding:4px 8px;border-radius:7px;background:#1d4ed8;font-size:11px}.title{font-size:17px;font-weight:700;margin:13px 0 5px}.detail{padding:22px;position:sticky;top:12px;max-height:calc(100vh - 24px);overflow:auto}.detail h2{font-size:27px;margin:8px 0}.info{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}.info div{background:#111a2b;border-radius:11px;padding:10px}.desc{line-height:1.55;color:#b8c3d4}.pkg{border-top:1px solid #263248;padding:9px 0;display:grid;grid-template-columns:1.7fr .5fr .5fr .5fr;gap:6px}.modal{display:none;position:fixed;inset:0;background:#000a;align-items:center;justify-content:center}.modal.show{display:flex}.box{width:min(600px,92vw);background:#0c1424;border:1px solid #33415c;border-radius:18px;padding:20px}.upload{padding:14px;border:1px dashed #405170;border-radius:13px;margin:10px 0}.ok{color:#6ee7b7}@media(max-width:900px){.layout{grid-template-columns:1fr}.grid{grid-template-columns:1fr}.stats{grid-template-columns:1fr}.detail{position:static}.toolbar{flex-wrap:wrap}.toolbar input{flex-basis:100%}}
</style></head><body><header class="top"><div><div class="brand">GameVault GameVault</div><span class="muted">Sammlung & Backup-Archiv · v0.1.0</span></div><button class="btn blue" onclick="modal(true)">Import</button></header><main class="wrap"><section class="stats"><div class="card stat"><span class="muted">Spiele</span><b id="sg">-</b></div><div class="card stat"><span class="muted">Backup-Pakete</span><b id="sp">-</b></div><div class="card stat"><span class="muted">Backup-Größe</span><b id="ss">-</b></div></section><div class="toolbar"><input id="q" placeholder="Titel suchen ..." oninput="render()"><select id="p" onchange="render()"><option value="">Alle Plattformen</option></select></div><div class="layout"><section class="grid" id="list"></section><aside class="detail" id="detail"><span class="muted">Spiel auswählen</span></aside></div></main><div id="modal" class="modal" onclick="if(event.target===this)modal(false)"><div class="box"><h2>Daten importieren</h2><p class="muted">Zuerst Game Collector XML, danach PS4 XLSX. Re-Import aktualisiert vorhandene Datensätze.</p><div class="upload"><b>Game Collector XML</b><br><input type="file" id="xml" accept=".xml"><button class="btn" onclick="upload('xml','/api/import/gamecollector')">Importieren</button></div><div class="upload"><b>PS4 Paketliste</b><br><input type="file" id="xlsx" accept=".xlsx"><button class="btn" onclick="upload('xlsx','/api/import/packages')">Importieren</button></div><div id="msg" class="ok"></div><p><button class="btn" onclick="modal(false)">Schließen</button></p></div></div><script>
let data=[],selected=null;function esc(s){return (s??'').toString().replace(/[&<>\"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]))}async function load(){data=await fetch('/api/games').then(r=>r.json());let st=await fetch('/api/stats').then(r=>r.json());sg.textContent=st.games;sp.textContent=st.packages;ss.textContent=st.size_gb.toLocaleString('de-DE')+' GB';p.innerHTML='<option value="">Alle Plattformen</option>'+Object.keys(st.platforms).sort().map(x=>`<option>${esc(x)}</option>`).join('');render()}function render(){let term=q.value.toLowerCase(),pl=p.value;let a=data.filter(g=>(!pl||g.platform===pl)&&(!term||(g.title+' '+(g.title_id||'')).toLowerCase().includes(term)));list.innerHTML=a.map(g=>`<div class="card ${selected===g.id?'on':''}" onclick="show(${g.id})"><span class="tag">${esc(g.platform)}</span><div class="title">${esc(g.title)}</div><span class="muted">${esc(g.publisher||'')} ${g.packages.length?' · '+g.packages.length+' Pakete':''}</span></div>`).join('')}function show(id){selected=id;let g=data.find(x=>x.id===id);render();let pk=g.packages.map(x=>`<div class="pkg"><span>${esc(x.name||x.filename)}</span><span>${esc(x.category||'')}</span><span>${esc(x.location||'')}</span><span>${x.size_gb==null?'':x.size_gb.toLocaleString('de-DE')+' GB'}</span></div>`).join('');detail.innerHTML=`<span class="tag">${esc(g.platform)}</span><h2>${esc(g.title)}</h2><p class="muted">${esc(g.publisher||'')} ${g.developer?' · '+esc(g.developer):''}</p><div class="info"><div><small class="muted">TitleID</small><br><b>${esc(g.title_id||'–')}</b></div><div><small class="muted">Genre</small><br><b>${esc(g.genres||'–')}</b></div><div><small class="muted">Status</small><br><b>${g.completed?'OK Durchgespielt':esc(g.collection_status||'–')}</b></div></div><p class="desc">${esc((g.description||'').replace(/<[^>]*>/g,' ')).slice(0,1800)}</p><h3>Backup-Pakete (${g.packages.length})</h3>${pk||'<p class="muted">Keine Backup-Pakete zugeordnet.</p>'}`}function modal(v){document.getElementById('modal').classList.toggle('show',v)}async function upload(id,url){let f=document.getElementById(id).files[0];if(!f)return;let fd=new FormData();fd.append('file',f);msg.textContent='Import läuft ...';let r=await fetch(url,{method:'POST',body:fd});msg.textContent=r.ok?'OK '+JSON.stringify(await r.json()):'Fehler: '+await r.text();if(r.ok)await load()}load();
</script></body></html>'''

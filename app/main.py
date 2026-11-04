from __future__ import annotations
import html, os, re, tempfile, xml.etree.ElementTree as ET
from typing import Optional
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy import create_engine, String, Text, Float, Boolean, ForeignKey, select, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, Session
from openpyxl import load_workbook
DB=os.getenv("DATABASE_URL","postgresql+psycopg://gamevault:gamevault@db:5432/gamevault")
engine=create_engine(DB,pool_pre_ping=True)
class Base(DeclarativeBase): pass
class Game(Base):
 __tablename__="games"
 id:Mapped[int]=mapped_column(primary_key=True); gc_id:Mapped[Optional[str]]=mapped_column(String(40),unique=True,nullable=True); platform:Mapped[str]=mapped_column(String(80),index=True); title:Mapped[str]=mapped_column(String(300),index=True); title_id:Mapped[Optional[str]]=mapped_column(String(40),index=True,nullable=True); publisher:Mapped[Optional[str]]=mapped_column(String(200),nullable=True); developer:Mapped[Optional[str]]=mapped_column(String(200),nullable=True); genres:Mapped[Optional[str]]=mapped_column(String(300),nullable=True); release_date:Mapped[Optional[str]]=mapped_column(String(30),nullable=True); completed:Mapped[bool]=mapped_column(Boolean,default=False); collection_status:Mapped[Optional[str]]=mapped_column(String(80),nullable=True); completeness:Mapped[Optional[str]]=mapped_column(String(80),nullable=True); current_value:Mapped[Optional[str]]=mapped_column(String(50),nullable=True); description:Mapped[Optional[str]]=mapped_column(Text,nullable=True); cover_source:Mapped[Optional[str]]=mapped_column(Text,nullable=True); pricecharting_url:Mapped[Optional[str]]=mapped_column(Text,nullable=True); packages:Mapped[list["Package"]]=relationship(back_populates="game",cascade="all,delete-orphan")
class Package(Base):
 __tablename__="packages"
 id:Mapped[int]=mapped_column(primary_key=True); filename:Mapped[str]=mapped_column(String(600),unique=True,index=True); game_id:Mapped[Optional[int]]=mapped_column(ForeignKey("games.id"),nullable=True,index=True); title_id:Mapped[Optional[str]]=mapped_column(String(40),index=True,nullable=True); name:Mapped[Optional[str]]=mapped_column(String(400),nullable=True); version:Mapped[Optional[str]]=mapped_column(String(40),nullable=True); pkg_version:Mapped[Optional[str]]=mapped_column(String(40),nullable=True); newest_patch:Mapped[Optional[str]]=mapped_column(String(40),nullable=True); decision:Mapped[Optional[str]]=mapped_column(String(80),nullable=True); location:Mapped[Optional[str]]=mapped_column(String(80),nullable=True); category:Mapped[Optional[str]]=mapped_column(String(40),nullable=True); size_gb:Mapped[Optional[float]]=mapped_column(Float,nullable=True); game:Mapped[Optional[Game]]=relationship(back_populates="packages")
Base.metadata.create_all(engine)
app=FastAPI(title="GameVault",version="0.1.1")
def txt(e,path):
 n=e.find(path); return (n.text or "").strip() if n is not None and n.text else None
def disp(e,path): return txt(e,path+"/displayname") or txt(e,path)
def norm_tid(v):
 if not v:return None
 s=re.sub(r"[^A-Za-z0-9]","",str(v)).upper(); m=re.fullmatch(r"CUSA(\d+)",s); return "CUSA"+m.group(1).zfill(5) if m else s
def clean(v): return re.sub(r"\s*\[(Game|Update)\]\s*$","",str(v or ""),flags=re.I).replace("_"," ").strip()
def key(v): return re.sub(r"[^a-z0-9]","",clean(v).casefold())
def nfloat(v):
 if v in (None,""):return None
 if isinstance(v,(int,float)):return float(v)
 try:return float(str(v).replace(".","").replace(",","."))
 except:return None
def import_xml(path):
 nodes=ET.parse(path).getroot().findall("./gamelist/game"); added=updated=0
 with Session(engine) as db:
  for e in nodes:
   gc=txt(e,"id"); g=db.scalar(select(Game).where(Game.gc_id==gc)); vals=dict(platform=disp(e,"platform") or "Unbekannt",title=txt(e,"title") or "Ohne Titel",publisher=disp(e,"publisher"),developer=disp(e,"developer"),genres=", ".join(x.text.strip() for x in e.findall("./genres/genre/displayname") if x.text),release_date=txt(e,"releasedate/date"),completed=(e.find("completed") is not None and e.find("completed").attrib.get("boolvalue")=="1"),collection_status=txt(e,"collectionstatus"),completeness=txt(e,"completeness"),current_value=txt(e,"currentvalue"),description=html.unescape(txt(e,"description") or ""),cover_source=txt(e,"coverfront"),pricecharting_url=txt(e,"pricechartingurl"))
   if g:
    for k,v in vals.items():setattr(g,k,v)
    updated+=1
   else: db.add(Game(gc_id=gc,**vals)); added+=1
  db.commit()
 return {"rows":len(nodes),"added":added,"updated":updated}
def import_xlsx(path):
 wb=load_workbook(path,data_only=True,read_only=True); ws=wb[wb.sheetnames[0]]; rows=ws.iter_rows(values_only=True); headers=[str(x).strip() if x else "" for x in next(rows)]; idx={n:i for i,n in enumerate(headers)}; added=updated=stubs=0
 with Session(engine) as db:
  ps4=db.scalars(select(Game).where(Game.platform=="PlayStation 4")).all(); byname={key(g.title):g for g in ps4}
  for r in rows:
   get=lambda n:r[idx[n]] if n in idx and idx[n]<len(r) else None
   fn=get("Filename")
   if not fn:continue
   tid=norm_tid(get("Title ID")); nm=clean(get("Name")); pkg=db.scalar(select(Package).where(Package.filename==str(fn))); game=pkg.game if pkg and pkg.game else byname.get(key(nm)) if nm else None
   if not game and tid: game=db.scalar(select(Game).where(Game.title_id==tid,Game.platform=="PlayStation 4"))
   if not game and get("Category") in ("Game","Patch"):
    game=Game(platform="PlayStation 4",title=nm or tid or str(fn),title_id=tid); db.add(game); db.flush(); byname[key(game.title)]=game; stubs+=1
   vals=dict(game_id=game.id if game else None,title_id=tid,name=nm or None,version=str(get("Version")) if get("Version") is not None else None,pkg_version=str(get("Version pkg")) if get("Version pkg") is not None else None,newest_patch=str(get("Newest Patch")) if get("Newest Patch") is not None else None,decision=str(get("Entscheidung")) if get("Entscheidung") is not None else None,location=str(get("Location")) if get("Location") is not None else None,category=str(get("Category")) if get("Category") is not None else None,size_gb=nfloat(get("Size (GB)")))
   if pkg:
    for k,v in vals.items():setattr(pkg,k,v)
    updated+=1
   else:db.add(Package(filename=str(fn),**vals));added+=1
  db.commit()
 return {"added":added,"updated":updated,"stubs":stubs}
def serial(g): return {"id":g.id,"title":g.title,"platform":g.platform,"title_id":g.title_id,"publisher":g.publisher,"developer":g.developer,"genres":g.genres,"completed":g.completed,"collection_status":g.collection_status,"description":g.description,"packages":[{"filename":p.filename,"name":p.name,"version":p.version,"pkg_version":p.pkg_version,"location":p.location,"category":p.category,"size_gb":p.size_gb} for p in g.packages]}
@app.get("/api/games")
def games():
 with Session(engine) as db:return [serial(g) for g in db.scalars(select(Game).order_by(Game.title)).all()]
@app.get("/api/stats")
def stats():
 with Session(engine) as db:return {"games":db.scalar(select(func.count(Game.id))) or 0,"packages":db.scalar(select(func.count(Package.id))) or 0,"size_gb":round(db.scalar(select(func.coalesce(func.sum(Package.size_gb),0))) or 0,3),"platforms":dict(db.execute(select(Game.platform,func.count(Game.id)).group_by(Game.platform)).all())}
@app.post("/api/import/gamecollector")
def gc(file:UploadFile=File(...)):
 with tempfile.NamedTemporaryFile(suffix=".xml",delete=False) as f:f.write(file.file.read());p=f.name
 try:return import_xml(p)
 finally:os.unlink(p)
@app.post("/api/import/packages")
def pkgs(file:UploadFile=File(...)):
 if not file.filename.lower().endswith((".xlsx",".xlsm")):raise HTTPException(400,"Bitte XLSX verwenden.")
 with tempfile.NamedTemporaryFile(suffix=".xlsx",delete=False) as f:f.write(file.file.read());p=f.name
 try:return import_xlsx(p)
 finally:os.unlink(p)
@app.get("/",response_class=HTMLResponse)
def ui(): return HTML
HTML="""<!doctype html><html lang='de'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>GameVault</title><style>*{box-sizing:border-box}body{margin:0;background:#070d1a;color:#e7edf7;font:14px system-ui}.w{max-width:1400px;margin:auto;padding:24px}.top{padding:18px 24px;border-bottom:1px solid #1f2937;display:flex;justify-content:space-between}.b{font-size:22px;font-weight:800}.mut{color:#8996aa}.btn,input,select{background:#111a2b;color:#eef;border:1px solid #283449;padding:10px;border-radius:10px}.btn{cursor:pointer}.blue{background:#2563eb}.stats,.grid{display:grid;gap:12px}.stats{grid-template-columns:repeat(3,1fr);margin:18px 0}.grid{grid-template-columns:1fr 1fr}.card,.detail,.bar{background:#0c1424;border:1px solid #1f2b40;border-radius:16px;padding:15px}.stat b{display:block;font-size:24px}.bar{display:flex;gap:8px;margin-bottom:16px}.bar input{flex:1}.layout{display:grid;grid-template-columns:1fr 1.35fr;gap:18px}.card{cursor:pointer}.card:hover{border-color:#3b82f6}.tag{display:inline-block;background:#1d4ed8;padding:4px 8px;border-radius:7px;font-size:11px}.title{font-size:17px;font-weight:700;margin:12px 0 4px}.pkg{border-top:1px solid #263248;padding:8px 0}.modal{display:none;position:fixed;inset:0;background:#000a;align-items:center;justify-content:center}.modal.show{display:flex}.box{width:min(600px,92vw);background:#0c1424;padding:20px;border-radius:18px}.up{border:1px dashed #405170;padding:12px;margin:10px 0;border-radius:12px}@media(max-width:900px){.layout,.grid,.stats{grid-template-columns:1fr}}</style></head><body><header class='top'><div><div class='b'>GameVault</div><span class='mut'>Sammlung und Backup-Archiv · v0.1.1</span></div><button class='btn blue' onclick='modal(true)'>Import</button></header><main class='w'><section class='stats'><div class='card stat'><span class='mut'>Spiele</span><b id='sg'>-</b></div><div class='card stat'><span class='mut'>Backup-Pakete</span><b id='sp'>-</b></div><div class='card stat'><span class='mut'>Backup-Größe</span><b id='ss'>-</b></div></section><div class='bar'><input id='q' placeholder='Titel oder TitleID suchen' oninput='render()'><select id='pf' onchange='render()'><option value=''>Alle Plattformen</option></select></div><div class='layout'><section class='grid' id='list'></section><aside class='detail' id='detail'><span class='mut'>Spiel auswählen</span></aside></div></main><div class='modal' id='modal'><div class='box'><h2>Daten importieren</h2><div class='up'>Game Collector XML <input type='file' id='xml'><button class='btn' onclick="upload('xml','/api/import/gamecollector')">Importieren</button></div><div class='up'>PS4 XLSX <input type='file' id='xlsx'><button class='btn' onclick="upload('xlsx','/api/import/packages')">Importieren</button></div><p id='msg'></p><button class='btn' onclick='modal(false)'>Schließen</button></div></div><script>let data=[];function e(s){return(s??'').toString().replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]))}async function load(){data=await fetch('/api/games').then(r=>r.json());let s=await fetch('/api/stats').then(r=>r.json());sg.textContent=s.games;sp.textContent=s.packages;ss.textContent=s.size_gb.toLocaleString('de-DE')+' GB';pf.innerHTML="<option value=''>Alle Plattformen</option>"+Object.keys(s.platforms).sort().map(x=>`<option>${e(x)}</option>`).join('');render()}function render(){let t=q.value.toLowerCase(),p=pf.value,a=data.filter(g=>(!p||g.platform===p)&&(!t||(g.title+' '+(g.title_id||'')).toLowerCase().includes(t)));list.innerHTML=a.map(g=>`<div class='card' onclick='show(${g.id})'><span class='tag'>${e(g.platform)}</span><div class='title'>${e(g.title)}</div><span class='mut'>${e(g.publisher||'')} ${g.packages.length?' · '+g.packages.length+' Pakete':''}</span></div>`).join('')}function show(id){let g=data.find(x=>x.id===id);detail.innerHTML=`<span class='tag'>${e(g.platform)}</span><h2>${e(g.title)}</h2><p class='mut'>${e(g.publisher||'')}</p><p>TitleID: <b>${e(g.title_id||'–')}</b></p><p>${e((g.description||'').replace(/<[^>]*>/g,' ')).slice(0,1800)}</p><h3>Backup-Pakete (${g.packages.length})</h3>`+g.packages.map(p=>`<div class='pkg'><b>${e(p.name||p.filename)}</b><br><span class='mut'>${e(p.category||'')} · ${e(p.location||'')} · ${p.size_gb??''} GB</span></div>`).join('')}function modal(v){document.getElementById('modal').classList.toggle('show',v)}async function upload(i,u){let f=document.getElementById(i).files[0];if(!f)return;let d=new FormData();d.append('file',f);msg.textContent='Import läuft ...';let r=await fetch(u,{method:'POST',body:d});msg.textContent=r.ok?'OK '+JSON.stringify(await r.json()):await r.text();if(r.ok)load()}load()</script></body></html>"""

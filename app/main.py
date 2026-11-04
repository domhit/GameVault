from __future__ import annotations
import html, os, re, tempfile, xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from sqlalchemy import create_engine, String, Text, Float, Boolean, ForeignKey, select, func, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, Session
from openpyxl import load_workbook
from .providers import online
DB=os.getenv('DATABASE_URL','postgresql+psycopg://gamevault:gamevault@db:5432/gamevault'); DATA=os.getenv('DATA_DIR','/data')
engine=create_engine(DB,pool_pre_ping=True)
class Base(DeclarativeBase):pass
class Game(Base):
 __tablename__='games'
 id:Mapped[int]=mapped_column(primary_key=True);gc_id:Mapped[Optional[str]]=mapped_column(String(40),unique=True,nullable=True);platform:Mapped[str]=mapped_column(String(80),index=True);title:Mapped[str]=mapped_column(String(300),index=True);title_id:Mapped[Optional[str]]=mapped_column(String(40),index=True,nullable=True);publisher:Mapped[Optional[str]]=mapped_column(String(200),nullable=True);developer:Mapped[Optional[str]]=mapped_column(String(200),nullable=True);genres:Mapped[Optional[str]]=mapped_column(String(300),nullable=True);release_date:Mapped[Optional[str]]=mapped_column(String(30),nullable=True);completed:Mapped[bool]=mapped_column(Boolean,default=False);collection_status:Mapped[Optional[str]]=mapped_column(String(80),nullable=True);completeness:Mapped[Optional[str]]=mapped_column(String(80),nullable=True);current_value:Mapped[Optional[str]]=mapped_column(String(50),nullable=True);description:Mapped[Optional[str]]=mapped_column(Text,nullable=True);cover_source:Mapped[Optional[str]]=mapped_column(Text,nullable=True);pricecharting_url:Mapped[Optional[str]]=mapped_column(Text,nullable=True);metadata_source:Mapped[Optional[str]]=mapped_column(String(100),nullable=True);metadata_updated_at:Mapped[Optional[str]]=mapped_column(String(40),nullable=True);remote_latest_version:Mapped[Optional[str]]=mapped_column(String(40),nullable=True);remote_checked_at:Mapped[Optional[str]]=mapped_column(String(40),nullable=True);metadata_error:Mapped[Optional[str]]=mapped_column(Text,nullable=True);packages:Mapped[list['Package']]=relationship(back_populates='game',cascade='all,delete-orphan')
class Package(Base):
 __tablename__='packages'
 id:Mapped[int]=mapped_column(primary_key=True);filename:Mapped[str]=mapped_column(String(600),unique=True,index=True);game_id:Mapped[Optional[int]]=mapped_column(ForeignKey('games.id'),nullable=True,index=True);title_id:Mapped[Optional[str]]=mapped_column(String(40),index=True,nullable=True);name:Mapped[Optional[str]]=mapped_column(String(400),nullable=True);version:Mapped[Optional[str]]=mapped_column(String(40),nullable=True);pkg_version:Mapped[Optional[str]]=mapped_column(String(40),nullable=True);newest_patch:Mapped[Optional[str]]=mapped_column(String(40),nullable=True);decision:Mapped[Optional[str]]=mapped_column(String(80),nullable=True);location:Mapped[Optional[str]]=mapped_column(String(80),nullable=True);category:Mapped[Optional[str]]=mapped_column(String(40),nullable=True);size_gb:Mapped[Optional[float]]=mapped_column(Float,nullable=True);game:Mapped[Optional[Game]]=relationship(back_populates='packages')
Base.metadata.create_all(engine)
# Lightweight migration for existing v0.2 DB
with engine.begin() as c:
 for col,typ in [('metadata_source','VARCHAR(100)'),('metadata_updated_at','VARCHAR(40)'),('remote_latest_version','VARCHAR(40)'),('remote_checked_at','VARCHAR(40)'),('metadata_error','TEXT')]:
  c.execute(text(f'ALTER TABLE games ADD COLUMN IF NOT EXISTS {col} {typ}'))
app=FastAPI(title='GameVault',version='0.4.0')
def now():return datetime.now(timezone.utc).isoformat()
def txt(e,p):
 n=e.find(p);return (n.text or '').strip() if n is not None and n.text else None
def disp(e,p):return txt(e,p+'/displayname') or txt(e,p)
def ntid(v):
 if not v:return None
 s=re.sub(r'[^A-Za-z0-9]','',str(v)).upper();m=re.fullmatch(r'CUSA(\d+)',s);return 'CUSA'+m.group(1).zfill(5) if m else s
def clean(v):return re.sub(r'\s*\[(Game|Update|Patch|DLC)\]\s*$','',str(v or ''),flags=re.I).replace('_',' ').strip()
def key(v):return re.sub(r'[^a-z0-9]','',clean(v).casefold())
def nf(v):
 try:return float(v) if isinstance(v,(int,float)) else float(str(v).replace('.','').replace(',','.'))
 except:return None
def import_xml(p):
 nodes=ET.parse(p).getroot().findall('./gamelist/game');a=u=0
 with Session(engine) as db:
  for e in nodes:
   gc=txt(e,'id');g=db.scalar(select(Game).where(Game.gc_id==gc));vals=dict(platform=disp(e,'platform') or 'Unbekannt',title=txt(e,'title') or 'Ohne Titel',publisher=disp(e,'publisher'),developer=disp(e,'developer'),genres=', '.join(x.text.strip() for x in e.findall('./genres/genre/displayname') if x.text),release_date=txt(e,'releasedate/date'),completed=e.find('completed') is not None and e.find('completed').attrib.get('boolvalue')=='1',collection_status=txt(e,'collectionstatus'),completeness=txt(e,'completeness'),current_value=txt(e,'currentvalue'),description=html.unescape(txt(e,'description') or ''),pricecharting_url=txt(e,'pricechartingurl'))
   if g:
    for k,v in vals.items():setattr(g,k,v)
    u+=1
   else:db.add(Game(gc_id=gc,**vals));a+=1
  db.commit()
 return {'rows':len(nodes),'added':a,'updated':u}
def import_xlsx(p):
 wb=load_workbook(p,data_only=True,read_only=True);ws=wb[wb.sheetnames[0]];rows=ws.iter_rows(values_only=True);hdr=[str(x).strip() if x else '' for x in next(rows)];ix={n:i for i,n in enumerate(hdr)};a=u=s=0
 with Session(engine) as db:
  ps4=db.scalars(select(Game).where(Game.platform=='PlayStation 4')).all();bn={key(g.title):g for g in ps4}
  for r in rows:
   get=lambda n:r[ix[n]] if n in ix and ix[n]<len(r) else None;fn=get('Filename')
   if not fn:continue
   tid=ntid(get('Title ID'));nm=clean(get('Name'));pkg=db.scalar(select(Package).where(Package.filename==str(fn)));g=pkg.game if pkg and pkg.game else bn.get(key(nm))
   if not g and tid:g=db.scalar(select(Game).where(Game.title_id==tid,Game.platform=='PlayStation 4'))
   if not g and get('Category') in ('Game','Patch'):g=Game(platform='PlayStation 4',title=nm or tid,title_id=tid);db.add(g);db.flush();bn[key(g.title)]=g;s+=1
   if g and tid and not g.title_id:g.title_id=tid
   vals=dict(game_id=g.id if g else None,title_id=tid,name=nm,version=str(get('Version')) if get('Version') is not None else None,pkg_version=str(get('Version pkg')) if get('Version pkg') is not None else None,newest_patch=str(get('Newest Patch')) if get('Newest Patch') is not None else None,decision=str(get('Entscheidung')) if get('Entscheidung') is not None else None,location=str(get('Location')) if get('Location') is not None else None,category=str(get('Category')) if get('Category') is not None else None,size_gb=nf(get('Size (GB)')))
   if pkg:
    for k,v in vals.items():setattr(pkg,k,v)
    u+=1
   else:db.add(Package(filename=str(fn),**vals));a+=1
  db.commit()
 return {'added':a,'updated':u,'stubs':s}
def backfill(db):
 changed=conflicts=0
 for g in db.scalars(select(Game)).all():
  ids=sorted({ntid(p.title_id) for p in g.packages if p.title_id})
  if not g.title_id and len(ids)==1:g.title_id=ids[0];changed+=1
  elif len(ids)>1:conflicts+=1
 db.commit();return changed,conflicts
def latest_local(g):
 vals=[p.version for p in g.packages if (p.category or '').casefold() in ('patch','update') and p.version]
 def vk(v):return tuple(int(x) for x in re.findall(r'\d+',v))
 return max(vals,key=vk) if vals else None
def enrich_one(db,g,caches,download=True):
 sources=[];rec=None
 try:
  if g.platform=='PlayStation 4':
   rec=online.ps4_match(caches['ps4'],g.title_id,g.title)
   if rec:
    g.title_id=g.title_id or ntid(online.pick(rec,'title_id','title id','cusa','id'));g.title=online.pick(rec,'title','name') or g.title;sources.append('SerialStation dataset')
   upd=online.update_match(caches['updates'],g.title_id)
   if upd:g.remote_latest_version=str(online.pick(upd,'latest_version','latest version','version','app_ver') or '') or None;sources.append('Sony update dataset')
   g.remote_checked_at=now()
  elif g.platform=='Xbox 360':
   rec=online.x360_match(caches['x360'],g.title_id,g.title)
   if rec:
    g.title_id=g.title_id or str(rec.get('id','')).upper();g.title=rec.get('title') or g.title;g.publisher=g.publisher or rec.get('publisher');g.developer=g.developer or rec.get('developer');g.genres=g.genres or ', '.join(rec.get('genre',[]) if isinstance(rec.get('genre'),list) else [rec.get('genre','')]);g.release_date=g.release_date or rec.get('release_date');sources.append('x360db')
  url=online.cover_candidate(g.platform,g.title_id,rec)
  if download and url:
   local=online.save_cover(url,g.id,DATA)
   if local:g.cover_source=local;sources.append('cover repository')
  g.metadata_source=', '.join(sources) or g.metadata_source;g.metadata_updated_at=now();g.metadata_error=None
  return bool(sources)
 except Exception as e:g.metadata_error=str(e)[:500];return False
@app.get('/covers/{name}')
def cover(name:str):
 p=Path(DATA)/'covers'/Path(name).name
 if not p.exists():raise HTTPException(404)
 return FileResponse(p)
@app.get('/api/games')
def games():
 with Session(engine) as db:
  backfill(db);return [ser(g) for g in db.scalars(select(Game).order_by(Game.title)).all()]
def ser(g):
 local=latest_local(g);remote=g.remote_latest_version
 def vk(v):return tuple(int(x) for x in re.findall(r'\d+',v or ''))
 status='unknown'
 if remote and local:status='update_available' if vk(remote)>vk(local) else 'current'
 elif remote:status='update_available'
 return {'id':g.id,'title':g.title,'platform':g.platform,'title_id':g.title_id,'publisher':g.publisher,'developer':g.developer,'genres':g.genres,'release_date':g.release_date,'completed':g.completed,'collection_status':g.collection_status,'completeness':g.completeness,'current_value':g.current_value,'description':g.description,'cover_source':g.cover_source,'metadata_missing':not bool(g.metadata_source or g.gc_id),'metadata_source':g.metadata_source,'metadata_updated_at':g.metadata_updated_at,'metadata_error':g.metadata_error,'local_latest_version':local,'remote_latest_version':remote,'update_status':status,'packages':[{'filename':p.filename,'title_id':p.title_id,'name':p.name,'version':p.version,'pkg_version':p.pkg_version,'newest_patch':p.newest_patch,'decision':p.decision,'location':p.location,'category':p.category,'size_gb':p.size_gb} for p in g.packages]}
@app.get('/api/stats')
def stats():
 with Session(engine) as db:
  gs=db.scalars(select(Game)).all();return {'games':len(gs),'packages':db.scalar(select(func.count(Package.id))) or 0,'size_gb':round(db.scalar(select(func.coalesce(func.sum(Package.size_gb),0))) or 0,3),'platforms':dict(db.execute(select(Game.platform,func.count(Game.id)).group_by(Game.platform)).all()),'missing':sum(not bool(g.metadata_source or g.gc_id) for g in gs),'updates':sum(ser(g)['update_status']=='update_available' for g in gs)}
@app.post('/api/maintenance/backfill-titleids')
def bf():
 with Session(engine) as db:
  a,b=backfill(db);return {'updated':a,'conflicts':b}
@app.post('/api/metadata/refresh')
def refresh():
 results={'checked':0,'enriched':0,'errors':0}
 try:c={'ps4':online.ps4_catalog(),'updates':online.ps4_updates(),'x360':online.x360_catalog()}
 except Exception as e:raise HTTPException(502,f'Quelldaten konnten nicht geladen werden: {e}')
 with Session(engine) as db:
  backfill(db)
  for g in db.scalars(select(Game)).all():
   results['checked']+=1
   if enrich_one(db,g,c):results['enriched']+=1
   if g.metadata_error:results['errors']+=1
  db.commit()
 return results
@app.post('/api/import/gamecollector')
def gc(file:UploadFile=File(...)):
 with tempfile.NamedTemporaryFile(suffix='.xml',delete=False) as f:f.write(file.file.read());p=f.name
 try:return import_xml(p)
 finally:os.unlink(p)
@app.post('/api/import/packages')
def pk(file:UploadFile=File(...)):
 with tempfile.NamedTemporaryFile(suffix='.xlsx',delete=False) as f:f.write(file.file.read());p=f.name
 try:return import_xlsx(p)
 finally:os.unlink(p)
@app.get('/',response_class=HTMLResponse)
def ui():return HTML
HTML=r'''<!doctype html><html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>GameVault</title><style>
*{box-sizing:border-box}html,body{height:100%;margin:0}body{background:#070d1a;color:#e7edf7;font:14px system-ui;overflow:hidden}.top{height:72px;display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #1f2937;padding:0 28px}.brand{font-size:22px;font-weight:800}.mut{color:#8996aa}.small{font-size:12px}.shell{height:calc(100vh - 72px);max-width:1550px;margin:auto;padding:16px 22px;display:grid;grid-template-rows:auto auto 1fr;gap:12px}.stats{display:grid;grid-template-columns:repeat(5,1fr);gap:10px}.stat,.card,.detail,.bar{background:#0c1424;border:1px solid #1f2b40;border-radius:15px}.stat{padding:12px 15px}.stat b{display:block;font-size:21px}.bar{display:flex;gap:8px;padding:9px}.btn,input,select{background:#111a2b;color:#eef;border:1px solid #283449;padding:9px 11px;border-radius:9px}.btn{cursor:pointer}.blue{background:#2563eb}.bar input{flex:1}.layout{min-height:0;display:grid;grid-template-columns:minmax(410px,.95fr) minmax(550px,1.35fr);gap:15px}.list,.detail{overflow-y:auto;min-height:0}.list{display:grid;grid-template-columns:1fr 1fr;gap:9px;align-content:start;padding-right:4px}.card{min-height:145px;display:grid;grid-template-columns:76px 1fr;overflow:hidden;cursor:pointer;border-left:5px solid var(--accent)}.card:hover,.card.on{border-color:var(--accent);background:#101d34}.cover,.heroCover{background:#101827;display:flex;align-items:center;justify-content:center;font-weight:900;color:var(--accent);font-size:19px}.cover img,.heroCover img{width:100%;height:100%;object-fit:cover}.meta{padding:12px}.tag{display:inline-block;padding:4px 7px;border-radius:7px;background:var(--accent);color:white;font-size:10px}.title{font-size:16px;font-weight:750;margin:9px 0 3px}.badges{margin-top:8px}.badge{display:inline-block;padding:3px 6px;border-radius:6px;background:#172238;margin:2px;font-size:10px}.warn{color:#fbbf24}.ok{color:#68d391}.detail{padding:21px}.hero{display:grid;grid-template-columns:135px 1fr auto;gap:18px}.heroCover{width:135px;height:185px;border-radius:13px;overflow:hidden}.detail h1{font-size:28px;margin:8px 0}.value{background:#111a2b;padding:11px 14px;border-radius:12px}.infos{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin:17px 0}.info{background:#111a2b;padding:9px;border-radius:10px;min-height:58px}.pkghead,.pkg{display:grid;grid-template-columns:1.6fr .5fr .5fr .6fr .5fr;gap:7px}.pkg{border-top:1px solid #253047;padding:9px 0}.pkghead{color:#7f8da3;font-size:11px}.modal{display:none;position:fixed;inset:0;background:#000b;z-index:5;align-items:center;justify-content:center}.modal.show{display:flex}.box{width:min(650px,93vw);background:#0c1424;padding:20px;border-radius:17px}.up{border:1px dashed #405170;padding:12px;margin:9px 0;border-radius:11px}.PS4{--accent:#2166d1}.PS3{--accent:#b63232}.PS2{--accent:#d8a620}.X360{--accent:#259b43}.OTHER{--accent:#64748b}@media(max-width:1000px){body{overflow:auto}.shell{height:auto}.layout{grid-template-columns:1fr}.list,.detail{overflow:visible}.stats{grid-template-columns:1fr 1fr}.list{grid-template-columns:1fr}}
</style></head><body><header class="top"><div><div class="brand">GameVault</div><div class="mut small">Sammlung, Backups und Metadaten · v0.4.0</div></div><div><button class="btn" onclick="metadata()">Metadaten aktualisieren</button> <button class="btn blue" onclick="modal(true)">Import</button></div></header><main class="shell"><section class="stats"><div class="stat"><span class="mut">Spiele</span><b id="sg">-</b></div><div class="stat"><span class="mut">Pakete</span><b id="sp">-</b></div><div class="stat"><span class="mut">Größe</span><b id="ss">-</b></div><div class="stat"><span class="mut">Metadaten fehlen</span><b id="sm">-</b></div><div class="stat"><span class="mut">Updates verfügbar</span><b id="su">-</b></div></section><div class="bar"><input id="q" placeholder="Titel oder TitleID suchen" oninput="render()"><select id="pf" onchange="render()"><option value="">Alle Plattformen</option></select><select id="sf" onchange="render()"><option value="">Alle Status</option><option value="missing">Metadaten fehlen</option><option value="updates">Update verfügbar</option></select></div><div class="layout"><section class="list" id="list"></section><aside class="detail" id="detail"><span class="mut">Spiel auswählen</span></aside></div></main><div class="modal" id="modal"><div class="box"><h2>Datenimport</h2><div class="up">Game Collector XML <input type="file" id="xml"><button class="btn" onclick="upload('xml','/api/import/gamecollector')">Import</button></div><div class="up">PS4 XLSX <input type="file" id="xlsx"><button class="btn" onclick="upload('xlsx','/api/import/packages')">Import</button></div><p id="msg"></p><button class="btn" onclick="modal(false)">Schließen</button></div></div><script>
let data=[],selected=null;const E=s=>(s??'').toString().replace(/[&<>\"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));function pc(p){return p==='PlayStation 4'?'PS4':p==='PlayStation 3'?'PS3':p==='PlayStation 2'?'PS2':p==='Xbox 360'?'X360':'OTHER'}function logo(p){return p==='Xbox 360'?'X360':p.replace('PlayStation ','PS')}function img(g,cls){return g.cover_source?`<div class='${cls}'><img src='${E(g.cover_source)}' onerror="this.parentElement.innerHTML='${logo(g.platform)}'"></div>`:`<div class='${cls}'>${logo(g.platform)}</div>`}async function load(){data=await fetch('/api/games').then(r=>r.json());let s=await fetch('/api/stats').then(r=>r.json());sg.textContent=s.games;sp.textContent=s.packages;ss.textContent=s.size_gb.toLocaleString('de-DE')+' GB';sm.textContent=s.missing;su.textContent=s.updates;pf.innerHTML='<option value="">Alle Plattformen</option>'+Object.keys(s.platforms).sort().map(x=>`<option>${E(x)}</option>`).join('');render()}function render(){let t=q.value.toLowerCase(),p=pf.value,f=sf.value;a=data.filter(g=>(!p||g.platform===p)&&(!t||(g.title+' '+(g.title_id||'')).toLowerCase().includes(t))&&(!f||(f==='missing'&&g.metadata_missing)||(f==='updates'&&g.update_status==='update_available')));list.innerHTML=a.map(g=>`<div class='card ${pc(g.platform)} ${selected===g.id?'on':''}' onclick='show(${g.id})'>${img(g,'cover')}<div class='meta'><span class='tag'>${logo(g.platform)}</span><div class='title'>${E(g.title)}</div><div class='small'>${E(g.title_id||'Keine TitleID')}</div><div class='mut small'>${E(g.publisher||'')} · ${g.packages.length} Pakete</div><div class='badges'>${g.metadata_missing?'<span class="badge warn">Metadaten fehlen</span>':''}${g.update_status==='update_available'?'<span class="badge warn">Update verfügbar</span>':g.update_status==='current'?'<span class="badge ok">Aktuell</span>':''}</div></div></div>`).join('')}function show(id){selected=id;let g=data.find(x=>x.id===id);render();detail.scrollTop=0;let pk=g.packages.map(p=>`<div class='pkg'><span><b>${E(p.name||p.filename)}</b><br><span class='mut small'>${E(p.filename)}</span></span><span>${E(p.category||'–')}</span><span>${E(p.version||'–')}</span><span>${E(p.location||'–')}</span><span>${p.size_gb==null?'–':p.size_gb.toLocaleString('de-DE')+' GB'}</span></div>`).join('');detail.className='detail '+pc(g.platform);detail.innerHTML=`<div class='hero'>${img(g,'heroCover')}<div><span class='tag'>${logo(g.platform)}</span><h1>${E(g.title)}</h1><div class='mut'>${E(g.publisher||'Unbekannt')}${g.developer?' · '+E(g.developer):''}</div><div class='badges'>${g.metadata_source?'<span class="badge">'+E(g.metadata_source)+'</span>':''}</div></div><div class='value'><span class='mut small'>Wert</span><br><b>${E(g.current_value||'–')}</b></div></div><div class='infos'><div class='info'><span class='mut small'>TitleID</span><br><b>${E(g.title_id||'–')}</b></div><div class='info'><span class='mut small'>Genre</span><br><b>${E(g.genres||'–')}</b></div><div class='info'><span class='mut small'>Release</span><br><b>${E(g.release_date||'–')}</b></div><div class='info'><span class='mut small'>Durchgespielt</span><br><b>${g.completed?'Ja':'Nein'}</b></div><div class='info'><span class='mut small'>Lokales Update</span><br><b>${E(g.local_latest_version||'–')}</b></div><div class='info'><span class='mut small'>Online aktuell</span><br><b>${E(g.remote_latest_version||'–')}</b></div><div class='info'><span class='mut small'>Update-Status</span><br><b>${g.update_status==='update_available'?'Update verfügbar':g.update_status==='current'?'Aktuell':'Unbekannt'}</b></div><div class='info'><span class='mut small'>Vollständigkeit</span><br><b>${E(g.completeness||'–')}</b></div></div>${g.description?'<h3>Beschreibung</h3><p>'+E(g.description.replace(/<[^>]*>/g,' ')).slice(0,4000)+'</p>':''}<h3>Backup-Pakete</h3><div class='pkghead'><span>Datei</span><span>Typ</span><span>Version</span><span>Ort</span><span>Größe</span></div>${pk||'<p class="mut">Keine Pakete.</p>'}`;}function modal(v){document.getElementById('modal').classList.toggle('show',v)}async function upload(i,u){let f=document.getElementById(i).files[0];if(!f)return;let d=new FormData();d.append('file',f);msg.textContent='Import läuft';let r=await fetch(u,{method:'POST',body:d});msg.textContent=r.ok?'OK '+JSON.stringify(await r.json()):await r.text();if(r.ok)load()}async function metadata(){if(!confirm('Alle Online-Metadaten und PS4-Updatestände aktualisieren?'))return;let b=document.querySelector('button[onclick="metadata()"]');b.disabled=true;b.textContent='Aktualisierung läuft ...';try{let r=await fetch('/api/metadata/refresh',{method:'POST'});alert(r.ok?JSON.stringify(await r.json()):await r.text());if(r.ok)await load()}finally{b.disabled=false;b.textContent='Metadaten aktualisieren'}}load();
</script></body></html>'''

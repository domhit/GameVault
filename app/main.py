from __future__ import annotations
import html, os, re, json, tempfile, xml.etree.ElementTree as ET
from typing import Optional
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from sqlalchemy import create_engine, String, Text, Float, Boolean, ForeignKey, select, func, inspect, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, Session
from openpyxl import load_workbook
from pathlib import Path
from datetime import datetime, timezone
from .providers import cascade, igdb, ps_resolver
DB=os.getenv("DATABASE_URL","postgresql+psycopg://gamevault:gamevault@db:5432/gamevault")
engine=create_engine(DB,pool_pre_ping=True)
DATA=os.getenv("DATA_DIR","/data")
class Base(DeclarativeBase): pass
class Game(Base):
    __tablename__="games"
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
    cover_provider:Mapped[Optional[str]]=mapped_column(String(120),nullable=True)
    cover_checked_at:Mapped[Optional[str]]=mapped_column(String(50),nullable=True)
    cover_error:Mapped[Optional[str]]=mapped_column(Text,nullable=True)
    metadata_status:Mapped[Optional[str]]=mapped_column(String(40),nullable=True)
    metadata_confidence:Mapped[Optional[float]]=mapped_column(Float,nullable=True)
    metadata_provider:Mapped[Optional[str]]=mapped_column(String(80),nullable=True)
    metadata_provider_id:Mapped[Optional[str]]=mapped_column(String(80),nullable=True)
    metadata_updated_at:Mapped[Optional[str]]=mapped_column(String(50),nullable=True)
    metadata_locked:Mapped[bool]=mapped_column(Boolean,default=False)
    candidate_title:Mapped[Optional[str]]=mapped_column(String(300),nullable=True)
    candidate_provider_id:Mapped[Optional[str]]=mapped_column(String(80),nullable=True)
    identifier_type:Mapped[Optional[str]]=mapped_column(String(40),nullable=True)
    game_modes:Mapped[Optional[str]]=mapped_column(Text,nullable=True)
    perspectives:Mapped[Optional[str]]=mapped_column(Text,nullable=True)
    themes:Mapped[Optional[str]]=mapped_column(Text,nullable=True)
    franchises:Mapped[Optional[str]]=mapped_column(Text,nullable=True)
    engines:Mapped[Optional[str]]=mapped_column(Text,nullable=True)
    multiplayer_json:Mapped[Optional[str]]=mapped_column(Text,nullable=True)
    pricecharting_url:Mapped[Optional[str]]=mapped_column(Text,nullable=True)
    packages:Mapped[list["Package"]]=relationship(back_populates="game",cascade="all,delete-orphan")
class Package(Base):
    __tablename__="packages"
    id:Mapped[int]=mapped_column(primary_key=True)
    filename:Mapped[str]=mapped_column(String(600),unique=True,index=True)
    game_id:Mapped[Optional[int]]=mapped_column(ForeignKey("games.id"),nullable=True,index=True)
    title_id:Mapped[Optional[str]]=mapped_column(String(40),index=True,nullable=True)
    name:Mapped[Optional[str]]=mapped_column(String(400),nullable=True)
    version:Mapped[Optional[str]]=mapped_column(String(40),nullable=True)
    pkg_version:Mapped[Optional[str]]=mapped_column(String(40),nullable=True)
    newest_patch:Mapped[Optional[str]]=mapped_column(String(40),nullable=True)
    decision:Mapped[Optional[str]]=mapped_column(String(80),nullable=True)
    location:Mapped[Optional[str]]=mapped_column(String(80),nullable=True)
    category:Mapped[Optional[str]]=mapped_column(String(40),nullable=True)
    size_gb:Mapped[Optional[float]]=mapped_column(Float,nullable=True)
    game:Mapped[Optional[Game]]=relationship(back_populates="packages")
Base.metadata.create_all(engine)
with engine.begin() as c:
    for col,typ in [("cover_provider","VARCHAR(120)"),("cover_checked_at","VARCHAR(50)"),("cover_error","TEXT"),("metadata_status","VARCHAR(40)"),("metadata_confidence","DOUBLE PRECISION"),("metadata_provider","VARCHAR(80)"),("metadata_provider_id","VARCHAR(80)"),("metadata_updated_at","VARCHAR(50)"),("metadata_locked","BOOLEAN DEFAULT FALSE"),("candidate_title","VARCHAR(300)"),("candidate_provider_id","VARCHAR(80)"),("identifier_type","VARCHAR(40)"),("game_modes","TEXT"),("perspectives","TEXT"),("themes","TEXT"),("franchises","TEXT"),("engines","TEXT"),("multiplayer_json","TEXT")]:
        c.execute(__import__("sqlalchemy").text(f"ALTER TABLE games ADD COLUMN IF NOT EXISTS {col} {typ}"))
app=FastAPI(title="GameVault",version="0.6.0")
def txt(e,path):
    n=e.find(path); return (n.text or "").strip() if n is not None and n.text else None
def disp(e,path): return txt(e,path+"/displayname") or txt(e,path)
def norm_tid(v):
    if not v:return None
    s=re.sub(r"[^A-Za-z0-9]","",str(v)).upper(); m=re.fullmatch(r"CUSA(\d+)",s)
    return "CUSA"+m.group(1).zfill(5) if m else s
def clean(v):
    s=str(v or "")
    s=re.sub(r"\s*\[(Game|Update|Patch|DLC)\]\s*$","",s,flags=re.I)
    s=re.sub(r"\s*[-:]?\s*(Update|Patch|DLC)\s*$","",s,flags=re.I)
    return s.replace("_"," ").strip()
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
            gc=txt(e,"id"); g=db.scalar(select(Game).where(Game.gc_id==gc))
            vals=dict(platform=disp(e,"platform") or "Unbekannt",title=txt(e,"title") or "Ohne Titel",publisher=disp(e,"publisher"),developer=disp(e,"developer"),genres=", ".join(x.text.strip() for x in e.findall("./genres/genre/displayname") if x.text),release_date=txt(e,"releasedate/date"),completed=(e.find("completed") is not None and e.find("completed").attrib.get("boolvalue")=="1"),collection_status=txt(e,"collectionstatus"),completeness=txt(e,"completeness"),current_value=txt(e,"currentvalue"),description=html.unescape(txt(e,"description") or ""),cover_source=txt(e,"coverfront"),pricecharting_url=txt(e,"pricechartingurl"))
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
            tid=norm_tid(get("Title ID")); nm=clean(get("Name")); pkg=db.scalar(select(Package).where(Package.filename==str(fn))); game=pkg.game if pkg and pkg.game else None
            if not game and nm: game=byname.get(key(nm))
            if not game and tid: game=db.scalar(select(Game).where(Game.title_id==tid,Game.platform=="PlayStation 4"))
            if not game and get("Category") in ("Game","Patch"):
                game=Game(platform="PlayStation 4",title=nm or tid or str(fn),title_id=tid); db.add(game); db.flush(); byname[key(game.title)]=game; stubs+=1
            if game and tid and not game.title_id: game.title_id=tid
            vals=dict(game_id=game.id if game else None,title_id=tid,name=nm or None,version=str(get("Version")) if get("Version") is not None else None,pkg_version=str(get("Version pkg")) if get("Version pkg") is not None else None,newest_patch=str(get("Newest Patch")) if get("Newest Patch") is not None else None,decision=str(get("Entscheidung")) if get("Entscheidung") is not None else None,location=str(get("Location")) if get("Location") is not None else None,category=str(get("Category")) if get("Category") is not None else None,size_gb=nfloat(get("Size (GB)")))
            if pkg:
                for k,v in vals.items():setattr(pkg,k,v)
                updated+=1
            else: db.add(Package(filename=str(fn),**vals)); added+=1
        db.commit()
    return {"added":added,"updated":updated,"stubs":stubs}
def serial(g):
    return {"id":g.id,"title":g.title,"platform":g.platform,"title_id":g.title_id,"publisher":g.publisher,"developer":g.developer,"genres":g.genres,"release_date":g.release_date,"completed":g.completed,"collection_status":g.collection_status,"completeness":g.completeness,"current_value":g.current_value,"description":g.description,"cover_source":g.cover_source,"cover_provider":g.cover_provider,"cover_checked_at":g.cover_checked_at,"cover_error":g.cover_error,"metadata_status":g.metadata_status,"metadata_confidence":g.metadata_confidence,"metadata_provider":g.metadata_provider,"metadata_provider_id":g.metadata_provider_id,"metadata_locked":g.metadata_locked,"candidate_title":g.candidate_title,"candidate_provider_id":g.candidate_provider_id,"identifier_type":g.identifier_type,"game_modes":g.game_modes,"perspectives":g.perspectives,"themes":g.themes,"franchises":g.franchises,"engines":g.engines,"multiplayer":json.loads(g.multiplayer_json) if g.multiplayer_json else [],"local_multiplayer":local_multiplayer(g),"local_coop":local_coop(g),"pricecharting_url":g.pricecharting_url,"metadata_missing":not bool(g.publisher and g.developer and g.genres and g.description),"packages":[{"filename":p.filename,"title_id":p.title_id,"name":p.name,"version":p.version,"pkg_version":p.pkg_version,"newest_patch":p.newest_patch,"decision":p.decision,"location":p.location,"category":p.category,"size_gb":p.size_gb} for p in g.packages]}
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

@app.get("/covers/{name}")
def local_cover(name:str):
    p=Path(DATA)/"covers"/Path(name).name
    if not p.exists(): raise HTTPException(404)
    return FileResponse(p)

@app.post("/api/covers/refresh")
def refresh_covers():
    result={"checked":0,"downloaded":0,"missing_id":0,"not_found":0,"by_provider":{}}
    try: catalog=cascade.load_ps4_catalog()
    except Exception as e: catalog={}; result["catalog_error"]=str(e)[:300]
    with Session(engine) as db:
        for g in db.scalars(select(Game).where(Game.platform.in_(["PlayStation 4","PlayStation 3","PlayStation 2"]))).all():
            result["checked"]+=1
            if not g.title_id:
                result["missing_id"]+=1;g.cover_error="Keine TitleID/Serial vorhanden";continue
            path,provider,url,errors=cascade.save_first(cascade.candidates(g.platform,g.title_id,catalog),g.id,DATA)
            g.cover_checked_at=datetime.now(timezone.utc).isoformat()
            if path:
                g.cover_source=path;g.cover_provider=provider;g.cover_error=None;result["downloaded"]+=1;result["by_provider"][provider]=result["by_provider"].get(provider,0)+1
            else:
                g.cover_error="; ".join(errors[-4:]) or "Kein Provider-Kandidat";result["not_found"]+=1
        db.commit()
    return result


def completeness(g):
    fields=[g.title_id,g.publisher,g.developer,g.genres,g.release_date,g.description,g.cover_source]
    return round(100*sum(bool(x) for x in fields)/len(fields))
def apply_igdb(g,m):
    if not g.metadata_locked:
        g.title=g.title or m.get('title')
        g.publisher=g.publisher or m.get('publisher');g.developer=g.developer or m.get('developer')
        g.genres=g.genres or m.get('genres');g.release_date=g.release_date or m.get('release_date');g.description=g.description or m.get('description')
        if not g.cover_source and m.get('cover_url'):
            g.cover_source=igdb.download_cover(m['cover_url'],g.id,DATA);g.cover_provider='IGDB' if g.cover_source else g.cover_provider
    g.metadata_provider='IGDB';g.metadata_provider_id=str(m.get('igdb_id'));g.metadata_confidence=m.get('confidence');g.metadata_status='complete' if completeness(g)>=85 else 'partial';g.metadata_updated_at=datetime.now(timezone.utc).isoformat();g.candidate_title=None;g.candidate_provider_id=None


def local_multiplayer(g):
 try:return any((x.get('offlinemax') or 0)>1 or x.get('splitscreen') for x in json.loads(g.multiplayer_json or '[]'))
 except:return False
def local_coop(g):
 try:return any(x.get('offlinecoop') or x.get('campaigncoop') for x in json.loads(g.multiplayer_json or '[]'))
 except:return False
def set_identifier_type(g):
 g.identifier_type={'PlayStation 4':'CUSA','PlayStation 3':'SERIAL','PlayStation 2':'SERIAL','Xbox 360':'TITLEID'}.get(g.platform)
def apply_extended(g,m):
 apply_igdb(g,m)
 for f in ['game_modes','perspectives','themes','franchises','engines']:
  if m.get(f):setattr(g,f,m[f])
 g.multiplayer_json=json.dumps(m.get('multiplayer_modes') or [])
def merge_games(db,target,source):
 for f in ['title_id','publisher','developer','genres','release_date','description','cover_source','current_value','collection_status','completeness','game_modes','perspectives','themes','franchises','engines','multiplayer_json','metadata_provider','metadata_provider_id']:
  if not getattr(target,f,None) and getattr(source,f,None):setattr(target,f,getattr(source,f))
 target.completed=target.completed or source.completed
 for p in list(source.packages):p.game=target
 db.flush();db.delete(source)
@app.get('/api/duplicates')
def duplicates():
 from difflib import SequenceMatcher
 with Session(engine) as db:
  gs=db.scalars(select(Game).where(Game.platform=='PlayStation 4')).all();out=[]
  for i,a in enumerate(gs):
   for b in gs[i+1:]:
    score=1.0 if a.title_id and b.title_id and a.title_id==b.title_id else SequenceMatcher(None,key(a.title),key(b.title)).ratio()
    if score>=.94:out.append({'a':serial(a),'b':serial(b),'score':round(score,3)})
  return out
@app.post('/api/duplicates/merge/{target_id}/{source_id}')
def merge_duplicate(target_id:int,source_id:int):
 with Session(engine) as db:
  a,b=db.get(Game,target_id),db.get(Game,source_id)
  if not a or not b:raise HTTPException(404)
  if a.platform!=b.platform:raise HTTPException(400,'Plattformen unterscheiden sich')
  merge_games(db,a,b);db.commit();return {'ok':True}
@app.put('/api/games/{game_id}')
def edit_game(game_id:int,payload:dict):
 allowed=['title','title_id','publisher','developer','genres','release_date','description','current_value','completed','collection_status','completeness']
 with Session(engine) as db:
  g=db.get(Game,game_id)
  if not g:raise HTTPException(404)
  for f in allowed:
   if f in payload:setattr(g,f,payload[f] if payload[f] not in ('',None) else None)
  if g.title_id:g.title_id=norm_tid(g.title_id) if g.platform=='PlayStation 4' else str(g.title_id).upper()
  set_identifier_type(g);g.metadata_locked=True;g.metadata_status='manual';db.commit();return serial(g)
@app.post('/api/games/{game_id}/resolve')
def resolve_game(game_id:int):
 with Session(engine) as db:
  g=db.get(Game,game_id)
  if not g:raise HTTPException(404)
  resolved=ps_resolver.resolve_ps4(g.title_id) if g.platform=='PlayStation 4' and g.title_id else None
  if resolved and (not g.title or g.title.upper().startswith('CUSA')):g.title=resolved
  hits=igdb.search(resolved or g.title,g.platform,10) if igdb.configured() else []
  if hits:
   m=igdb.extended_by_id(hits[0]['id'])
   if hits[0].get('_confidence',0)>=.90:apply_extended(g,m)
   else:g.metadata_status='review';g.candidate_title=m['title'];g.candidate_provider_id=str(m['igdb_id']);g.metadata_confidence=hits[0].get('_confidence',0)
  set_identifier_type(g);db.commit();return {'resolved_title':resolved,'matches':len(hits),'game':serial(g)}

@app.get('/api/metadata/quality')
def quality():
    with Session(engine) as db:
        gs=db.scalars(select(Game)).all()
        return {'total':len(gs),'complete':sum(completeness(g)>=85 for g in gs),'partial':sum(40<=completeness(g)<85 for g in gs),'missing':sum(completeness(g)<40 for g in gs),'review':sum(g.metadata_status=='review' for g in gs),'without_id':sum(not g.title_id for g in gs),'without_cover':sum(not g.cover_source for g in gs),'igdb_configured':igdb.configured()}

@app.post('/api/metadata/igdb/refresh')
def igdb_refresh():
    if not igdb.configured():raise HTTPException(503,'IGDB ist nicht konfiguriert. IGDB_CLIENT_ID und IGDB_CLIENT_SECRET in Portainer setzen.')
    out={'checked':0,'applied':0,'review':0,'not_found':0,'skipped_locked':0,'errors':0}
    with Session(engine) as db:
        for g in db.scalars(select(Game).order_by(Game.id)).all():
            if g.metadata_locked:out['skipped_locked']+=1;continue
            if completeness(g)>=100:continue
            out['checked']+=1
            try:
                hits=igdb.search(g.title,g.platform)
                if not hits:g.metadata_status='not_found';out['not_found']+=1;continue
                m=igdb.map_record(hits[0])
                if m['confidence']>=0.94:apply_igdb(g,m);out['applied']+=1
                else:g.metadata_status='review';g.metadata_confidence=m['confidence'];g.candidate_title=m['title'];g.candidate_provider_id=str(m['igdb_id']);out['review']+=1
            except Exception as e:g.metadata_status='error';g.cover_error=str(e)[:500];out['errors']+=1
        db.commit()
    return out

@app.get('/api/games/{game_id}/igdb-candidates')
def candidates(game_id:int):
    if not igdb.configured():raise HTTPException(503,'IGDB nicht konfiguriert')
    with Session(engine) as db:
        g=db.get(Game,game_id)
        if not g:raise HTTPException(404)
        return [igdb.map_record(x) for x in igdb.search(g.title,g.platform,10)]

@app.post('/api/games/{game_id}/igdb-accept/{igdb_id}')
def accept(game_id:int,igdb_id:int):
    if not igdb.configured():raise HTTPException(503,'IGDB nicht konfiguriert')
    rows=igdb.post('games',f'fields name,summary,first_release_date,cover.image_id,genres.name,involved_companies.company.name,involved_companies.developer,involved_companies.publisher; where id = {igdb_id}; limit 1;')
    if not rows:raise HTTPException(404,'IGDB-Treffer nicht gefunden')
    rows[0]['_confidence']=1.0
    with Session(engine) as db:
        g=db.get(Game,game_id)
        if not g:raise HTTPException(404)
        apply_igdb(g,igdb.map_record(rows[0]));g.metadata_status='complete' if completeness(g)>=85 else 'partial';g.metadata_locked=True;db.commit();return {'ok':True,'quality':completeness(g)}

@app.post('/api/games/{game_id}/metadata-unlock')
def unlock(game_id:int):
    with Session(engine) as db:
        g=db.get(Game,game_id)
        if not g:raise HTTPException(404)
        g.metadata_locked=False;db.commit();return {'ok':True}

@app.get("/",response_class=HTMLResponse)
def ui(): return HTML
HTML=r'''<!doctype html><html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>GameVault</title><style>
*{box-sizing:border-box}html,body{height:100%;margin:0}body{background:#070d1a;color:#e7edf7;font:14px system-ui,Segoe UI,sans-serif;overflow:hidden}.top{height:72px;display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #1f2937;padding:0 28px;background:#08101e}.brand{font-size:22px;font-weight:800}.mut{color:#8996aa}.shell{height:calc(100vh - 72px);max-width:1500px;margin:auto;padding:18px 24px;display:grid;grid-template-rows:auto auto 1fr;gap:14px}.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}.card,.detail,.bar,.stat{background:#0c1424;border:1px solid #1f2b40;border-radius:16px}.stat{padding:14px 17px}.stat b{font-size:22px;display:block;margin-top:3px}.bar{display:flex;gap:8px;padding:10px}.btn,input,select{background:#111a2b;color:#eef;border:1px solid #283449;padding:10px 12px;border-radius:10px}.btn{cursor:pointer}.blue{background:#2563eb;border-color:#2563eb}.bar input{flex:1}.layout{min-height:0;display:grid;grid-template-columns:minmax(390px,.9fr) minmax(530px,1.35fr);gap:16px}.listpane,.detail{min-height:0;overflow-y:auto;scrollbar-color:#334155 transparent}.listpane{display:grid;grid-template-columns:1fr 1fr;gap:10px;align-content:start;padding-right:4px}.card{padding:0;overflow:hidden;cursor:pointer;min-height:148px;display:grid;grid-template-columns:82px 1fr}.card:hover,.card.on{border-color:#3b82f6;background:#101d34}.cover{background:linear-gradient(145deg,#1e3a5f,#111827);display:flex;align-items:center;justify-content:center;color:#7092ba;font-size:30px;position:relative}.cover img{width:100%;height:100%;object-fit:cover}.meta{padding:13px}.tag{display:inline-block;background:#1d4ed8;padding:4px 7px;border-radius:7px;font-size:10px}.warning{color:#fbbf24}.title{font-size:16px;font-weight:750;margin:10px 0 4px}.small{font-size:12px}.detail{padding:22px}.hero{display:grid;grid-template-columns:145px 1fr auto;gap:20px;align-items:start}.heroCover{width:145px;height:195px;background:linear-gradient(145deg,#1e3a5f,#111827);border-radius:14px;display:flex;align-items:center;justify-content:center;font-size:42px;color:#7092ba;overflow:hidden}.heroCover img{width:100%;height:100%;object-fit:cover}.detail h1{font-size:28px;margin:8px 0}.value{background:#111a2b;border-radius:14px;padding:12px 16px;text-align:right}.value b{font-size:19px}.infos{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin:18px 0}.info{background:#111a2b;border-radius:11px;padding:10px;min-height:59px}.desc{line-height:1.55;color:#bdc8d8;white-space:pre-line}.pkghead,.pkg{display:grid;grid-template-columns:1.6fr .55fr .55fr .65fr .55fr;gap:8px;align-items:center}.pkghead{color:#7f8da3;font-size:11px;padding:8px 0}.pkg{border-top:1px solid #263248;padding:10px 0}.modal{display:none;position:fixed;inset:0;background:#000b;z-index:10;align-items:center;justify-content:center}.modal.show{display:flex}.box{width:min(620px,92vw);background:#0c1424;border:1px solid #33415c;border-radius:18px;padding:20px}.up{border:1px dashed #405170;padding:14px;border-radius:12px;margin:10px 0}@media(max-width:1000px){body{overflow:auto}.shell{height:auto}.layout{grid-template-columns:1fr}.listpane,.detail{overflow:visible}.listpane{grid-template-columns:1fr 1fr}.infos{grid-template-columns:1fr 1fr}}@media(max-width:650px){.stats,.listpane{grid-template-columns:1fr}.hero{grid-template-columns:100px 1fr}.heroCover{width:100px;height:140px}.value{grid-column:1/3}.pkghead{display:none}.pkg{grid-template-columns:1fr 1fr}}

.card{border-left:5px solid var(--accent,#64748b)}.card:hover,.card.on{border-color:var(--accent,#64748b)}.tag{background:var(--accent,#64748b)}.platform-mark{color:var(--accent,#64748b);font-size:16px;font-weight:800}.PS4{--accent:#2166d1}.PS3{--accent:#c33939}.PS2{--accent:#d6a51d}.X360{--accent:#269b45}.OTHER{--accent:#64748b}
</style></head><body><header class="top"><div><div class="brand">GameVault</div><div class="mut small">Sammlung, Backups und Metadaten · v0.6.0</div></div><button class="btn" onclick="igdbRefresh()">IGDB aktualisieren</button> <button class="btn" onclick="covers()">Cover aktualisieren</button> <button class="btn blue" onclick="modal(true)">Import</button></header><main class="shell"><section class="stats"><div class="stat"><span class="mut">Spiele</span><b id="sg">-</b></div><div class="stat"><span class="mut">Backup-Pakete</span><b id="sp">-</b></div><div class="stat"><span class="mut">Backup-Größe</span><b id="ss">-</b></div></section><div class="bar"><input id="q" placeholder="Titel oder TitleID suchen ..." oninput="render()"><select id="pf" onchange="render()"><option value="">Alle Plattformen</option></select><select id="mf" onchange="render()"><option value="">Alle Metadaten</option><option value="missing">Metadaten fehlen</option><option value="review">Zuordnung prüfen</option><option value="cover">Cover fehlt</option><option value="id">TitleID / Serial fehlt</option><option value="localmp">Local Multiplayer</option><option value="localcoop">Local Co-op</option></select></div><div class="layout"><section class="listpane" id="list"></section><aside class="detail" id="detail"><span class="mut">Spiel auswählen</span></aside></div></main><div id="modal" class="modal"><div class="box"><h2>Daten importieren</h2><p class="mut">Game Collector XML zuerst, danach PS4 XLSX. Re-Import aktualisiert vorhandene Datensätze.</p><div class="up"><b>Game Collector XML</b><br><input type="file" id="xml" accept=".xml"><button class="btn" onclick="upload('xml','/api/import/gamecollector')">Importieren</button></div><div class="up"><b>PS4 Paketliste</b><br><input type="file" id="xlsx" accept=".xlsx"><button class="btn" onclick="upload('xlsx','/api/import/packages')">Importieren</button></div><p id="msg"></p><button class="btn" onclick="modal(false)">Schließen</button></div></div><script>
let data=[],selected=null;const PC=p=>p==='PlayStation 4'?'PS4':p==='PlayStation 3'?'PS3':p==='PlayStation 2'?'PS2':p==='Xbox 360'?'X360':'OTHER';const E=s=>(s??'').toString().replace(/[&<>\"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));function img(src,cls){if(!src)return `<div class='${cls} platform-mark'>GV</div>`;return `<div class='${cls}'><img src='${E(src)}' onerror="this.parentElement.classList.add('platform-mark');this.parentElement.innerHTML='GV'"></div>`}async function load(){data=await fetch('/api/games').then(r=>r.json());let s=await fetch('/api/stats').then(r=>r.json());sg.textContent=s.games;sp.textContent=s.packages;ss.textContent=s.size_gb.toLocaleString('de-DE')+' GB';pf.innerHTML='<option value="">Alle Plattformen</option>'+Object.keys(s.platforms).sort().map(x=>`<option>${E(x)}</option>`).join('');render()}function render(){let term=q.value.toLowerCase(),pl=pf.value,missing=mf.value==='missing';let review=mf.value==='review',cover=mf.value==='cover',noid=mf.value==='id',lmp=mf.value==='localmp',lcoop=mf.value==='localcoop';let a=data.filter(g=>(!pl||g.platform===pl)&&(!missing||g.metadata_missing)&&(!review||g.metadata_status==='review')&&(!cover||!g.cover_source)&&(!noid||!g.title_id)&&(!lmp||g.local_multiplayer)&&(!lcoop||g.local_coop)&&(!term||(g.title+' '+(g.title_id||'')).toLowerCase().includes(term)));list.innerHTML=a.map(g=>`<div class='card ${PC(g.platform)} ${selected===g.id?'on':''}' onclick='show(${g.id})'>${img(g.cover_source,'cover')}<div class='meta'><span class='tag'>${E(g.platform)}</span>${g.metadata_missing?` <span class='warning small'>Metadaten fehlen</span>`:''}${g.metadata_status==='review'?` <span class='warning small'>Zuordnung prüfen</span>`:''}<div class='title'>${E(g.title)}</div><div class='small'>${E(g.title_id||'Keine TitleID')}</div><div class='mut small'>${E(g.publisher||'')}${g.packages.length?' · '+g.packages.length+' Pakete':''}</div></div></div>`).join('')}function show(id){selected=id;let g=data.find(x=>x.id===id);render();detail.scrollTop=0;detail.className='detail '+PC(g.platform);let pk=g.packages.map(p=>`<div class='pkg'><span><b>${E(p.name||p.filename)}</b><br><span class='mut small'>${E(p.filename)}</span></span><span>${E(p.category||'–')}</span><span>${E(p.version||'–')}</span><span>${E(p.location||'–')}</span><span>${p.size_gb==null?'–':p.size_gb.toLocaleString('de-DE')+' GB'}</span></div>`).join('');detail.innerHTML=`<div class='hero'>${img(g.cover_source,'heroCover')}<div><span class='tag'>${E(g.platform)}</span>${g.metadata_missing?` <span class='warning'>Metadaten fehlen</span>`:''}<h1>${E(g.title)}</h1><div class='mut'>${E(g.publisher||'Unbekannter Publisher')}${g.developer?' · '+E(g.developer):''}</div></div><div class='value'><span class='mut small'>Aktueller Wert</span><br><b>${E(g.current_value||'–')}</b></div></div><div class='infos'><div class='info'><span class='mut small'>TitleID</span><br><b>${E(g.title_id||'–')}</b></div><div class='info'><span class='mut small'>Genre</span><br><b>${E(g.genres||'–')}</b></div><div class='info'><span class='mut small'>Release</span><br><b>${E(g.release_date||'–')}</b></div><div class='info'><span class='mut small'>Sammlung</span><br><b>${E(g.collection_status||'–')}</b></div><div class='info'><span class='mut small'>Vollständigkeit</span><br><b>${E(g.completeness||'–')}</b></div><div class='info'><span class='mut small'>Durchgespielt</span><br><b>${g.completed?'Ja':'Nein'}</b></div><div class='info'><span class='mut small'>Entwickler</span><br><b>${E(g.developer||'–')}</b></div><div class='info'><span class='mut small'>Backups</span><br><b>${g.packages.length}</b></div></div>${g.description?`<h3>Beschreibung</h3><p class='desc'>${E(g.description.replace(/<[^>]*>/g,' ')).slice(0,4000)}</p>`:''}${g.metadata_status==='review'?`<h3>IGDB-Zuordnung prüfen</h3><p class='warning'>Vorschlag: ${E(g.candidate_title||'')} (${Math.round((g.metadata_confidence||0)*100)} %)</p><button class='btn' onclick='showCandidates(${g.id})'>Treffer anzeigen</button>`:''}<div style='display:flex;gap:8px;flex-wrap:wrap;margin:14px 0'><button class='btn' onclick='editGame(${g.id})'>Metadaten bearbeiten</button><button class='btn' onclick='resolveOne(${g.id})'>ID/IGDB auflösen</button><button class='btn' onclick='showCandidates(${g.id})'>IGDB suchen</button></div><div class='infos'><div class='info'><span class='mut small'>Game Modes</span><br><b>${E(g.game_modes||'–')}</b></div><div class='info'><span class='mut small'>Perspektive</span><br><b>${E(g.perspectives||'–')}</b></div><div class='info'><span class='mut small'>Franchise</span><br><b>${E(g.franchises||'–')}</b></div><div class='info'><span class='mut small'>Engine</span><br><b>${E(g.engines||'–')}</b></div><div class='info'><span class='mut small'>Local Multiplayer</span><br><b>${g.local_multiplayer?'Ja':'Nein'}</b></div><div class='info'><span class='mut small'>Local Co-op</span><br><b>${g.local_coop?'Ja':'Nein'}</b></div></div><h3>Backup-Pakete</h3><div class='pkghead'><span>Datei</span><span>Typ</span><span>Version</span><span>Speicherort</span><span>Größe</span></div>${pk||'<p class="mut">Keine Backup-Pakete zugeordnet.</p>'}`;}function modal(v){document.getElementById('modal').classList.toggle('show',v)}async function upload(i,u){let f=document.getElementById(i).files[0];if(!f)return;let d=new FormData();d.append('file',f);msg.textContent='Import läuft ...';let r=await fetch(u,{method:'POST',body:d});msg.textContent=r.ok?'OK '+JSON.stringify(await r.json()):'Fehler: '+await r.text();if(r.ok)await load()}load();
async function covers(){let b=document.querySelector('button[onclick=\"covers()\"]');if(!confirm('Cover für PS4, PS3 und PS2 über die Provider-Kaskade suchen?'))return;b.disabled=true;b.textContent='Cover-Suche läuft ...';try{let r=await fetch('/api/covers/refresh',{method:'POST'});let x=r.ok?await r.json():await r.text();alert(typeof x==='string'?x:JSON.stringify(x,null,2));if(r.ok)await load()}finally{b.disabled=false;b.textContent='Cover aktualisieren'}}
async function igdbRefresh(){if(!confirm('Fehlende Metadaten über IGDB suchen? Eindeutige Treffer ab 94 % werden automatisch übernommen.'))return;let r=await fetch('/api/metadata/igdb/refresh',{method:'POST'});alert(r.ok?JSON.stringify(await r.json(),null,2):await r.text());if(r.ok)await load()}
async function showCandidates(id){let r=await fetch(`/api/games/${id}/igdb-candidates`);if(!r.ok){alert(await r.text());return}let rows=await r.json();let msg=rows.map((x,i)=>`${i+1}: ${x.title} (${Math.round(x.confidence*100)} %) [IGDB ${x.igdb_id}]`).join('\n');let n=prompt(msg+'\n\nNummer zum Übernehmen:');let x=rows[Number(n)-1];if(!x)return;r=await fetch(`/api/games/${id}/igdb-accept/${x.igdb_id}`,{method:'POST'});alert(r.ok?'Übernommen':await r.text());if(r.ok)await load()}
async function editGame(id){let g=data.find(x=>x.id===id),title=prompt('Titel',g.title);if(title===null)return;let tid=prompt('TitleID / Serial',g.title_id||'');if(tid===null)return;let publisher=prompt('Publisher',g.publisher||'');if(publisher===null)return;let developer=prompt('Developer',g.developer||'');if(developer===null)return;let r=await fetch(`/api/games/${id}`,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({title,title_id:tid,publisher,developer})});alert(r.ok?'Gespeichert':await r.text());if(r.ok){await load();show(id)}}async function resolveOne(id){let r=await fetch(`/api/games/${id}/resolve`,{method:'POST'});alert(r.ok?JSON.stringify(await r.json(),null,2):await r.text());if(r.ok){await load();show(id)}}
</script></body></html>'''

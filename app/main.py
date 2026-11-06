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
from .providers import cascade, igdb
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
    metadata_sources:Mapped[Optional[str]]=mapped_column(Text,nullable=True)
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
    for col,typ in [("cover_provider","VARCHAR(120)"),("cover_checked_at","VARCHAR(50)"),("cover_error","TEXT"),("metadata_status","VARCHAR(40)"),("metadata_confidence","DOUBLE PRECISION"),("metadata_provider","VARCHAR(80)"),("metadata_provider_id","VARCHAR(80)"),("metadata_updated_at","VARCHAR(50)"),("metadata_locked","BOOLEAN DEFAULT FALSE"),("candidate_title","VARCHAR(300)"),("candidate_provider_id","VARCHAR(80)"),("identifier_type","VARCHAR(40)"),("game_modes","TEXT"),("perspectives","TEXT"),("themes","TEXT"),("franchises","TEXT"),("engines","TEXT"),("multiplayer_json","TEXT"),("metadata_sources","TEXT")]:
        c.execute(__import__("sqlalchemy").text(f"ALTER TABLE games ADD COLUMN IF NOT EXISTS {col} {typ}"))
app=FastAPI(title="GameVault",version="0.7.2")
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
def cover_is_local(g):
 return bool(g.cover_source and str(g.cover_source).startswith('/covers/'))
def cover_is_remote(g):
 return bool(g.cover_source and str(g.cover_source).lower().startswith(('http://','https://')))
def cover_is_legacy(g):
 return bool(g.cover_source and not cover_is_local(g) and not cover_is_remote(g))
def source_map(g):
 try:return json.loads(g.metadata_sources or '{}')
 except:return {}
def save_source_map(g,m):g.metadata_sources=json.dumps(m,ensure_ascii=False,sort_keys=True)
def source_of(g,field):return source_map(g).get(field)
def multiplayer_rows(g):
 try:return json.loads(g.multiplayer_json or '[]')
 except:return []
def local_multiplayer(g):return any((x.get('offlinemax') or 0)>1 or x.get('splitscreen') for x in multiplayer_rows(g))
def local_coop(g):return any(x.get('offlinecoop') or x.get('campaigncoop') for x in multiplayer_rows(g))
def online_multiplayer(g):return any((x.get('onlinemax') or 0)>1 or x.get('onlinecoop') for x in multiplayer_rows(g))
def metadata_quality(g):
 critical={'title':g.title,'platform':g.platform,'publisher':g.publisher,'genres':g.genres,'cover':cover_is_local(g)}
 optional={'identifier':g.title_id,'developer':g.developer,'release_date':g.release_date,'description':g.description,'game_modes':g.game_modes,'perspectives':g.perspectives,'themes':g.themes,'franchises':g.franchises,'engines':g.engines}
 missing_critical=[k for k,v in critical.items() if not v]
 missing_optional=[k for k,v in optional.items() if not v]
 score=round(100*((len(critical)-len(missing_critical))*2+(len(optional)-len(missing_optional)))/(len(critical)*2+len(optional)))
 status='critical' if missing_critical else ('partial' if missing_optional else 'complete')
 return {'score':score,'status':status,'missing_critical':missing_critical,'missing_optional':missing_optional}
def serial(g):
    return {"id":g.id,"title":g.title,"platform":g.platform,"title_id":g.title_id,"publisher":g.publisher,"developer":g.developer,"genres":g.genres,"release_date":g.release_date,"completed":g.completed,"collection_status":g.collection_status,"completeness":g.completeness,"current_value":g.current_value,"description":g.description,"cover_source":g.cover_source,"cover_local":cover_is_local(g),"cover_provider":g.cover_provider,"cover_checked_at":g.cover_checked_at,"cover_error":g.cover_error,"metadata_status":g.metadata_status,"metadata_confidence":g.metadata_confidence,"metadata_provider":g.metadata_provider,"metadata_provider_id":g.metadata_provider_id,"metadata_locked":False,"metadata_sources":source_map(g),"candidate_title":g.candidate_title,"candidate_provider_id":g.candidate_provider_id,"identifier_type":g.identifier_type,"game_modes":g.game_modes,"perspectives":g.perspectives,"themes":g.themes,"franchises":g.franchises,"engines":g.engines,"multiplayer":multiplayer_rows(g),"local_multiplayer":local_multiplayer(g),"local_coop":local_coop(g),"online_multiplayer":online_multiplayer(g),"pricecharting_url":g.pricecharting_url,"metadata_quality":metadata_quality(g),"metadata_missing":metadata_quality(g)["status"]=="critical","packages":[{"filename":p.filename,"title_id":p.title_id,"name":p.name,"version":p.version,"pkg_version":p.pkg_version,"newest_patch":p.newest_patch,"decision":p.decision,"location":p.location,"category":p.category,"size_gb":p.size_gb} for p in g.packages]}
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
    fields=[g.title_id,g.publisher,g.developer,g.genres,g.release_date,g.description,cover_is_local(g)]
    return round(100*sum(bool(x) for x in fields)/len(fields))
def apply_igdb(g,m,force=False):
 changed=[];sources=source_map(g)
 # Manual fields are protected. Other catalog fields are refreshed from IGDB.
 mapping={'publisher':'publisher','developer':'developer','genres':'genres','release_date':'release_date','description':'description','game_modes':'game_modes','perspectives':'perspectives','themes':'themes','franchises':'franchises','engines':'engines'}
 for dst,src in mapping.items():
  v=m.get(src)
  if v and sources.get(dst)!='manual' and getattr(g,dst,None)!=v:
   setattr(g,dst,v);sources[dst]='igdb';changed.append(dst)
 # Title is conservative: only replace missing/technical titles unless user explicitly chose force.
 title=m.get('title')
 if title and sources.get('title')!='manual' and (force or not g.title or str(g.title).upper().startswith('CUSA')) and g.title!=title:
  g.title=title;sources['title']='igdb';changed.append('title')
 if m.get('multiplayer_modes') and sources.get('multiplayer')!='manual':
  value=json.dumps(m['multiplayer_modes'])
  if g.multiplayer_json!=value:g.multiplayer_json=value;changed.append('multiplayer')
  sources['multiplayer']='igdb'
 if m.get('cover_url') and sources.get('cover')!='manual':
  if force or not cover_is_local(g) or g.cover_provider=='IGDB':
   cp=igdb.download_cover(m['cover_url'],g.id,DATA)
   if cp and g.cover_source!=cp:g.cover_source=cp;changed.append('cover')
   if cp:g.cover_provider='IGDB';sources['cover']='igdb'
 g.metadata_provider='IGDB';g.metadata_provider_id=str(m.get('igdb_id'));g.metadata_confidence=m.get('confidence');g.metadata_updated_at=datetime.now(timezone.utc).isoformat();g.candidate_title=None;g.candidate_provider_id=None
 save_source_map(g,sources);g.metadata_locked=False
 g.metadata_status='complete' if completeness(g)>=85 else 'partial'
 return changed

@app.get('/api/igdb/test/{igdb_id}')
def igdb_test(igdb_id:int):
 if not igdb.configured():raise HTTPException(503,'IGDB nicht konfiguriert')
 try:
  item=igdb.get_by_id(igdb_id)
  if not item:raise HTTPException(404,'IGDB ID nicht gefunden')
  return {'ok':True,'configured':True,'game':item}
 except HTTPException:raise
 except Exception as e:raise HTTPException(502,f'{type(e).__name__}: {e}')

@app.post('/api/games/{game_id}/resolve-trace')
def resolve_trace(game_id:int):
 out=[]
 with Session(engine) as db:
  g=db.get(Game,game_id)
  if not g:raise HTTPException(404)
  out.append({'step':'Identifier','ok':bool(g.title_id),'detail':g.title_id or 'fehlt'})
  query=g.title
  if g.platform=='PlayStation 4' and g.title_id:
   try:
    from .providers import online
    row=online.ps4_match(online.ps4_catalog(),g.title_id,g.title);resolved=online.pick(row,'title','name') if row else None
    out.append({'step':'PS4 Resolver','ok':bool(resolved),'detail':resolved or 'kein Treffer'})
    if resolved:query=resolved
   except Exception as e:out.append({'step':'PS4 Resolver','ok':False,'detail':str(e)[:250]})
  try:
   hits=igdb.search(query,g.platform,10);out.append({'step':'IGDB Suche','ok':bool(hits),'detail':f'{len(hits)} Treffer für {query}'})
   if hits:
    m=igdb.map_record(hits[0]);out.append({'step':'Bester Treffer','ok':True,'detail':f"{m['title']} · IGDB {m['igdb_id']} · {round(m['confidence']*100)} %"})
    if m['confidence']>=.90:changed=apply_igdb(g,m,force=True);g.metadata_locked=False;db.commit();out.append({'step':'Übernahme','ok':True,'detail':'Aktualisiert: '+(', '.join(changed) if changed else 'keine Änderungen')})
    else:out.append({'step':'Übernahme','ok':False,'detail':'unter 90 %, manuell auswählen'})
  except Exception as e:out.append({'step':'IGDB','ok':False,'detail':f'{type(e).__name__}: {e}'[:300]})
  return {'trace':out}

def duplicate_score(a,b):
 from difflib import SequenceMatcher
 if a.platform!=b.platform:return 0.0,[]
 reasons=[]
 if a.title_id and b.title_id and a.title_id==b.title_id:reasons.append('gleiche TitleID');return 1.0,reasons
 title_score=SequenceMatcher(None,key(a.title),key(b.title)).ratio()
 if title_score>=.94:reasons.append(f'Titel {round(title_score*100)} %')
 if a.metadata_provider_id and b.metadata_provider_id and a.metadata_provider_id==b.metadata_provider_id:reasons.append('gleiche IGDB-ID');title_score=max(title_score,.99)
 return title_score,reasons

def preferred_merge_target(a,b):
 # Prefer the Game Collector record because it owns collection/value/completion history.
 if bool(a.gc_id)!=bool(b.gc_id):return (a,b) if a.gc_id else (b,a)
 # Then prefer the richer record.
 def richness(g):return sum(bool(x) for x in [g.title_id,g.publisher,g.developer,g.genres,g.description,g.cover_source,g.current_value,g.metadata_provider_id])+len(g.packages)
 return (a,b) if richness(a)>=richness(b) else (b,a)

def conflict_fields(a,b):
 fields=['title','title_id','publisher','developer','genres','release_date','current_value','collection_status','completeness','metadata_provider_id']
 return [{'field':f,'target':getattr(a,f,None),'source':getattr(b,f,None)} for f in fields if getattr(a,f,None) and getattr(b,f,None) and str(getattr(a,f))!=str(getattr(b,f))]

@app.get('/api/duplicates')
def duplicate_list():
 with Session(engine) as db:
  gs=db.scalars(select(Game)).all();out=[]
  for i,a in enumerate(gs):
   for b in gs[i+1:]:
    score,reasons=duplicate_score(a,b)
    if score>=.94:
     keep,merge=preferred_merge_target(a,b)
     out.append({'keep':serial(keep),'merge':serial(merge),'score':round(score,3),'reasons':reasons,'conflicts':conflict_fields(keep,merge)})
  return sorted(out,key=lambda x:x['score'],reverse=True)

@app.post('/api/duplicates/merge/{target_id}/{source_id}')
def duplicate_merge(target_id:int,source_id:int):
 with Session(engine) as db:
  a,b=db.get(Game,target_id),db.get(Game,source_id)
  if not a or not b:raise HTTPException(404)
  if a.platform!=b.platform:raise HTTPException(400,'Plattformen unterscheiden sich')
  moved=len(b.packages);changed=[];sources=source_map(a);bsources=source_map(b)
  # Missing target fields are inherited. Existing target values win, especially Game Collector collection data.
  for f in ['title_id','publisher','developer','genres','release_date','description','cover_source','cover_provider','current_value','collection_status','completeness','game_modes','perspectives','themes','franchises','engines','multiplayer_json','metadata_provider','metadata_provider_id','pricecharting_url']:
   if not getattr(a,f,None) and getattr(b,f,None):
    setattr(a,f,getattr(b,f));changed.append(f)
    if bsources.get(f):sources[f]=bsources[f]
  a.completed=a.completed or b.completed
  for pkg in list(b.packages):pkg.game=a
  save_source_map(a,sources);db.flush();db.delete(b);db.commit()
  return {'ok':True,'target':a.id,'removed':source_id,'packages_moved':moved,'fields_inherited':changed}

@app.post('/api/covers/localize')
def localize_covers():
 result={'checked':0,'already_local':0,'downloaded':0,'legacy_cleared':0,'remote_failed':0,'provider_fallback':0,'no_cover':0}
 try:catalog=cascade.load_ps4_catalog()
 except Exception:catalog={}
 with Session(engine) as db:
  for g in db.scalars(select(Game).order_by(Game.id)).all():
   result['checked']+=1
   if cover_is_local(g):result['already_local']+=1;continue
   old=g.cover_source
   # First try existing remote URL, if any.
   if cover_is_remote(g):
    try:
     path,provider,url,errors=cascade.save_first([(g.cover_source,g.cover_provider or 'existing remote')],g.id,DATA)
     if path:g.cover_source=path;g.cover_provider=provider;g.cover_error=None;result['downloaded']+=1;continue
    except Exception:pass
    result['remote_failed']+=1
   # Legacy Game Collector paths are not usable in the web container.
   if cover_is_legacy(g):g.cover_source=None;g.cover_provider=None;result['legacy_cleared']+=1
   # Try platform cascade next.
   try:
    items=cascade.candidates(g.platform,g.title_id,catalog)
    path,provider,url,errors=cascade.save_first(items,g.id,DATA)
    if path:g.cover_source=path;g.cover_provider=provider;g.cover_error=None;result['provider_fallback']+=1;continue
   except Exception as e:g.cover_error=str(e)[:400]
   # Finally use IGDB by known id or title/platform.
   if igdb.configured():
    try:
     m=igdb.get_by_id(int(g.metadata_provider_id)) if g.metadata_provider=='IGDB' and g.metadata_provider_id and str(g.metadata_provider_id).isdigit() else None
     if not m:
      hits=igdb.search(g.title,g.platform,5);m=igdb.map_record(hits[0]) if hits else None
     if m and m.get('cover_url'):
      cp=igdb.download_cover(m['cover_url'],g.id,DATA)
      if cp:g.cover_source=cp;g.cover_provider='IGDB';g.cover_error=None;result['downloaded']+=1;continue
    except Exception as e:g.cover_error=str(e)[:400]
   result['no_cover']+=1
  db.commit()
 return result

@app.get('/api/data-quality')
def data_quality():
 with Session(engine) as db:
  gs=db.scalars(select(Game).order_by(Game.title)).all()
  rows=[]
  for g in gs:
   q=metadata_quality(g)
   if q['status']!='complete' or not g.title_id or not cover_is_local(g) or g.metadata_status=='review':
    rows.append({'id':g.id,'title':g.title,'platform':g.platform,'quality':q,'without_id':not bool(g.title_id),'without_cover':not cover_is_local(g),'review':g.metadata_status=='review'})
  return rows

@app.get('/api/metadata/quality')
def quality():
    with Session(engine) as db:
        gs=db.scalars(select(Game)).all()
        return {'total':len(gs),'complete':sum(metadata_quality(g)['status']=='complete' for g in gs),'partial':sum(metadata_quality(g)['status']=='partial' for g in gs),'missing':sum(metadata_quality(g)['status']=='critical' for g in gs),'review':sum(g.metadata_status=='review' for g in gs),'without_id':sum(not g.title_id for g in gs),'without_cover':sum(not cover_is_local(g) for g in gs),'igdb_configured':igdb.configured()}

@app.post('/api/metadata/igdb/refresh')
def igdb_refresh():
 if not igdb.configured():raise HTTPException(503,'IGDB ist nicht konfiguriert.')
 out={'checked':0,'resolved_by_id':0,'resolved_by_title':0,'applied':0,'review':0,'not_found':0,'errors':0,'changed_fields':0}
 with Session(engine) as db:
  games=db.scalars(select(Game).order_by(Game.id)).all()
  for g in games:
   out['checked']+=1
   try:
    # Same resolver order as the detail action: known IGDB ID, CUSA-title resolution, then title/platform search.
    m=None
    if g.metadata_provider=='IGDB' and g.metadata_provider_id and str(g.metadata_provider_id).isdigit():
     m=igdb.get_by_id(int(g.metadata_provider_id));out['resolved_by_id']+=1 if m else 0
    query=g.title
    if not m and g.platform=='PlayStation 4' and g.title_id:
     try:
      from .providers import online
      row=online.ps4_match(online.ps4_catalog(),g.title_id,g.title);resolved=online.pick(row,'title','name') if row else None
      if resolved:query=resolved
     except Exception:pass
    if not m:
     hits=igdb.search(query,g.platform,10)
     if hits and hits[0].get('_confidence',0)>=.90:
      m=igdb.get_by_id(hits[0]['id']) or igdb.map_record(hits[0]);out['resolved_by_title']+=1
     elif hits:
      best=igdb.map_record(hits[0]);g.metadata_status='review';g.metadata_confidence=best['confidence'];g.candidate_title=best['title'];g.candidate_provider_id=str(best['igdb_id']);out['review']+=1;db.commit();continue
    if not m:g.metadata_status='not_found';out['not_found']+=1;db.commit();continue
    changed=apply_igdb(g,m,force=False);out['changed_fields']+=len(changed);out['applied']+=1;db.commit()
   except Exception as e:
    db.rollback();g=db.get(Game,g.id);g.metadata_status='error';g.cover_error=str(e)[:500];db.commit();out['errors']+=1
 return out

@app.put('/api/games/{game_id}/metadata')
def edit_metadata(game_id:int,payload:dict):
 allowed={'title','title_id','identifier_type','publisher','developer','genres','release_date','description','current_value','collection_status','completeness','completed','game_modes','perspectives','themes','franchises','engines','pricecharting_url','cover_source'}
 with Session(engine) as db:
  g=db.get(Game,game_id)
  if not g:raise HTTPException(404,'Spiel nicht gefunden')
  changed=[]
  for f in allowed:
   if f in payload:
    v=payload[f]
    v=None if v in ('',None) else v
    if getattr(g,f,None)!=v:setattr(g,f,v);changed.append(f)
  if g.title_id:
   nv=norm_tid(g.title_id) if g.platform=='PlayStation 4' else str(g.title_id).strip().upper()
   if nv!=g.title_id:g.title_id=nv;changed.append('title_id_normalized')
  if not g.identifier_type:g.identifier_type={'PlayStation 4':'CUSA','PlayStation 3':'SERIAL','PlayStation 2':'SERIAL','Xbox 360':'TITLEID'}.get(g.platform,'OTHER')
  sources=source_map(g)
  for f in changed:
   if f!='title_id_normalized':sources[f]='manual'
  save_source_map(g,sources);g.metadata_locked=False;g.metadata_status='manual';db.commit();db.refresh(g)
  return {'game':serial(g),'changed':changed}

@app.post('/api/games/{game_id}/igdb-direct/{igdb_id}')
def direct_igdb(game_id:int,igdb_id:int):
 if not igdb.configured():raise HTTPException(503,'IGDB nicht konfiguriert')
 try:m=igdb.get_by_id(igdb_id)
 except Exception as e:raise HTTPException(502,f'IGDB Fehler: {type(e).__name__}: {e}')
 if not m:raise HTTPException(404,'IGDB ID nicht gefunden')
 with Session(engine) as db:
  g=db.get(Game,game_id)
  if not g:raise HTTPException(404,'Spiel nicht gefunden')
  changed=apply_igdb(g,m,force=True)
  g.metadata_locked=False;db.commit();db.refresh(g)
  return {'game':serial(g),'changed':changed,'igdb_id':igdb_id}

@app.post('/api/games/{game_id}/cover-from-url')
def cover_from_url(game_id:int,payload:dict):
 url=str(payload.get('url') or '').strip()
 if not url.startswith(('http://','https://')):raise HTTPException(400,'HTTP/HTTPS Cover-URL erforderlich')
 with Session(engine) as db:
  g=db.get(Game,game_id)
  if not g:raise HTTPException(404,'Spiel nicht gefunden')
  path,provider,source_url,errors=cascade.save_first([(url,'manual URL')],g.id,DATA)
  if not path:raise HTTPException(502,'Cover konnte nicht geladen werden')
  g.cover_source=path;g.cover_provider='manual URL';sources=source_map(g);sources['cover']='manual';save_source_map(g,sources);db.commit();return {'cover_source':path}

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
        apply_igdb(g,igdb.map_record(rows[0]),force=True);g.metadata_status='complete' if completeness(g)>=85 else 'partial';g.metadata_locked=False;db.commit();return {'ok':True,'quality':completeness(g)}

@app.post('/api/games/{game_id}/metadata-unlock')
def unlock(game_id:int):
    with Session(engine) as db:
        g=db.get(Game,game_id)
        if not g:raise HTTPException(404)
        g.metadata_locked=False;db.commit();return {'ok':True,'note':'global lock deprecated; manual field sources remain protected'}

@app.get("/",response_class=HTMLResponse)
def ui(): return HTML
HTML=r'''<!doctype html><html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>GameVault</title><style>
*{box-sizing:border-box}html,body{height:100%;margin:0}body{background:#070d1a;color:#e7edf7;font:14px system-ui,Segoe UI,sans-serif;overflow:hidden}.top{height:72px;display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #1f2937;padding:0 28px;background:#08101e}.brand{font-size:22px;font-weight:800}.mut{color:#8996aa}.shell{height:calc(100vh - 72px);max-width:1500px;margin:auto;padding:18px 24px;display:grid;grid-template-rows:auto auto 1fr;gap:14px}.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}.card,.detail,.bar,.stat{background:#0c1424;border:1px solid #1f2b40;border-radius:16px}.stat{padding:14px 17px}.stat b{font-size:22px;display:block;margin-top:3px}.bar{display:flex;gap:8px;padding:10px}.btn,input,select{background:#111a2b;color:#eef;border:1px solid #283449;padding:10px 12px;border-radius:10px}.btn{cursor:pointer}.blue{background:#2563eb;border-color:#2563eb}.bar input{flex:1}.layout{min-height:0;display:grid;grid-template-columns:minmax(390px,.9fr) minmax(530px,1.35fr);gap:16px}.listpane,.detail{min-height:0;overflow-y:auto;scrollbar-color:#334155 transparent}.listpane{display:grid;grid-template-columns:1fr 1fr;gap:10px;align-content:start;padding-right:4px}.card{padding:0;overflow:hidden;cursor:pointer;min-height:148px;display:grid;grid-template-columns:82px 1fr}.card:hover,.card.on{border-color:#3b82f6;background:#101d34}.cover{background:linear-gradient(145deg,#1e3a5f,#111827);display:flex;align-items:center;justify-content:center;color:#7092ba;font-size:30px;position:relative}.cover img{width:100%;height:100%;object-fit:cover}.meta{padding:13px}.tag{display:inline-block;background:#1d4ed8;padding:4px 7px;border-radius:7px;font-size:10px}.warning{color:#fbbf24}.title{font-size:16px;font-weight:750;margin:10px 0 4px}.small{font-size:12px}.detail{padding:22px}.hero{display:grid;grid-template-columns:145px 1fr auto;gap:20px;align-items:start}.heroCover{width:145px;height:195px;background:linear-gradient(145deg,#1e3a5f,#111827);border-radius:14px;display:flex;align-items:center;justify-content:center;font-size:42px;color:#7092ba;overflow:hidden}.heroCover img{width:100%;height:100%;object-fit:cover}.detail h1{font-size:28px;margin:8px 0}.value{background:#111a2b;border-radius:14px;padding:12px 16px;text-align:right}.value b{font-size:19px}.infos{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin:18px 0}.info{background:#111a2b;border-radius:11px;padding:10px;min-height:59px}.desc{line-height:1.55;color:#bdc8d8;white-space:pre-line}.pkghead,.pkg{display:grid;grid-template-columns:1.6fr .55fr .55fr .65fr .55fr;gap:8px;align-items:center}.pkghead{color:#7f8da3;font-size:11px;padding:8px 0}.pkg{border-top:1px solid #263248;padding:10px 0}.modal{display:none;position:fixed;inset:0;background:#000b;z-index:10;align-items:center;justify-content:center}.modal.show{display:flex}.box{width:min(620px,92vw);background:#0c1424;border:1px solid #33415c;border-radius:18px;padding:20px}.up{border:1px dashed #405170;padding:14px;border-radius:12px;margin:10px 0}@media(max-width:1000px){body{overflow:auto}.shell{height:auto}.layout{grid-template-columns:1fr}.listpane,.detail{overflow:visible}.listpane{grid-template-columns:1fr 1fr}.infos{grid-template-columns:1fr 1fr}}@media(max-width:650px){.stats,.listpane{grid-template-columns:1fr}.hero{grid-template-columns:100px 1fr}.heroCover{width:100px;height:140px}.value{grid-column:1/3}.pkghead{display:none}.pkg{grid-template-columns:1fr 1fr}}

.card{border-left:5px solid var(--accent,#64748b)}.card:hover,.card.on{border-color:var(--accent,#64748b)}.tag{background:var(--accent,#64748b)}.platform-mark{color:var(--accent,#64748b);font-size:16px;font-weight:800}.PS4{--accent:#2166d1}.PS3{--accent:#c33939}.PS2{--accent:#d6a51d}.X360{--accent:#269b45}.OTHER{--accent:#64748b}
.editor-actions{display:flex;gap:8px;flex-wrap:wrap;margin:18px 0}.editor-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}.editor-grid label{display:flex;flex-direction:column;gap:4px}.editor-grid textarea{min-height:90px}.wide{grid-column:1/-1}.spinner{display:inline-block;width:15px;height:15px;border:2px solid #64748b;border-top-color:#fff;border-radius:50%;animation:spin .7s linear infinite}@keyframes spin{to{transform:rotate(360deg)}}.candidate{display:grid;grid-template-columns:60px 1fr auto;gap:10px;padding:9px;border-top:1px solid #263248}.candidate img{width:55px;height:75px;object-fit:cover}.actions{display:flex;justify-content:flex-end;gap:8px;margin-top:12px}.global-busy{display:none;position:fixed;right:20px;bottom:20px;z-index:99;background:#172238;border:1px solid #3b82f6;border-radius:12px;padding:12px 16px;box-shadow:0 8px 30px #0008}.global-busy.show{display:block}.field-card{border-left:4px solid #3b82f6}.field-critical{border-left-color:#ef4444;background:#281318}.field-optional{border-left-color:#eab308;background:#27220f}.field-manual{border-left-color:#f59e0b}.field-auto{border-left-color:#3b82f6}.qualitybar{height:8px;background:#172238;border-radius:99px;overflow:hidden}.qualitybar>span{display:block;height:100%;background:#3b82f6}.top-actions{display:flex;gap:7px;flex-wrap:wrap;justify-content:flex-end}.app-dialog{display:none;position:fixed;inset:0;background:#000c;z-index:300;align-items:center;justify-content:center;padding:16px}.app-dialog.show{display:flex}.dialog-card{background:#0c1424;border:1px solid #33415c;border-radius:16px;padding:18px;width:min(580px,96vw);max-height:85vh;overflow:auto}.dialog-actions{display:flex;gap:8px;justify-content:flex-end;margin-top:14px}@media(max-width:700px){.top{height:auto;min-height:72px;padding:12px 14px;gap:10px;align-items:flex-start}.top-actions{max-width:60%}.shell{height:auto;padding:10px}.bar{position:sticky;top:0;z-index:4}.editor-grid{grid-template-columns:1fr}.wide{grid-column:auto}.dialog-card{width:100%}.btn{min-height:42px}.detail{padding:14px}}
.editor-modal{padding:clamp(8px,2vh,20px);overflow:hidden;overscroll-behavior:contain}
.editor-box{padding:0!important;width:min(860px,96vw)!important;height:min(860px,calc(100vh - 24px));height:min(860px,calc(100dvh - 24px));max-height:calc(100vh - 24px)!important;max-height:calc(100dvh - 24px)!important;display:flex;flex-direction:column;overflow:hidden;border-radius:18px}
.editor-header{flex:0 0 auto;display:flex;align-items:center;justify-content:space-between;gap:12px;padding:14px 18px;border-bottom:1px solid #263248;background:#0c1424;z-index:2}
.editor-header h2{margin:0}.editor-close{display:none}
.editor-scroll{flex:1 1 auto;min-height:0;overflow-y:auto;overflow-x:hidden;-webkit-overflow-scrolling:touch;overscroll-behavior:contain;padding:16px 18px 24px;touch-action:pan-y}
.editor-footer{flex:0 0 auto;margin:0!important;padding:12px 18px calc(12px + env(safe-area-inset-bottom));border-top:1px solid #263248;background:#0c1424;z-index:3;box-shadow:0 -8px 24px #0005}
.editor-footer .btn{min-width:110px}
body.editor-open{overflow:hidden;touch-action:none}
body.editor-open .editor-scroll{touch-action:pan-y}
@media(max-width:1000px){.editor-box{width:min(820px,calc(100vw - 20px))!important}.editor-grid{grid-template-columns:1fr 1fr}}
@media(max-width:700px){.editor-modal{padding:0;align-items:stretch}.editor-box{width:100vw!important;height:100vh;height:100dvh;max-height:100vh!important;max-height:100dvh!important;border-radius:0}.editor-header{padding:12px 14px}.editor-close{display:inline-flex}.editor-scroll{padding:14px 14px 28px}.editor-grid{grid-template-columns:1fr!important}.wide{grid-column:auto!important}.editor-footer{padding:10px 14px calc(10px + env(safe-area-inset-bottom));display:grid!important;grid-template-columns:1fr 1fr}.editor-footer .btn{width:100%;min-height:46px}}
@media(max-height:850px) and (min-width:701px){.editor-box{height:calc(100vh - 20px);height:calc(100dvh - 20px)}.editor-header{padding:10px 16px}.editor-scroll{padding:12px 16px 20px}.editor-grid{gap:8px}.editor-grid label{gap:3px}.editor-footer{padding:9px 16px}.editor-grid textarea{min-height:72px}}
.wide-dialog{width:min(980px,96vw)}.dq-row,.dup-row{border:1px solid #263248;border-radius:12px;padding:12px;margin:8px 0;background:#0a1220}.dup-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}.conflict{color:#fbbf24;font-size:12px}.score-pill{display:inline-block;padding:3px 7px;border-radius:99px;background:#17335d;color:#93c5fd}@media(max-width:700px){.dup-grid{grid-template-columns:1fr}.wide-dialog{width:100%}}</style></head><body><header class="top"><div><div class="brand">GameVault</div><div class="mut small">Sammlung, Backups und Metadaten · v0.7.2</div></div><div class="top-actions"><button class="btn" onclick="openQuality()">Datenqualität</button><button class="btn" onclick="openDuplicates()">Duplikate</button><button class="btn" onclick="igdbRefresh()">IGDB aktualisieren</button><button class="btn" onclick="localizeCovers()">Cover lokal speichern</button><button class="btn" onclick="covers()">Cover aktualisieren</button><button class="btn blue" onclick="modal(true)">Import</button></div></header><main class="shell"><section class="stats"><div class="stat"><span class="mut">Spiele</span><b id="sg">-</b></div><div class="stat"><span class="mut">Backup-Pakete</span><b id="sp">-</b></div><div class="stat"><span class="mut">Backup-Größe</span><b id="ss">-</b></div></section><div class="bar"><input id="q" placeholder="Titel oder TitleID suchen ..." oninput="render()"><select id="pf" onchange="render()"><option value="">Alle Plattformen</option></select><select id="mf" onchange="render()"><option value="">Alle Metadaten</option><option value="missing">Metadaten fehlen</option><option value="review">Zuordnung prüfen</option><option value="cover">Cover fehlt</option><option value="id">TitleID / Serial fehlt</option><option value="localmp">Local Multiplayer</option><option value="localcoop">Local Co-op</option><option value="onlinemp">Online Multiplayer</option></select></div><div class="layout"><section class="listpane" id="list"></section><aside class="detail" id="detail"><span class="mut">Spiel auswählen</span></aside></div></main><div id="modal" class="modal"><div class="box"><h2>Daten importieren</h2><p class="mut">Game Collector XML zuerst, danach PS4 XLSX. Re-Import aktualisiert vorhandene Datensätze.</p><div class="up"><b>Game Collector XML</b><br><input type="file" id="xml" accept=".xml"><button class="btn" onclick="upload('xml','/api/import/gamecollector')">Importieren</button></div><div class="up"><b>PS4 Paketliste</b><br><input type="file" id="xlsx" accept=".xlsx"><button class="btn" onclick="upload('xlsx','/api/import/packages')">Importieren</button></div><p id="msg"></p><button class="btn" onclick="modal(false)">Schließen</button></div></div><div id="editorModal" class="modal editor-modal"><div class="box editor-box"><div class="editor-header"><h2>Metadaten bearbeiten</h2><button type="button" class="btn editor-close" onclick="closeEditor()" aria-label="Schließen">Schließen</button></div><div class="editor-scroll"><div class="editor-grid"><label>Titel<input id="edTitle"></label><label>Plattform<input id="edPlatform" disabled></label><label>Identifier<select id="edType"><option>CUSA</option><option>SERIAL</option><option>TITLEID</option><option>OTHER</option></select></label><label>TitleID / Serial<input id="edTid"></label><label>IGDB ID<input id="edIgdb"></label><label>Publisher<input id="edPublisher"></label><label>Developer<input id="edDeveloper"></label><label>Genre<input id="edGenres"></label><label>Release<input id="edRelease"></label><label>Wert<input id="edValue"></label><label>Game Modes<input id="edModes"></label><label>Perspektive<input id="edPerspective"></label><label>Themes<input id="edThemes"></label><label>Franchise<input id="edFranchise"></label><label>Engine<input id="edEngine"></label><label>Sammlungsstatus<input id="edCollection"></label><label>Vollständigkeit<input id="edCompleteness"></label><label>PriceCharting URL<input id="edPriceUrl"></label><label>Cover URL<input id="edCoverUrl" placeholder="https://..."></label><label class="wide">Beschreibung<textarea id="edDescription"></textarea></label></div></div><div class="actions editor-footer"><button class="btn" onclick="closeEditor()">Abbrechen</button><button class="btn blue" id="saveBtn" onclick="saveMetadata()">Speichern</button></div></div></div><div id="igdbModal" class="modal"><div class="box"><h2>IGDB suchen</h2><div id="igdbState"></div><div id="igdbResults"></div><div style="display:flex;gap:8px;margin-top:12px"><input id="directId" placeholder="IGDB ID direkt" style="flex:1"><button class="btn" onclick="directLoad()">ID laden</button></div><div class="actions"><button class="btn" onclick="closeIgdb()">Schließen</button></div></div></div><div id="traceModal" class="modal"><div class="box"><h2>ID / IGDB auflösen</h2><div id="traceState"><span class="spinner"></span> Suche läuft ...</div><div id="traceRows"></div><div class="actions"><button class="btn" onclick="traceModal.classList.remove('show')">Schließen</button></div></div></div><div id="globalBusy" class="global-busy"><span class="spinner"></span> <span id="busyText">Abfrage läuft ...</span></div><div id="qualityModal" class="app-dialog"><div class="dialog-card wide-dialog"><h2>Datenqualität</h2><div id="qualityBody"></div><div class="dialog-actions"><button class="btn" onclick="qualityModal.classList.remove('show')">Schließen</button></div></div></div><div id="duplicatesModal" class="app-dialog"><div class="dialog-card wide-dialog"><h2>Mögliche Duplikate</h2><div id="duplicatesBody"></div><div class="dialog-actions"><button class="btn" onclick="duplicatesModal.classList.remove('show')">Schließen</button></div></div></div><div id="appDialog" class="app-dialog"><div class="dialog-card"><h2 id="appDialogTitle">GameVault</h2><div id="appDialogBody"></div><div class="dialog-actions"><button id="appDialogCancel" class="btn">Abbrechen</button><button id="appDialogOk" class="btn blue">OK</button></div></div></div><script>
let data=[],selected=null;
function appMessage(title,html){return new Promise(resolve=>{appDialogTitle.textContent=title;appDialogBody.innerHTML=html;appDialogCancel.style.display='none';appDialogOk.textContent='OK';appDialogOk.onclick=()=>{appDialog.classList.remove('show');resolve(true)};appDialog.classList.add('show')})}
function appConfirm(title,html){return new Promise(resolve=>{appDialogTitle.textContent=title;appDialogBody.innerHTML=html;appDialogCancel.style.display='inline-block';appDialogOk.textContent='Bestätigen';appDialogCancel.onclick=()=>{appDialog.classList.remove('show');resolve(false)};appDialogOk.onclick=()=>{appDialog.classList.remove('show');resolve(true)};appDialog.classList.add('show')})}
function fieldClass(g,key,value,critical=false){let src=(g.metadata_sources||{})[key];if(src==='manual')return 'field-card field-manual';if(!value)return 'field-card '+(critical?'field-critical':'field-optional');return 'field-card field-auto'}

let busyCount=0;function busy(on,text='Abfrage läuft ...'){busyCount=Math.max(0,busyCount+(on?1:-1));if(text)busyText.textContent=text;globalBusy.classList.toggle('show',busyCount>0)}
const PC=p=>p==='PlayStation 4'?'PS4':p==='PlayStation 3'?'PS3':p==='PlayStation 2'?'PS2':p==='Xbox 360'?'X360':'OTHER';const E=s=>(s??'').toString().replace(/[&<>\"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));function img(src,cls){if(!src||!src.startsWith('/covers/'))return `<div class='${cls} platform-mark'>GV</div>`;return `<div class='${cls}'><img src='${E(src)}' onerror="this.parentElement.classList.add('platform-mark');this.parentElement.innerHTML='GV'"></div>`}async function load(){data=await fetch('/api/games').then(r=>r.json());let s=await fetch('/api/stats').then(r=>r.json());sg.textContent=s.games;sp.textContent=s.packages;ss.textContent=s.size_gb.toLocaleString('de-DE')+' GB';pf.innerHTML='<option value="">Alle Plattformen</option>'+Object.keys(s.platforms).sort().map(x=>`<option>${E(x)}</option>`).join('');render()}function render(){let term=q.value.toLowerCase(),pl=pf.value,missing=mf.value==='missing';let review=mf.value==='review',cover=mf.value==='cover',noid=mf.value==='id',lmp=mf.value==='localmp',lcoop=mf.value==='localcoop',omp=mf.value==='onlinemp';let a=data.filter(g=>(!pl||g.platform===pl)&&(!missing||g.metadata_missing)&&(!review||g.metadata_status==='review')&&(!cover||!g.cover_local)&&(!noid||!g.title_id)&&(!lmp||g.local_multiplayer)&&(!lcoop||g.local_coop)&&(!omp||g.online_multiplayer)&&(!term||(g.title+' '+(g.title_id||'')).toLowerCase().includes(term)));list.innerHTML=a.map(g=>`<div class='card ${PC(g.platform)} ${selected===g.id?'on':''}' onclick='show(${g.id})'>${img(g.cover_source,'cover')}<div class='meta'><span class='tag'>${E(g.platform)}</span>${g.metadata_missing?` <span class='warning small'>Metadaten fehlen</span>`:''}${g.metadata_status==='review'?` <span class='warning small'>Zuordnung prüfen</span>`:''}<div class='title'>${E(g.title)}</div><div class='small'>${E(g.title_id||'Keine TitleID')}</div><div class='mut small'>${E(g.publisher||'')}${g.packages.length?' · '+g.packages.length+' Pakete':''}</div></div></div>`).join('')}function show(id){selected=id;let g=data.find(x=>x.id===id);render();detail.scrollTop=0;detail.className='detail '+PC(g.platform);let pk=g.packages.map(p=>`<div class='pkg'><span><b>${E(p.name||p.filename)}</b><br><span class='mut small'>${E(p.filename)}</span></span><span>${E(p.category||'–')}</span><span>${E(p.version||'–')}</span><span>${E(p.location||'–')}</span><span>${p.size_gb==null?'–':p.size_gb.toLocaleString('de-DE')+' GB'}</span></div>`).join('');detail.innerHTML=`<div class='hero'>${img(g.cover_source,'heroCover')}<div><span class='tag'>${E(g.platform)}</span>${g.metadata_missing?` <span class='warning'>Metadaten fehlen</span>`:''}<h1>${E(g.title)}</h1><div class='mut'>${E(g.publisher||'Unbekannter Publisher')}${g.developer?' · '+E(g.developer):''}</div></div><div class='value'><span class='mut small'>Aktueller Wert</span><br><b>${E(g.current_value||'–')}</b></div></div><div class='info'><span class='mut small'>Metadatenqualität</span><br><b>${g.metadata_quality.score} % · ${g.metadata_quality.status==='complete'?'Vollständig':g.metadata_quality.status==='partial'?'Unvollständig':'Kritisch'}</b><div class='qualitybar'><span style='width:${g.metadata_quality.score}%'></span></div></div><div class='infos'><div class='info ${fieldClass(g,'title_id',g.title_id,true)}'><span class='mut small'>TitleID</span><br><b>${E(g.title_id||'–')}</b></div><div class='info ${fieldClass(g,'genres',g.genres,true)}'><span class='mut small'>Genre</span><br><b>${E(g.genres||'–')}</b></div><div class='info ${fieldClass(g,'release_date',g.release_date,false)}'><span class='mut small'>Release</span><br><b>${E(g.release_date||'–')}</b></div><div class='info'><span class='mut small'>Sammlung</span><br><b>${E(g.collection_status||'–')}</b></div><div class='info'><span class='mut small'>Vollständigkeit</span><br><b>${E(g.completeness||'–')}</b></div><div class='info'><span class='mut small'>Durchgespielt</span><br><b>${g.completed?'Ja':'Nein'}</b></div><div class='info ${fieldClass(g,'developer',g.developer,false)}'><span class='mut small'>Entwickler</span><br><b>${E(g.developer||'–')}</b></div><div class='info'><span class='mut small'>Backups</span><br><b>${g.packages.length}</b></div></div>${g.description?`<h3>Beschreibung</h3><p class='desc'>${E(g.description.replace(/<[^>]*>/g,' ')).slice(0,4000)}</p>`:''}${g.metadata_status==='review'?`<h3>IGDB-Zuordnung prüfen</h3><p class='warning'>Vorschlag: ${E(g.candidate_title||'')} (${Math.round((g.metadata_confidence||0)*100)} %)</p><button class='btn' onclick='openIgdb(${g.id})'>Treffer anzeigen</button>`:''}<div class='infos'><div class='info ${fieldClass(g,'game_modes',g.game_modes,false)}'><span class='mut small'>Game Modes</span><br><b>${E(g.game_modes||'–')}</b></div><div class='info ${fieldClass(g,'perspectives',g.perspectives,false)}'><span class='mut small'>Perspektive</span><br><b>${E(g.perspectives||'–')}</b></div><div class='info ${fieldClass(g,'themes',g.themes,false)}'><span class='mut small'>Themes</span><br><b>${E(g.themes||'–')}</b></div><div class='info ${fieldClass(g,'franchises',g.franchises,false)}'><span class='mut small'>Franchise</span><br><b>${E(g.franchises||'–')}</b></div><div class='info ${fieldClass(g,'engines',g.engines,false)}'><span class='mut small'>Engine</span><br><b>${E(g.engines||'–')}</b></div><div class='info'><span class='mut small'>Local Multiplayer</span><br><b>${g.local_multiplayer?'Ja':'Nein'}</b></div><div class='info'><span class='mut small'>Local Co-op</span><br><b>${g.local_coop?'Ja':'Nein'}</b></div><div class='info'><span class='mut small'>Online Multiplayer</span><br><b>${g.online_multiplayer?'Ja':'Nein'}</b></div></div><div class='info' style='margin-top:12px'><span class='mut small'>Datenquellen</span><br><span class='small'>${Object.entries(g.metadata_sources||{}).map(([k,v])=>E(k)+': '+E(v)).join(' · ')||'noch nicht zugeordnet'}</span></div>${g.pricecharting_url?`<div class='info' style='margin-top:8px'><span class='mut small'>PriceCharting</span><br><a href='${E(g.pricecharting_url)}' target='_blank' rel='noopener' style='color:#60a5fa'>Preis-/Spieleintrag öffnen</a></div>`:''}<div class='editor-actions'><button class='btn blue' onclick='openEditor(${g.id})'>Metadaten bearbeiten</button><button class='btn' onclick='openIgdb(${g.id})'>IGDB suchen</button><button class='btn' onclick='resolveTrace(${g.id})'>ID / IGDB auflösen</button></div><h3>Backup-Pakete</h3><div class='pkghead'><span>Datei</span><span>Typ</span><span>Version</span><span>Speicherort</span><span>Größe</span></div>${pk||'<p class="mut">Keine Backup-Pakete zugeordnet.</p>'}`;}function modal(v){document.getElementById('modal').classList.toggle('show',v)}async function upload(i,u){let f=document.getElementById(i).files[0];if(!f)return;let d=new FormData();d.append('file',f);msg.textContent='Import läuft ...';let r=await fetch(u,{method:'POST',body:d});msg.textContent=r.ok?'OK '+JSON.stringify(await r.json()):'Fehler: '+await r.text();if(r.ok)await load()}load();
async function covers(){let b=document.querySelector('button[onclick=\"covers()\"]');if(!await appConfirm('Cover aktualisieren','Cover für PS4, PS3 und PS2 über die Provider-Kaskade suchen?'))return;b.disabled=true;b.textContent='Cover-Suche läuft ...';try{let r=await fetch('/api/covers/refresh',{method:'POST'});let x=r.ok?await r.json():await r.text();await appMessage('Cover Ergebnis','<pre>'+E(typeof x==='string'?x:JSON.stringify(x,null,2))+'</pre>');if(r.ok)await load()}finally{b.disabled=false;b.textContent='Cover aktualisieren'}}
async function igdbRefresh(){if(!await appConfirm('IGDB aktualisieren','Alle Spiele wie mit <b>ID / IGDB auflösen</b> aktualisieren? Manuell bearbeitete Felder bleiben geschützt.'))return;busy(true,'IGDB aktualisiert die gesamte Bibliothek ...');try{let r=await fetch('/api/metadata/igdb/refresh',{method:'POST'});let result=r.ok?await r.json():await r.text();await appMessage('IGDB Ergebnis','<pre>'+E(typeof result==='string'?result:JSON.stringify(result,null,2))+'</pre>');if(r.ok){await load();if(selected)show(selected)}}finally{busy(false)}}
async function showCandidates(id){return openIgdb(id)}
let activeGame=null;
function openEditor(id){let g=data.find(x=>x.id===id);activeGame=id;edTitle.value=g.title||'';edPlatform.value=g.platform||'';edType.value=g.identifier_type||(g.platform==='PlayStation 4'?'CUSA':g.platform==='Xbox 360'?'TITLEID':'SERIAL');edTid.value=g.title_id||'';edIgdb.value=g.metadata_provider==='IGDB'?(g.metadata_provider_id||''):'';edPublisher.value=g.publisher||'';edDeveloper.value=g.developer||'';edGenres.value=g.genres||'';edRelease.value=g.release_date||'';edValue.value=g.current_value||'';edModes.value=g.game_modes||'';edPerspective.value=g.perspectives||'';edThemes.value=g.themes||'';edFranchise.value=g.franchises||'';edEngine.value=g.engines||'';edCollection.value=g.collection_status||'';edCompleteness.value=g.completeness||'';edPriceUrl.value=g.pricecharting_url||'';edCoverUrl.value='';edDescription.value=g.description||'';editorModal.classList.add('show');document.body.classList.add('editor-open');setTimeout(()=>{let sc=editorModal.querySelector('.editor-scroll');if(sc)sc.scrollTop=0},0)}
function closeEditor(){editorModal.classList.remove('show');document.body.classList.remove('editor-open')}
async function saveMetadata(){saveBtn.disabled=true;saveBtn.innerHTML='<span class="spinner"></span> Speichern';let P={title:edTitle.value,title_id:edTid.value,identifier_type:edType.value,publisher:edPublisher.value,developer:edDeveloper.value,genres:edGenres.value,release_date:edRelease.value,current_value:edValue.value,game_modes:edModes.value,perspectives:edPerspective.value,themes:edThemes.value,franchises:edFranchise.value,engines:edEngine.value,collection_status:edCollection.value,completeness:edCompleteness.value,pricecharting_url:edPriceUrl.value,description:edDescription.value};try{let r=await fetch(`/api/games/${activeGame}/metadata`,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(P)});if(!r.ok){await appMessage('Fehler','<pre>'+E(await r.text())+'</pre>');return}let saved=await r.json();if(edIgdb.value){r=await fetch(`/api/games/${activeGame}/igdb-direct/${edIgdb.value}`,{method:'POST'});if(!r.ok){await appMessage('IGDB Fehler','<pre>'+E(await r.text())+'</pre>')}}if(edCoverUrl.value.trim()){r=await fetch(`/api/games/${activeGame}/cover-from-url`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url:edCoverUrl.value.trim()})});if(!r.ok){await appMessage('Cover Fehler','<pre>'+E(await r.text())+'</pre>')}}closeEditor();await load();show(activeGame)}finally{saveBtn.disabled=false;saveBtn.textContent='Speichern'}}
async function openIgdb(id){busy(true,'IGDB-Suche läuft ...');try{activeGame=id;igdbModal.classList.add('show');igdbResults.innerHTML='';igdbState.innerHTML='<span class="spinner"></span> IGDB wird durchsucht ...';let r=await fetch(`/api/games/${id}/igdb-candidates`);if(!r.ok){igdbState.textContent=await r.text();return}let rows=await r.json();igdbState.textContent=rows.length+' Treffer';igdbResults.innerHTML=rows.map(x=>`<div class="candidate">${x.cover_url?`<img src="${E(x.cover_url)}">`:'<div></div>'}<div><b>${E(x.title)}</b><br><span class="mut">IGDB ${x.igdb_id} · ${Math.round(x.confidence*100)} %</span></div><button class="btn" onclick="acceptId(${x.igdb_id})">Übernehmen</button></div>`).join('')}
finally{busy(false)}}function closeIgdb(){igdbModal.classList.remove('show')}
async function acceptId(i){busy(true,'IGDB-Daten werden übernommen ...');try{igdbState.innerHTML='<span class="spinner"></span> Übernahme ...';let r=await fetch(`/api/games/${activeGame}/igdb-direct/${i}`,{method:'POST'});if(!r.ok){igdbState.textContent=await r.text();return}let result=await r.json();if(result.changed)await appMessage('IGDB übernommen','Aktualisiert: '+E(result.changed.join(', ')||'keine Änderungen'));closeIgdb();await load();show(activeGame)}
finally{busy(false)}}async function directLoad(){if(!/^\d+$/.test(directId.value.trim()))return await appMessage('IGDB','Numerische IGDB-ID eingeben');await acceptId(directId.value.trim())}
async function resolveTrace(id){busy(true,'ID / IGDB wird aufgelöst ...');try{activeGame=id;traceModal.classList.add('show');traceRows.innerHTML='';traceState.innerHTML='<span class="spinner"></span> Suche läuft ...';let r=await fetch(`/api/games/${id}/resolve-trace`,{method:'POST'});if(!r.ok){traceState.textContent=await r.text();return}let x=await r.json();traceState.textContent='Fertig';traceRows.innerHTML=x.trace.map(t=>`<p><b>${t.ok?'✓':'✗'} ${E(t.step)}</b><br><span class="mut">${E(t.detail)}</span></p>`).join('');await load();show(id)}finally{busy(false)}}
async function localizeCovers(){if(!await appConfirm('Cover lokal speichern','Alle Cover lokal speichern? Alte Game-Collector-Pfade werden verworfen und über Provider/IGDB neu gesucht.'))return;busy(true,'Cover werden lokalisiert ...');try{let r=await fetch('/api/covers/localize',{method:'POST'});let x=r.ok?await r.json():await r.text();await appMessage('Cover Ergebnis','<pre>'+E(typeof x==='string'?x:JSON.stringify(x,null,2))+'</pre>');if(r.ok)await load()}finally{busy(false)}}
async function openQuality(){qualityModal.classList.add('show');qualityBody.innerHTML='<span class="spinner"></span> Datenqualität wird geladen ...';let r=await fetch('/api/data-quality');if(!r.ok){qualityBody.textContent=await r.text();return}let rows=await r.json();qualityBody.innerHTML=rows.length?rows.map(x=>`<div class="dq-row" onclick="qualityModal.classList.remove('show');show(${x.id})"><b>${E(x.title)}</b> · ${E(x.platform)} <span class="score-pill">${x.quality.score}%</span><br><span class="small">${x.quality.missing_critical.length?'Kritisch: '+E(x.quality.missing_critical.join(', ')):''}${x.quality.missing_optional.length?' · Optional: '+E(x.quality.missing_optional.join(', ')):''}${x.without_id?' · ID fehlt':''}${x.without_cover?' · Cover fehlt':''}${x.review?' · Review':''}</span></div>`).join(''):'<p>Keine Problemfälle.</p>'}
async function openDuplicates(){duplicatesModal.classList.add('show');duplicatesBody.innerHTML='<span class="spinner"></span> Duplikate werden analysiert ...';let r=await fetch('/api/duplicates');if(!r.ok){duplicatesBody.textContent=await r.text();return}let rows=await r.json();duplicatesBody.innerHTML=rows.length?rows.map((x,i)=>`<div class="dup-row" id="dup-${i}"><div><span class="score-pill">${Math.round(x.score*100)} %</span> ${E((x.reasons||[]).join(' · '))}</div><div class="dup-grid"><div><b>Behalten</b><br>${E(x.keep.title)}<br><span class="small">${E(x.keep.title_id||'keine ID')} · ${x.keep.packages.length} Pakete ${x.keep.current_value?'· Wert '+E(x.keep.current_value):''}</span></div><div><b>Zusammenführen</b><br>${E(x.merge.title)}<br><span class="small">${E(x.merge.title_id||'keine ID')} · ${x.merge.packages.length} Pakete</span></div></div>${x.conflicts.length?`<div class="conflict">Konflikte: ${E(x.conflicts.map(c=>c.field).join(', '))}</div>`:''}<button class="btn blue" onclick="mergeDuplicate(${x.keep.id},${x.merge.id},${i})">Zusammenführen</button></div>`).join(''):'<p>Keine möglichen Duplikate gefunden.</p>'}
async function mergeDuplicate(keepId,mergeId,row){if(!await appConfirm('Duplikate zusammenführen','Packages und fehlende Felder werden auf den bevorzugten Datensatz übertragen. Der zweite Datensatz wird danach gelöscht.'))return;busy(true,'Duplikate werden zusammengeführt ...');try{let r=await fetch(`/api/duplicates/merge/${keepId}/${mergeId}`,{method:'POST'});let x=r.ok?await r.json():await r.text();if(!r.ok){await appMessage('Merge-Fehler','<pre>'+E(x)+'</pre>');return}await appMessage('Zusammengeführt',`Packages verschoben: ${x.packages_moved}<br>Übernommene Felder: ${E((x.fields_inherited||[]).join(', ')||'keine')}`);await load();openDuplicates()}finally{busy(false)}}
</script></body></html>'''

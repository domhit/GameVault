from __future__ import annotations
import html, os, re, json, tempfile, xml.etree.ElementTree as ET, secrets, time, hashlib, hmac
from typing import Optional
from fastapi import FastAPI, UploadFile, File, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, FileResponse
from sqlalchemy import create_engine, String, Text, Float, Boolean, Integer, BigInteger, ForeignKey, select, func, inspect, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, Session
from openpyxl import load_workbook
from pathlib import Path
from datetime import datetime, timezone
from .providers import cascade, igdb, orbispatches
from .providers.consoles.ps3_ftp import PS3FTPProvider, PLAYABLE_CATEGORIES, NON_GAME_CATEGORIES, HOMEBREW_HINTS, NON_GAME_IDS, NON_GAME_TITLE_HINTS
from .providers.consoles.ps3_webman import PS3WebManProvider
from .providers.consoles.xbox360_aurora import AuroraProvider
from .providers.consoles.xboxclassic_xbmc4gamers import XBMC4GamersProvider
from .providers.consoles.ps4_goldhen import PS4GoldHENProvider
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
    remote_latest_version:Mapped[Optional[str]]=mapped_column(String(40),nullable=True)
    remote_update_checked_at:Mapped[Optional[str]]=mapped_column(String(50),nullable=True)
    region:Mapped[Optional[str]]=mapped_column(String(40),nullable=True)
    media_format:Mapped[Optional[str]]=mapped_column(String(40),nullable=True)
    edition:Mapped[Optional[str]]=mapped_column(String(120),nullable=True)
    storefront:Mapped[Optional[str]]=mapped_column(String(120),nullable=True)
    tags:Mapped[Optional[str]]=mapped_column(Text,nullable=True)
    notes:Mapped[Optional[str]]=mapped_column(Text,nullable=True)
    resolver_log:Mapped[Optional[str]]=mapped_column(Text,nullable=True)
    pricecharting_url:Mapped[Optional[str]]=mapped_column(Text,nullable=True)
    packages:Mapped[list["Package"]]=relationship(back_populates="game",cascade="all,delete-orphan")
class Console(Base):
    __tablename__='consoles'
    id:Mapped[int]=mapped_column(primary_key=True)
    name:Mapped[str]=mapped_column(String(120))
    platform:Mapped[str]=mapped_column(String(80),default='PlayStation 3')
    host:Mapped[str]=mapped_column(String(255))
    ftp_port:Mapped[int]=mapped_column(Integer,default=21)
    ftp_username:Mapped[Optional[str]]=mapped_column(String(120),nullable=True)
    ftp_password:Mapped[Optional[str]]=mapped_column(String(255),nullable=True)
    webman_url:Mapped[Optional[str]]=mapped_column(String(500),nullable=True)
    provider_type:Mapped[Optional[str]]=mapped_column(String(50),nullable=True)
    nova_url:Mapped[Optional[str]]=mapped_column(String(500),nullable=True)
    nova_username:Mapped[Optional[str]]=mapped_column(String(120),nullable=True)
    nova_password:Mapped[Optional[str]]=mapped_column(String(255),nullable=True)
    database_path:Mapped[Optional[str]]=mapped_column(String(800),nullable=True)
    image_source:Mapped[Optional[str]]=mapped_column(Text,nullable=True)
    enabled:Mapped[bool]=mapped_column(Boolean,default=True)
    last_scan_at:Mapped[Optional[str]]=mapped_column(String(50),nullable=True)
    last_scan_status:Mapped[Optional[str]]=mapped_column(String(40),nullable=True)
    last_scan_message:Mapped[Optional[str]]=mapped_column(Text,nullable=True)

class InstalledGame(Base):
    __tablename__='installed_games'
    id:Mapped[int]=mapped_column(primary_key=True)
    console_id:Mapped[int]=mapped_column(ForeignKey('consoles.id'),index=True)
    game_id:Mapped[Optional[int]]=mapped_column(ForeignKey('games.id'),nullable=True,index=True)
    platform:Mapped[str]=mapped_column(String(80))
    identifier:Mapped[Optional[str]]=mapped_column(String(80),nullable=True,index=True)
    title:Mapped[str]=mapped_column(String(400))
    installed_version:Mapped[Optional[str]]=mapped_column(String(40),nullable=True)
    content_type:Mapped[Optional[str]]=mapped_column(String(120),nullable=True)
    category:Mapped[Optional[str]]=mapped_column(String(40),nullable=True)
    content_id:Mapped[Optional[str]]=mapped_column(String(120),nullable=True)
    source:Mapped[str]=mapped_column(String(80))
    path:Mapped[str]=mapped_column(Text)
    storage:Mapped[Optional[str]]=mapped_column(String(80),nullable=True)
    last_seen_at:Mapped[str]=mapped_column(String(50))
    match_method:Mapped[Optional[str]]=mapped_column(String(40),nullable=True)
    match_confidence:Mapped[Optional[float]]=mapped_column(Float,nullable=True)
    file_size:Mapped[Optional[str]]=mapped_column(String(80),nullable=True)
    installed_size_bytes:Mapped[Optional[int]]=mapped_column(BigInteger,nullable=True)
    size_checked_at:Mapped[Optional[str]]=mapped_column(String(50),nullable=True)

class PlatformImage(Base):
    __tablename__='platform_images'
    platform:Mapped[str]=mapped_column(String(80),primary_key=True)
    image_source:Mapped[Optional[str]]=mapped_column(Text,nullable=True)
class DuplicateExclusion(Base):
    __tablename__="duplicate_exclusions"
    id:Mapped[int]=mapped_column(primary_key=True)
    game_a_id:Mapped[int]=mapped_column(Integer,index=True)
    game_b_id:Mapped[int]=mapped_column(Integer,index=True)
    created_at:Mapped[str]=mapped_column(String(50))

class Package(Base):
    __tablename__="packages"
    id:Mapped[int]=mapped_column(primary_key=True)
    filename:Mapped[str]=mapped_column(String(600),unique=True,index=True)
    game_id:Mapped[Optional[int]]=mapped_column(ForeignKey("games.id"),nullable=True,index=True)
    title_id:Mapped[Optional[str]]=mapped_column(String(40),index=True,nullable=True)
    name:Mapped[Optional[str]]=mapped_column(String(400),nullable=True)
    version:Mapped[Optional[str]]=mapped_column(String(40),nullable=True)
    newest_patch:Mapped[Optional[str]]=mapped_column(String(40),nullable=True)
    decision:Mapped[Optional[str]]=mapped_column(String(80),nullable=True)
    location:Mapped[Optional[str]]=mapped_column(String(80),nullable=True)
    category:Mapped[Optional[str]]=mapped_column(String(40),nullable=True)
    size_gb:Mapped[Optional[float]]=mapped_column(Float,nullable=True)
    game:Mapped[Optional[Game]]=relationship(back_populates="packages")
class GameSelection(Base):
    __tablename__="game_selections"
    id:Mapped[int]=mapped_column(primary_key=True)
    game_id:Mapped[int]=mapped_column(ForeignKey("games.id"),index=True)
    selection_name:Mapped[str]=mapped_column(String(120),default="Spieleauswahl Freund",index=True)
    created_at:Mapped[str]=mapped_column(String(50))
Base.metadata.create_all(engine)
with engine.begin() as c:
    for col,typ in [("cover_provider","VARCHAR(120)"),("cover_checked_at","VARCHAR(50)"),("cover_error","TEXT"),("metadata_status","VARCHAR(40)"),("metadata_confidence","DOUBLE PRECISION"),("metadata_provider","VARCHAR(80)"),("metadata_provider_id","VARCHAR(80)"),("metadata_updated_at","VARCHAR(50)"),("metadata_locked","BOOLEAN DEFAULT FALSE"),("candidate_title","VARCHAR(300)"),("candidate_provider_id","VARCHAR(80)"),("identifier_type","VARCHAR(40)"),("game_modes","TEXT"),("perspectives","TEXT"),("themes","TEXT"),("franchises","TEXT"),("engines","TEXT"),("multiplayer_json","TEXT"),("metadata_sources","TEXT"),("remote_latest_version","VARCHAR(40)"),("remote_update_checked_at","VARCHAR(50)"),("region","VARCHAR(40)"),("media_format","VARCHAR(40)"),("edition","VARCHAR(120)"),("storefront","VARCHAR(120)"),("tags","TEXT"),("notes","TEXT"),("resolver_log","TEXT")]:
        c.execute(__import__("sqlalchemy").text(f"ALTER TABLE games ADD COLUMN IF NOT EXISTS {col} {typ}"))
    for col,typ in [('match_method','VARCHAR(40)'),('match_confidence','DOUBLE PRECISION'),('file_size','VARCHAR(80)'),('installed_size_bytes','BIGINT'),('size_checked_at','VARCHAR(50)')]:
        c.execute(text(f"ALTER TABLE installed_games ADD COLUMN IF NOT EXISTS {col} {typ}"))
    c.execute(text("ALTER TABLE installed_games ALTER COLUMN installed_size_bytes TYPE BIGINT USING installed_size_bytes::BIGINT"))
    for col,typ in [('provider_type','VARCHAR(50)'),('nova_url','VARCHAR(500)'),('nova_username','VARCHAR(120)'),('nova_password','VARCHAR(255)'),('database_path','VARCHAR(800)'),('image_source','TEXT')]:
        c.execute(text(f"ALTER TABLE consoles ADD COLUMN IF NOT EXISTS {col} {typ}"))
    c.execute(text("UPDATE consoles SET provider_type='ps3' WHERE provider_type IS NULL"))
    pkg_cols={r[0] for r in c.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='packages'")).fetchall()}
    if 'pkg_version' in pkg_cols:
        c.execute(text("UPDATE packages SET version = pkg_version WHERE lower(coalesce(category,'')) = 'game' AND nullif(pkg_version,'') IS NOT NULL"))
        c.execute(text("UPDATE packages SET version = NULL WHERE lower(coalesce(category,'')) IN ('dlc','addon','add-on','add on')"))
        c.execute(text("ALTER TABLE packages DROP COLUMN pkg_version"))
    c.execute(text("UPDATE packages SET category = 'Patch' WHERE lower(coalesce(category,'')) IN ('patch','update')"))
    c.execute(text("UPDATE packages SET category = 'DLC', version = NULL WHERE lower(coalesce(category,'')) IN ('dlc','addon','add-on','add on')"))
    c.execute(text("UPDATE packages SET category = 'Game' WHERE lower(coalesce(category,'')) = 'game'"))
app=FastAPI(title="GameVault",version="1.2.0-dev30")
ADMIN_PASSWORD=os.getenv("GAMEVAULT_ADMIN_PASSWORD","")
ADMIN_SESSION_MINUTES=max(5,int(os.getenv("GAMEVAULT_ADMIN_SESSION_MINUTES","60")))
SELECTION_NAME=os.getenv("GAMEVAULT_SELECTION_NAME","Spieleauswahl Freund")
ADMIN_COOKIE="gamevault_admin"
_admin_sessions={}
def _session_ok(token):
    if not token:return False
    expires=_admin_sessions.get(token,0)
    if expires<=time.time():
        _admin_sessions.pop(token,None);return False
    _admin_sessions[token]=time.time()+ADMIN_SESSION_MINUTES*60
    return True
@app.middleware("http")
async def readonly_guard(request:Request,call_next):
    path=request.url.path
    allowed_write=path in ("/api/auth/login","/api/auth/logout") or path.startswith("/api/selections/")
    if request.method not in ("GET","HEAD","OPTIONS") and path.startswith("/api/") and not allowed_write and not _session_ok(request.cookies.get(ADMIN_COOKIE)):
        return __import__("fastapi").responses.JSONResponse(status_code=403,content={"detail":"GameVault ist im Besuchermodus. Verwaltung zuerst freischalten."})
    return await call_next(request)
@app.get('/api/auth/status')
def auth_status(request:Request):
    return {'admin':_session_ok(request.cookies.get(ADMIN_COOKIE)),'password_configured':bool(ADMIN_PASSWORD),'session_minutes':ADMIN_SESSION_MINUTES}
@app.post('/api/auth/login')
def auth_login(payload:dict,response:Response):
    if not ADMIN_PASSWORD:raise HTTPException(503,'GAMEVAULT_ADMIN_PASSWORD ist nicht gesetzt')
    supplied=str(payload.get('password') or '')
    if not hmac.compare_digest(supplied,ADMIN_PASSWORD):raise HTTPException(401,'Passwort falsch')
    token=secrets.token_urlsafe(32);_admin_sessions[token]=time.time()+ADMIN_SESSION_MINUTES*60
    response.set_cookie(ADMIN_COOKIE,token,max_age=ADMIN_SESSION_MINUTES*60,httponly=True,samesite='lax',secure=os.getenv('GAMEVAULT_COOKIE_SECURE','false').lower()=='true')
    return {'ok':True,'admin':True,'session_minutes':ADMIN_SESSION_MINUTES}
@app.post('/api/auth/logout')
def auth_logout(request:Request,response:Response):
    _admin_sessions.pop(request.cookies.get(ADMIN_COOKIE),None);response.delete_cookie(ADMIN_COOKIE);return {'ok':True,'admin':False}
@app.get('/api/selections')
def selections():
    with Session(engine) as db:
        ids=set(db.scalars(select(GameSelection.game_id).where(GameSelection.selection_name==SELECTION_NAME)).all())
        rows=db.scalars(select(Game).where(Game.id.in_(ids)).order_by(Game.platform,Game.title)).all() if ids else []
        platforms={}
        for g in rows:platforms[g.platform]=platforms.get(g.platform,0)+1
        return {'name':SELECTION_NAME,'game_ids':sorted(ids),'count':len(ids),'platforms':platforms,'games':[serial(g) for g in rows]}
@app.post('/api/selections/{game_id}')
def selection_add(game_id:int):
    with Session(engine) as db:
        if not db.get(Game,game_id):raise HTTPException(404,'Spiel nicht gefunden')
        exists=db.scalar(select(GameSelection).where(GameSelection.game_id==game_id,GameSelection.selection_name==SELECTION_NAME))
        if not exists:db.add(GameSelection(game_id=game_id,selection_name=SELECTION_NAME,created_at=datetime.now(timezone.utc).isoformat()));db.commit()
        return {'ok':True,'selected':True,'game_id':game_id}
@app.delete('/api/selections/{game_id}')
def selection_remove(game_id:int):
    with Session(engine) as db:
        row=db.scalar(select(GameSelection).where(GameSelection.game_id==game_id,GameSelection.selection_name==SELECTION_NAME))
        if row:db.delete(row);db.commit()
        return {'ok':True,'selected':False,'game_id':game_id}
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
    raw=str(v).strip().replace(' ','')
    try:
        if ',' in raw and '.' in raw:
            raw=raw.replace('.','').replace(',','.') if raw.rfind(',')>raw.rfind('.') else raw.replace(',','')
        elif ',' in raw:raw=raw.replace(',','.')
        return float(raw)
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
def normalize_package_category(v):
    raw=str(v or '').strip();k=raw.casefold()
    if k in ('game','base','base game'):return 'Game'
    if k in ('patch','update'):return 'Patch'
    if k in ('dlc','addon','add-on','add on'):return 'DLC'
    return raw or None
def imported_package_version(category,row_version,row_pkg_version):
    if category=='Game':return str(row_pkg_version) if row_pkg_version not in (None,'') else None
    if category=='Patch':return str(row_version) if row_version not in (None,'') else None
    return None
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
            category=normalize_package_category(get("Category"))
            if not game and category in ("Game","Patch"):
                game=Game(platform="PlayStation 4",title=nm or tid or str(fn),title_id=tid); db.add(game); db.flush(); byname[key(game.title)]=game; stubs+=1
            if game and tid and not game.title_id: game.title_id=tid
            vals=dict(game_id=game.id if game else None,title_id=tid,name=nm or None,version=imported_package_version(category,get("Version"),get("Version pkg")),newest_patch=str(get("Newest Patch")) if get("Newest Patch") is not None else None,decision=str(get("Entscheidung")) if get("Entscheidung") is not None else None,location=str(get("Location")) if get("Location") is not None else None,category=category,size_gb=nfloat(get("Size (GB)")))
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
def resolver_events(g):
 try:return json.loads(g.resolver_log or '[]')
 except:return []
def add_resolver_event(g,provider,ok,detail):
 rows=resolver_events(g);rows.append({'at':datetime.now(timezone.utc).isoformat(),'provider':provider,'ok':bool(ok),'detail':str(detail)[:500]});g.resolver_log=json.dumps(rows[-30:],ensure_ascii=False)
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
def version_key(v):
 nums=re.findall(r'\d+',str(v or ''))
 return tuple(int(x) for x in nums) if nums else ()
def local_patch_version(g):
 vals=[p.version for p in g.packages if (p.category or '').casefold() in ('game','patch','update') and p.version]
 return max(vals,key=version_key) if vals else None
def ps4_update_status(g):
 if g.platform!='PlayStation 4':return 'not_applicable'
 remote=g.remote_latest_version;local=local_patch_version(g)
 if not remote:return 'unknown'
 if not local:return 'update_available'
 return 'update_available' if version_key(remote)>version_key(local) else 'current'
def serial(g):
    return {"id":g.id,"title":g.title,"platform":g.platform,"title_id":g.title_id,"publisher":g.publisher,"developer":g.developer,"genres":g.genres,"release_date":g.release_date,"completed":g.completed,"collection_status":g.collection_status,"completeness":g.completeness,"current_value":g.current_value,"description":g.description,"cover_source":g.cover_source,"cover_local":cover_is_local(g),"cover_provider":g.cover_provider,"cover_checked_at":g.cover_checked_at,"cover_error":g.cover_error,"metadata_status":g.metadata_status,"metadata_confidence":g.metadata_confidence,"metadata_provider":g.metadata_provider,"metadata_provider_id":g.metadata_provider_id,"metadata_locked":False,"metadata_sources":source_map(g),"candidate_title":g.candidate_title,"candidate_provider_id":g.candidate_provider_id,"identifier_type":g.identifier_type,"game_modes":g.game_modes,"perspectives":g.perspectives,"themes":g.themes,"franchises":g.franchises,"engines":g.engines,"multiplayer":multiplayer_rows(g),"local_multiplayer":local_multiplayer(g),"local_coop":local_coop(g),"online_multiplayer":online_multiplayer(g),"pricecharting_url":g.pricecharting_url,"metadata_quality":metadata_quality(g),"metadata_missing":metadata_quality(g)["status"]=="critical","local_patch_version":local_patch_version(g),"remote_latest_version":g.remote_latest_version,"remote_update_checked_at":g.remote_update_checked_at,"update_status":ps4_update_status(g),"region":g.region,"media_format":g.media_format,"edition":g.edition,"storefront":g.storefront,"tags":[x.strip() for x in (g.tags or "").split(",") if x.strip()],"notes":g.notes,"resolver_log":resolver_events(g),"installed_on":[],"packages":[{"id":p.id,"filename":p.filename,"title_id":p.title_id,"name":p.name,"version":p.version,"newest_patch":p.newest_patch,"decision":p.decision,"location":p.location,"category":p.category,"size_gb":p.size_gb} for p in g.packages]}
def console_effective_version(parent,all_rows):
 children=[x for x in all_rows if x.console_id==parent.console_id and x.identifier==parent.identifier and x.category=='Title Update' and x.installed_version]
 if children:return max((x.installed_version for x in children),key=version_key)
 return parent.installed_version

@app.get("/api/games")
def games():
    with Session(engine) as db:
        rows=[];consoles={c.id:c for c in db.scalars(select(Console)).all()}
        all_installed=db.scalars(select(InstalledGame).where(InstalledGame.game_id.is_not(None))).all();installed={}
        for x in all_installed:installed.setdefault(x.game_id,[]).append(x)
        for g in db.scalars(select(Game).order_by(Game.title)).all():
            row=serial(g);game_rows=installed.get(g.id,[]);parents=[x for x in game_rows if x.category not in ('DLC','Title Update')]
            row['installed_on']=[{'console_id':x.console_id,'console_name':consoles[x.console_id].name if x.console_id in consoles else x.platform,'platform':x.platform,'category':x.category,'version':console_effective_version(x,game_rows),'base_version':x.installed_version,'path':x.path,'storage':x.storage,'source':x.source,'last_seen_at':x.last_seen_at,'file_size':x.file_size,'installed_size_bytes':x.installed_size_bytes,'installed_size':format_bytes(x.installed_size_bytes) if x.installed_size_bytes is not None else None,'size_checked_at':x.size_checked_at,'content_id':x.content_id,'title_updates':sum(1 for c in game_rows if c.console_id==x.console_id and c.identifier==x.identifier and c.category=='Title Update'),'dlc_count':sum(1 for c in game_rows if c.console_id==x.console_id and c.identifier==x.identifier and c.category=='DLC')} for x in parents];rows.append(row)
        return rows
@app.get("/api/stats")
def stats():
    with Session(engine) as db:return {"games":db.scalar(select(func.count(Game.id))) or 0,"packages":db.scalar(select(func.count(Package.id))) or 0,"size_gb":round(db.scalar(select(func.coalesce(func.sum(Package.size_gb),0))) or 0,3),"platforms":dict(db.execute(select(Game.platform,func.count(Game.id)).group_by(Game.platform)).all())}
def console_dict(c):
 return {'id':c.id,'name':c.name,'platform':c.platform,'host':c.host,'ftp_port':c.ftp_port,'ftp_username':c.ftp_username,'webman_url':c.webman_url,'provider_type':c.provider_type or 'ps3','nova_url':c.nova_url,'nova_username':c.nova_username,'database_path':c.database_path,'image_source':c.image_source,'enabled':c.enabled,'last_scan_at':c.last_scan_at,'last_scan_status':c.last_scan_status,'last_scan_message':c.last_scan_message}
def installed_dict(x):
 return {'id':x.id,'console_id':x.console_id,'game_id':x.game_id,'platform':x.platform,'identifier':x.identifier,'title':x.title,'installed_version':x.installed_version,'content_type':x.content_type,'category':x.category,'content_id':x.content_id,'source':x.source,'path':x.path,'storage':x.storage,'last_seen_at':x.last_seen_at,'match_method':x.match_method,'match_confidence':x.match_confidence,'file_size':x.file_size,'installed_size_bytes':x.installed_size_bytes,'size_checked_at':x.size_checked_at}
def match_installed(db,item):
 platform=item.get('platform') or 'PlayStation 3'
 ident=(item.get('identifier') or '').replace('-','').replace('_','').upper() or None
 if ident:
  g=db.scalar(select(Game).where(Game.platform==platform,func.replace(func.replace(func.upper(Game.title_id),'-',''),'_','')==ident))
  if g:return g,'identifier',1.0
 title_key=key(item.get('title'))
 matches=[g for g in db.scalars(select(Game).where(Game.platform==platform)).all() if key(g.title)==title_key]
 return (matches[0],'title_exact',.98) if len(matches)==1 else (None,None,None)
def match_suggestions(db,item,limit=8):
 from difflib import SequenceMatcher
 title=key(item.title);rows=[]
 for g in db.scalars(select(Game).where(Game.platform==item.platform)).all():
  candidate=key(g.title);ratio=SequenceMatcher(None,title,candidate).ratio()
  containment=(min(len(title),len(candidate))/max(len(title),len(candidate))) if title and candidate and (title in candidate or candidate in title) else 0
  score=max(ratio,containment)
  if score>=.45:rows.append({'id':g.id,'title':g.title,'title_id':g.title_id,'score':round(score,3),'match_reason':'Teilstring' if containment>ratio else 'Ähnlichkeit'})
 return sorted(rows,key=lambda x:x['score'],reverse=True)[:limit]

@app.get('/api/library/search')
def library_search(platform:str,q:str='',limit:int=80,exclude_linked:bool=False):
 with Session(engine) as db:
  query=select(Game).where(Game.platform==platform).order_by(Game.title)
  games=db.scalars(query).all();term=key(q);linked=set()
  if exclude_linked:
   linked={x.game_id for x in db.scalars(select(InstalledGame).where(InstalledGame.platform==platform,InstalledGame.game_id.is_not(None))).all()}
  rows=[]
  for g in games:
   if g.id in linked:continue
   if term and term not in key(g.title) and term not in key(g.title_id):continue
   rows.append({'id':g.id,'title':g.title,'title_id':g.title_id,'cover_source':g.cover_source,'publisher':g.publisher,'release_date':g.release_date})
   if len(rows)>=max(1,min(limit,200)):break
  return rows
def merge_scan_items(items):
 merged={};child_categories={'DLC','Title Update'}
 for item in items:
  ident=(item.get('identifier') or '').replace('-','').replace('_','').upper() or None;path=(item.get('path') or '').replace('/mount.ps3/','/');category=item.get('category') or item.get('content_type') or 'Unknown';item=item.copy();item['path']=path
  child_key=(item.get('content_id') or '',item.get('installed_version') or '',path)
  # PS3 FTP ISO and webMAN are two views of the same installed game. Collapse parents by platform+TitleID.
  if item.get('platform')=='PlayStation 3' and ident and category not in child_categories:k=('PlayStation 3',ident,'parent')
  elif ident:k=(item.get('platform'),ident,category,child_key if category in child_categories else '')
  else:k=(item.get('platform'),key(item.get('title')),category,path)
  if k not in merged:merged[k]=item;continue
  old=merged[k]
  ftp_new=str(item.get('source') or '').startswith('FTP');ftp_old=str(old.get('source') or '').startswith('FTP')
  # FTP controls canonical local path/storage/size-capable record; webMAN can improve title/version metadata.
  if ftp_new and not ftp_old:
   old['path']=item.get('path') or old.get('path');old['storage']=item.get('storage') or old.get('storage');old['content_type']=item.get('content_type') or old.get('content_type');old['category']=item.get('category') or old.get('category')
  for f in ('identifier','installed_version','content_id','file_size','installed_size_bytes'):
   if not old.get(f) and item.get(f):old[f]=item[f]
  old_filelike='+' in (old.get('title') or '') or (old.get('title') or '').lower().endswith('.iso');new_filelike='+' in (item.get('title') or '') or (item.get('title') or '').lower().endswith('.iso')
  if old_filelike and not new_filelike:old['title']=item['title']
  sources=set((old.get('source') or '').split(' + '));sources.add(item.get('source') or '');old['source']=' + '.join(sorted(x for x in sources if x))
 return list(merged.values())

@app.get('/api/consoles')
def list_consoles():
 with Session(engine) as db:
  out=[]
  for c in db.scalars(select(Console).order_by(Console.name)).all():
   row=console_dict(c);installed=db.scalars(select(InstalledGame).where(InstalledGame.console_id==c.id)).all();row['installed_count']=len(installed);row['matched_count']=sum(bool(x.game_id) for x in installed);row['content_counts']={};parents=[x for x in installed if x.category not in ('DLC','Title Update')];unique_sizes={}
   for x in parents:
    sk=(x.platform,(x.identifier or '').upper() or x.id);unique_sizes[sk]=max(unique_sizes.get(sk,0),x.installed_size_bytes or 0)
   row['installed_size_bytes']=sum(unique_sizes.values());row['installed_size']=format_bytes(row['installed_size_bytes']) if row['installed_size_bytes'] else None;row['sizes_checked']=sum(v>0 for v in unique_sizes.values())
   for x in installed:row['content_counts'][x.category or x.content_type or 'Other']=row['content_counts'].get(x.category or x.content_type or 'Other',0)+1
   out.append(row)
  return out
@app.post('/api/consoles')
def create_console(payload:dict):
 name=str(payload.get('name') or '').strip();host=str(payload.get('host') or '').strip()
 if not name or not host:raise HTTPException(400,'Name und Host/IP sind erforderlich')
 with Session(engine) as db:
  provider=str(payload.get('provider_type') or 'ps3');platform='Xbox 360' if provider=='xbox360_aurora' else ('Xbox Classic' if provider=='xboxclassic_xbmc4gamers' else ('PlayStation 4' if provider=='ps4_goldhen' else 'PlayStation 3'));c=Console(name=name,platform=platform,provider_type=provider,host=host,ftp_port=int(payload.get('ftp_port') or (2121 if provider=='ps4_goldhen' else 21)),ftp_username=str(payload.get('ftp_username') or ('xboxftp' if provider=='xbox360_aurora' else 'anonymous')),ftp_password=str(payload.get('ftp_password') or ('xboxftp' if provider=='xbox360_aurora' else '')),webman_url=str(payload.get('webman_url') or '').strip() or None,nova_url=str(payload.get('nova_url') or '').strip() or None,nova_username=str(payload.get('nova_username') or '').strip() or None,nova_password=str(payload.get('nova_password') or ''),database_path=str(payload.get('database_path') or '').strip() or None)
  db.add(c);db.commit();db.refresh(c);return console_dict(c)
@app.put('/api/consoles/{console_id}')
def update_console(console_id:int,payload:dict):
 with Session(engine) as db:
  c=db.get(Console,console_id)
  if not c:raise HTTPException(404)
  for f in ('name','host','ftp_port','ftp_username','ftp_password','webman_url','provider_type','nova_url','nova_username','nova_password','database_path','image_source','enabled'):
   if f in payload:setattr(c,f,payload[f])
  db.commit();return console_dict(c)
@app.delete('/api/consoles/{console_id}')
def delete_console(console_id:int):
 with Session(engine) as db:
  c=db.get(Console,console_id)
  if not c:raise HTTPException(404)
  db.execute(text('DELETE FROM installed_games WHERE console_id=:id'),{'id':console_id});db.delete(c);db.commit();return {'ok':True}
@app.get('/api/platform-images')
def platform_images():
 with Session(engine) as db:return {x.platform:x.image_source for x in db.scalars(select(PlatformImage)).all() if x.image_source}
@app.post('/api/platform-images/{platform}')
def platform_image_upload(platform:str,file:UploadFile=File(...)):
 from urllib.parse import unquote
 platform=unquote(platform);ext=Path(file.filename or '').suffix.lower()
 if ext not in ('.jpg','.jpeg','.png','.webp'):raise HTTPException(400,'Bitte JPG, PNG oder WebP verwenden')
 raw=file.file.read()
 if len(raw)>8*1024*1024:raise HTTPException(400,'Bild maximal 8 MB')
 safe=hashlib.sha1(platform.encode()).hexdigest()[:16];folder=Path(DATA)/'platform-images';folder.mkdir(parents=True,exist_ok=True);name=f'{safe}{ext}'
 for old in folder.glob(safe+'.*'):
  try:old.unlink()
  except Exception:pass
 (folder/name).write_bytes(raw)
 with Session(engine) as db:
  row=db.get(PlatformImage,platform) or PlatformImage(platform=platform);row.image_source=f'/platform-images/{name}';db.add(row);db.commit();return {'ok':True,'platform':platform,'image_source':row.image_source}
@app.get('/platform-images/{name}')
def platform_image_file(name:str):
 p=Path(DATA)/'platform-images'/Path(name).name
 if not p.exists():raise HTTPException(404)
 return FileResponse(p)
@app.post('/api/consoles/{console_id}/image')
def console_image(console_id:int,file:UploadFile=File(...)):
 ext=Path(file.filename or '').suffix.lower()
 if ext not in ('.jpg','.jpeg','.png','.webp'):raise HTTPException(400,'Bitte JPG, PNG oder WebP verwenden')
 raw=file.file.read()
 if len(raw)>8*1024*1024:raise HTTPException(400,'Bild maximal 8 MB')
 with Session(engine) as db:
  c=db.get(Console,console_id)
  if not c:raise HTTPException(404,'Konsole nicht gefunden')
  folder=Path(DATA)/'console-images';folder.mkdir(parents=True,exist_ok=True);name=f'console-{console_id}{ext}';dest=folder/name
  for old in folder.glob(f'console-{console_id}.*'):
   try:old.unlink()
   except Exception:pass
  dest.write_bytes(raw);c.image_source=f'/console-images/{name}';db.commit();return {'ok':True,'image_source':c.image_source}
@app.delete('/api/consoles/{console_id}/image')
def console_image_delete(console_id:int):
 with Session(engine) as db:
  c=db.get(Console,console_id)
  if not c:raise HTTPException(404)
  old=c.image_source;c.image_source=None;db.commit()
 if old and old.startswith('/console-images/'):
  try:(Path(DATA)/'console-images'/Path(old).name).unlink()
  except Exception:pass
 return {'ok':True}
@app.get('/console-images/{name}')
def console_image_file(name:str):
 p=Path(DATA)/'console-images'/Path(name).name
 if not p.exists():raise HTTPException(404)
 return FileResponse(p)

@app.post('/api/consoles/{console_id}/test')
def test_console(console_id:int):
 with Session(engine) as db:
  c=db.get(Console,console_id)
  if not c:raise HTTPException(404)
  if (c.provider_type or 'ps3')=='xbox360_aurora':
   return AuroraProvider(c.host,c.ftp_port,c.ftp_username,c.ftp_password,c.nova_url,c.nova_username,c.nova_password).health()
  if c.provider_type=='xboxclassic_xbmc4gamers':
   return XBMC4GamersProvider(c.host,c.ftp_port,c.ftp_username,c.ftp_password,c.database_path or '/E/XBMC4Gamers/system/UserData/profiles/Dominic/Database/MyPrograms6.db').health()
  if c.provider_type=='ps4_goldhen':
   return PS4GoldHENProvider(c.host,c.ftp_port,c.ftp_username,c.ftp_password,c.database_path or '/system_data/priv/mms/app.db').health()
  ftp=PS3FTPProvider(c.host,c.ftp_port,c.ftp_username,c.ftp_password).health();web=PS3WebManProvider(c.webman_url).health() if c.webman_url else {'ok':False,'optional':True,'detail':'not configured'}
  return {'ftp':ftp,'webman':web}
@app.post('/api/consoles/{console_id}/scan')
def scan_console(console_id:int):
 now=datetime.now(timezone.utc).isoformat()
 with Session(engine) as db:
  c=db.get(Console,console_id)
  if not c:raise HTTPException(404)
  if c.last_scan_status=='running':raise HTTPException(409,'Für diese Konsole läuft bereits ein Scan')
  c.last_scan_status='running';c.last_scan_message='Scan läuft';db.commit()
  try:
   if (c.provider_type or 'ps3')=='xbox360_aurora':
    aurora_result=AuroraProvider(c.host,c.ftp_port,c.ftp_username,c.ftp_password,c.nova_url,c.nova_username,c.nova_password,25).scan();items=aurora_result['items'];ftp_result={'diagnostics':aurora_result['diagnostics']};web_result={'diagnostics':{'not_applicable':True}}
   elif c.provider_type=='xboxclassic_xbmc4gamers':
    classic_result=XBMC4GamersProvider(c.host,c.ftp_port,c.ftp_username,c.ftp_password,c.database_path or '/E/XBMC4Gamers/system/UserData/profiles/Dominic/Database/MyPrograms6.db',25).scan();items=classic_result['items'];ftp_result={'diagnostics':classic_result['diagnostics']};web_result={'diagnostics':{'not_applicable':True}}
   elif c.provider_type=='ps4_goldhen':
    ps4_result=PS4GoldHENProvider(c.host,c.ftp_port,c.ftp_username,c.ftp_password,c.database_path or '/system_data/priv/mms/app.db',25).scan();items=ps4_result['items'];ftp_result={'diagnostics':ps4_result['diagnostics']};web_result={'diagnostics':{'not_applicable':True}}
   else:
    ftp_result=PS3FTPProvider(c.host,c.ftp_port,c.ftp_username,c.ftp_password,25).scan();items=ftp_result['items'];web_result={'items':[],'diagnostics':{'optional':True}}
    if c.webman_url:
     web_result=PS3WebManProvider(c.webman_url,20).scan();items+=web_result['items']
   items=merge_scan_items(items)
   previous=db.scalars(select(InstalledGame).where(InstalledGame.console_id==c.id)).all();overrides={};size_cache={}
   for old_item in previous:
    old_ident=(old_item.identifier or '').replace('-','').replace('_','').upper();old_key=(old_ident,old_item.category or old_item.content_type or '',old_item.path)
    if old_item.installed_size_bytes is not None:
     size_cache[old_key]=(old_item.installed_size_bytes,old_item.size_checked_at)
     if old_item.platform=='PlayStation 3' and old_ident:
      prev=size_cache.get(('ps3',old_ident));size_cache[('ps3',old_ident)]=max([prev,(old_item.installed_size_bytes,old_item.size_checked_at)],key=lambda x:x[0]) if prev else (old_item.installed_size_bytes,old_item.size_checked_at)
   for old_item in previous:
    if old_item.match_method=='manual' and old_item.game_id:
     k=(old_item.identifier or '').replace('-','').replace('_','').upper() or (key(old_item.title),old_item.path)
     overrides[k]=(old_item.game_id,old_item.match_method,old_item.match_confidence)
   db.execute(text('DELETE FROM installed_games WHERE console_id=:id'),{'id':c.id})
   matched=unknown=playable=game_candidates=non_game=homebrew=serials_applied=0;cats={};unknown_items=[];homebrew_items=[]
   for item in items:
    cats[item.get('category') or item.get('content_type') or 'Unknown']=cats.get(item.get('category') or item.get('content_type') or 'Unknown',0)+1
    scan_key=(item.get('identifier') or '').replace('-','').replace('_','').upper() or (key(item.get('title')),item.get('path'))
    override=overrides.get(scan_key)
    if override:game=db.get(Game,override[0]);method=override[1];confidence=override[2]
    else:
     game,method,confidence=match_installed(db,item);method='parent_identifier' if game and item.get('category') in ('DLC','Title Update') else method
    item_category=item.get('category') or item.get('content_type') or ''
    title_cf=str(item.get('title') or '').casefold()
    item_id=str(item.get('identifier') or '').upper()
    is_known_non_game=item_id in NON_GAME_IDS or any(h in title_cf for h in NON_GAME_TITLE_HINTS)
    is_homebrew=(item.get('platform') in ('PlayStation 1','PlayStation 2','PlayStation 3','PlayStation Portable') and any(h in title_cf for h in HOMEBREW_HINTS))
    is_non_game=item_category in NON_GAME_CATEGORIES or is_known_non_game
    if game:
     matched+=1
     ident=(item.get('identifier') or '').replace('-','').replace('_','').upper()
     if ident and re.fullmatch(r'[A-Z]{4}\d{5}',ident) and not game.title_id and method in ('title_exact','manual'):
      game.title_id=ident;game.identifier_type='SERIAL';sources=source_map(game);sources['title_id']='console_scan';save_source_map(game,sources);serials_applied+=1
    elif not is_non_game and not is_homebrew:
     unknown+=1
     unknown_items.append({k:item.get(k) for k in ('title','identifier','content_id','category','platform','path','source')})
    is_playable=((item.get('platform') in ('Xbox 360','Xbox Classic') and item_category in ('Xbox 360 Game','XBLA','Xbox Classic')) or item_category in PLAYABLE_CATEGORIES or item.get('content_type') in ('PS3 ISO','webMAN Game')) and not is_non_game
    if is_playable:playable+=1
    if is_homebrew:
     homebrew+=1
     homebrew_items.append({k:item.get(k) for k in ('title','identifier','content_id','category','platform','path','source')})
    elif is_non_game:non_game+=1
    elif is_playable:game_candidates+=1
    item_ident=(item.get('identifier') or '').replace('-','').replace('_','').upper();cache_key=(item_ident,item.get('category') or item.get('content_type') or '',item.get('path') or '');cached_size=size_cache.get(cache_key) or (size_cache.get(('ps3',item_ident)) if item.get('platform')=='PlayStation 3' and item_ident else None)
    db.add(InstalledGame(console_id=c.id,game_id=game.id if game else None,platform=item.get('platform') or 'PlayStation 3',identifier=item.get('identifier'),title=item.get('title') or item.get('identifier') or 'Unknown',installed_version=item.get('installed_version'),content_type=item.get('content_type'),category=item.get('category'),content_id=item.get('content_id'),source=item.get('source') or 'PS3',path=item.get('path') or '',storage=item.get('storage'),last_seen_at=now,match_method=method,match_confidence=confidence,file_size=item.get('file_size'),installed_size_bytes=cached_size[0] if cached_size else item.get('installed_size_bytes'),size_checked_at=cached_size[1] if cached_size else None))
   c.last_scan_at=now;c.last_scan_status='ok';c.last_scan_message=f'{len(items)} Inhalte, {matched} zugeordnet' + (f" · /dev_hdd0/game: {ftp_result['diagnostics'].get('hdd_game',{}).get('sfo_parsed',0)} SFO gelesen, {ftp_result['diagnostics'].get('hdd_game',{}).get('sfo_failed',0)} Fehler" if (c.provider_type or 'ps3')=='ps3' else '');db.commit()
   return {'ok':True,'items':len(items),'playable':playable,'game_candidates':game_candidates,'non_game':non_game,'homebrew':homebrew,'unknown_items':unknown_items,'homebrew_items':homebrew_items,'matched':matched,'unknown':unknown,'serials_applied':serials_applied,'manual_overrides_restored':len(overrides),'categories':cats,'ftp':ftp_result['diagnostics'],'webman':web_result['diagnostics']}
  except Exception as e:
   db.rollback();c=db.get(Console,console_id);c.last_scan_at=now;c.last_scan_status='error';c.last_scan_message=f'{type(e).__name__}: {e}'[:500];db.commit();raise HTTPException(502,c.last_scan_message)
def format_bytes(value):
 value=int(value or 0);units=['B','KB','MB','GB','TB'];n=float(value)
 for unit in units:
  if n<1024 or unit==units[-1]:
   if unit=='B':return f'{int(n)} B'
   return f'{n:.2f}'.replace('.',',')+' '+unit
  n/=1024

@app.post('/api/consoles/{console_id}/scan-sizes')
def scan_console_sizes(console_id:int,payload:dict={}):
 now=datetime.now(timezone.utc).isoformat();force_all=bool(payload.get('force_all',False))
 with Session(engine) as db:
  c=db.get(Console,console_id)
  if not c:raise HTTPException(404,'Konsole nicht gefunden')
  provider=c.provider_type or 'ps3'
  if provider not in ('xbox360_aurora','ps3'):raise HTTPException(400,'Größenscan derzeit für Xbox 360 / Aurora und PS3 verfügbar')
  categories=['Xbox 360 Game','XBLA','Xbox Classic'] if provider=='xbox360_aurora' else None
  q=select(InstalledGame).where(InstalledGame.console_id==console_id)
  if categories:q=q.where(InstalledGame.category.in_(categories))
  else:q=q.where((InstalledGame.category.in_(list(PLAYABLE_CATEGORIES)))|(InstalledGame.content_type.in_(['PS3 ISO','webMAN Game','FTP Folder Game'])))
  all_rows=db.scalars(q.order_by(InstalledGame.title)).all();rows=all_rows if force_all else [x for x in all_rows if x.installed_size_bytes is None]
  skipped=len(all_rows)-len(rows)
  if not rows:return {'ok':True,'checked':0,'updated':0,'failed':0,'remote_skipped':0,'already_cached':skipped,'total':format_bytes(sum(x.installed_size_bytes or 0 for x in all_rows)),'message':'Keine fehlenden Größen'}
  c.last_scan_status='size_running';c.last_scan_message=f'Größenscan {len(rows)} Einträge';db.commit()
  try:
   if provider=='xbox360_aurora':results=AuroraProvider(c.host,c.ftp_port,c.ftp_username,c.ftp_password,c.nova_url,c.nova_username,c.nova_password,30).calculate_sizes([{'id':x.id,'path':x.path} for x in rows]);roots=results[0].get('ftp_roots',[]) if results else []
   else:results=PS3FTPProvider(c.host,c.ftp_port,c.ftp_username,c.ftp_password,30).calculate_sizes([{'id':x.id,'path':x.path} for x in rows]);roots=[]
   updated=failed=remote_skipped=0;failures=[]
   for r in results:
    x=db.get(InstalledGame,r['id'])
    if r.get('remote'):remote_skipped+=1;failures.append({'title':x.title,'source_path':r.get('path'),'error':r.get('error'),'remote':True});continue
    if not r.get('ok'):failed+=1;failures.append({'title':x.title,'source_path':r.get('source_path') or r.get('path'),'attempts':r.get('attempts',[]),'error':r.get('error')});continue
    x.installed_size_bytes=int(r.get('size_bytes',r.get('bytes',0)));x.size_checked_at=now;updated+=1
   c=db.get(Console,console_id);c.last_scan_status='ok';db.commit()
   current=db.scalars(q).all();total=sum(x.installed_size_bytes or 0 for x in current);c.last_scan_message=f'Größen {updated} neu, {skipped} Cache, {format_bytes(total)}';db.commit()
   return {'ok':True,'checked':len(rows),'updated':updated,'failed':failed,'remote_skipped':remote_skipped,'already_cached':skipped,'total':format_bytes(total),'force_all':force_all,'ftp_roots':roots,'failure_examples':failures[:20]}
  except Exception as e:
   db.rollback();c=db.get(Console,console_id);c.last_scan_status='error';c.last_scan_message=f'{type(e).__name__}: {e}'[:500];db.commit();raise HTTPException(502,c.last_scan_message)

@app.get('/api/consoles/{console_id}/installed')
def installed_games(console_id:int):
 with Session(engine) as db:
  rows=[]
  for x in db.scalars(select(InstalledGame).where(InstalledGame.console_id==console_id).order_by(InstalledGame.title)).all():
   row=installed_dict(x);row['suggestions']=[] if x.game_id else match_suggestions(db,x);row['linked_game']={'id':x.game_id,'title':db.get(Game,x.game_id).title} if x.game_id and db.get(Game,x.game_id) else None;rows.append(row)
  return rows

@app.get('/api/consoles/{console_id}/bulk-import-preview')
def bulk_import_preview(console_id:int):
 with Session(engine) as db:
  c=db.get(Console,console_id)
  if not c:raise HTTPException(404,'Konsole nicht gefunden')
  rows=db.scalars(select(InstalledGame).where(InstalledGame.console_id==console_id,InstalledGame.game_id.is_(None)).order_by(InstalledGame.title)).all()
  children={'DLC','Title Update'};candidates=[];already_existing=children_skipped=0
  for x in rows:
   if x.category in children:children_skipped+=1;continue
   ident=(x.identifier or '').replace('-','').replace('_','').upper() or None
   existing=None
   if ident:existing=db.scalar(select(Game).where(Game.platform==x.platform,func.replace(func.replace(func.upper(Game.title_id),'-',''),'_','')==ident))
   if existing:already_existing+=1;continue
   candidates.append({'installed_id':x.id,'title':x.title,'platform':x.platform,'identifier':x.identifier,'path':x.path,'size_bytes':x.installed_size_bytes,'size':format_bytes(x.installed_size_bytes) if x.installed_size_bytes is not None else None})
  return {'console':console_dict(c),'unknown_rows':len(rows),'importable':len(candidates),'already_existing':already_existing,'children_skipped':children_skipped,'examples':candidates[:30]}

@app.post('/api/consoles/{console_id}/bulk-import')
def bulk_import_console(console_id:int,payload:dict={}):
 enrich=bool(payload.get('igdb',False));created=linked_existing=failed=0;errors=[];created_ids=[]
 with Session(engine) as db:
  c=db.get(Console,console_id)
  if not c:raise HTTPException(404,'Konsole nicht gefunden')
  rows=db.scalars(select(InstalledGame).where(InstalledGame.console_id==console_id,InstalledGame.game_id.is_(None)).order_by(InstalledGame.title)).all()
  for x in rows:
   if x.category in ('DLC','Title Update'):continue
   try:
    ident=(x.identifier or '').replace('-','').replace('_','').upper() or None
    existing=db.scalar(select(Game).where(Game.platform==x.platform,func.replace(func.replace(func.upper(Game.title_id),'-',''),'_','')==ident)) if ident else None
    if existing:
     x.game_id=existing.id;x.match_method='identifier';x.match_confidence=1.0;linked_existing+=1;continue
    g=Game(platform=x.platform,title=x.title,title_id=ident,identifier_type='CUSA' if x.platform=='PlayStation 4' else ('TITLEID' if x.platform in ('Xbox 360','Xbox Classic') else 'SERIAL'),collection_status='In Sammlung',media_format='Digital' if x.category=='XBLA' else None,metadata_status='console_scan')
    sources={'title':'console_scan','platform':'console_scan'}
    if ident:sources['title_id']='console_scan'
    save_source_map(g,sources);db.add(g);db.flush();x.game_id=g.id;x.match_method='console_bulk_create';x.match_confidence=1.0;created+=1;created_ids.append(g.id)
    # XBMC4Gamers scanner already provides useful installed size; metadata enrichment can be done globally later.
    if enrich and igdb.configured():
     hits=igdb.search(g.title,g.platform,5);best=igdb.map_record(hits[0]) if hits else None
     if best and best.get('confidence',0)>=.94:apply_igdb(g,igdb.get_by_id(best['igdb_id']) or best,force=False)
   except Exception as e:failed+=1;errors.append(f'{x.title}: {type(e).__name__}: {e}'[:300])
  db.commit()
 return {'ok':True,'created':created,'linked_existing':linked_existing,'failed':failed,'created_game_ids':created_ids[:50],'errors':errors[:30]}

@app.post('/api/installed-games/{installed_id}/create-game')
def create_game_from_installed(installed_id:int,payload:dict={}):
 with Session(engine) as db:
  x=db.get(InstalledGame,installed_id)
  if not x:raise HTTPException(404,'Installierter Inhalt nicht gefunden')
  if x.game_id:
   g=db.get(Game,x.game_id);return {'created':False,'reason':'already_linked','game':serial(g),'igdb':None}
  ident=(x.identifier or '').replace('-','').replace('_','').upper() or None
  if ident and x.platform=='PlayStation 3' and not re.fullmatch(r'[A-Z]{4}\d{5}',ident):raise HTTPException(400,'Ungültige PS3-Serial')
  if ident and x.platform=='PlayStation 4' and not re.fullmatch(r'CUSA\d{5}',ident):raise HTTPException(400,'Ungültige CUSA')
  if ident and x.platform in ('Xbox 360','Xbox Classic') and not re.fullmatch(r'[0-9A-F]{8}',ident):raise HTTPException(400,'Ungültige Xbox TitleID')
  if ident:
   existing=db.scalar(select(Game).where(Game.platform==x.platform,func.replace(func.replace(func.upper(Game.title_id),'-',''),'_','')==ident))
   if existing:
    x.game_id=existing.id;x.match_method='identifier';x.match_confidence=1.0;db.commit()
    return {'created':False,'reason':'identifier_exists','game':serial(existing),'igdb':None}
  title=str(payload.get('title') or x.title or ident or 'Unbekanntes Konsolenspiel').strip()
  g=Game(platform=x.platform,title=title,title_id=ident,identifier_type='CUSA' if x.platform=='PlayStation 4' else ('TITLEID' if x.platform in ('Xbox 360','Xbox Classic') else 'SERIAL'),collection_status='In Sammlung',media_format='ISO' if 'ISO' in (x.content_type or '').upper() or '/PS3ISO/' in (x.path or '').upper() else None,metadata_status='console_scan')
  sources={'title':'console_scan','platform':'console_scan'}
  if ident:sources['title_id']='console_scan'
  save_source_map(g,sources);db.add(g);db.flush()
  x.game_id=g.id;x.match_method='console_create';x.match_confidence=1.0
  igdb_result={'attempted':False,'matched':False,'detail':'IGDB nicht konfiguriert'}
  if igdb.configured():
   igdb_result={'attempted':True,'matched':False,'detail':'kein eindeutiger Treffer'}
   try:
    hits=igdb.search(title,x.platform,10)
    best=igdb.map_record(hits[0]) if hits else None
    if best and best.get('confidence',0)>=.90:
     full=igdb.get_by_id(best['igdb_id']) or best;changed=apply_igdb(g,full,force=False)
     igdb_result={'attempted':True,'matched':True,'igdb_id':best['igdb_id'],'title':best['title'],'confidence':best['confidence'],'changed':changed}
    elif best:
     g.metadata_status='review';g.metadata_confidence=best['confidence'];g.candidate_title=best['title'];g.candidate_provider_id=str(best['igdb_id'])
     igdb_result={'attempted':True,'matched':False,'review':True,'igdb_id':best['igdb_id'],'title':best['title'],'confidence':best['confidence']}
   except Exception as e:igdb_result={'attempted':True,'matched':False,'detail':f'{type(e).__name__}: {e}'[:300]}
  db.commit();db.refresh(g)
  return {'created':True,'game':serial(g),'installed_game':installed_dict(x),'igdb':igdb_result}

@app.post('/api/installed-games/{installed_id}/match/{game_id}')
def match_installed_manual(installed_id:int,game_id:int,payload:dict={}):
 with Session(engine) as db:
  x=db.get(InstalledGame,installed_id);g=db.get(Game,game_id)
  if not x or not g:raise HTTPException(404)
  if g.platform!=x.platform:raise HTTPException(400,'Plattformen stimmen nicht überein')
  x.game_id=g.id;x.match_method='manual';x.match_confidence=1.0
  if payload.get('apply_identifier',True) and x.identifier and not g.title_id:
   g.title_id=x.identifier;g.identifier_type='CUSA' if x.platform=='PlayStation 4' else ('TITLEID' if x.platform in ('Xbox 360','Xbox Classic') else 'SERIAL');sources=source_map(g);sources['title_id']='console_scan';save_source_map(g,sources)
  db.commit();return {'ok':True,'installed_game':installed_dict(x),'game':serial(g)}
@app.post('/api/installed-games/{installed_id}/unmatch')
def unmatch_installed(installed_id:int,payload:dict={}):
 with Session(engine) as db:
  x=db.get(InstalledGame,installed_id)
  if not x:raise HTTPException(404)
  old_game_id=x.game_id;identifier_removed=False
  if old_game_id and payload.get('remove_scan_identifier',True):
   g=db.get(Game,old_game_id);sources=source_map(g) if g else {}
   scan_id=(x.identifier or '').replace('-','').replace('_','').upper()
   game_id=(g.title_id or '').replace('-','').replace('_','').upper() if g else ''
   if g and scan_id and scan_id==game_id and sources.get('title_id')=='console_scan':
    g.title_id=None;g.identifier_type=None;sources.pop('title_id',None);save_source_map(g,sources);identifier_removed=True
  x.game_id=None;x.match_method=None;x.match_confidence=None;db.commit()
  return {'ok':True,'old_game_id':old_game_id,'identifier_removed':identifier_removed}

@app.get('/api/games/{game_id}/console-content')
def game_console_content(game_id:int):
 with Session(engine) as db:
  if not db.get(Game,game_id):raise HTTPException(404,'Spiel nicht gefunden')
  consoles={c.id:c for c in db.scalars(select(Console)).all()};rows=[]
  items=db.scalars(select(InstalledGame).where(InstalledGame.game_id==game_id).order_by(InstalledGame.console_id,InstalledGame.category,InstalledGame.title)).all()
  for x in items:
   row=installed_dict(x);row['console_name']=consoles[x.console_id].name if x.console_id in consoles else x.platform;rows.append(row)
  return rows

@app.post('/api/x360db/enrich')
def enrich_x360db():
 from .providers import online
 try:catalog=online.x360_catalog()
 except Exception as e:raise HTTPException(502,f'x360db nicht erreichbar: {e}')
 out={'checked':0,'matched':0,'changed':0,'covers':0}
 with Session(engine) as db:
  for g in db.scalars(select(Game).where(Game.platform=='Xbox 360')).all():
   out['checked']+=1;row=online.x360_match(catalog,g.title_id,g.title)
   if not row:continue
   out['matched']+=1;sources=source_map(g);changed=False
   for field,names in [('title',('title',)),('developer',('developer',)),('publisher',('publisher',)),('release_date',('release_date',))]:
    v=online.pick(row,*names)
    if v and sources.get(field)!='manual' and not getattr(g,field,None):setattr(g,field,str(v));sources[field]='x360db';changed=True
   genres=row.get('genre')
   if genres and sources.get('genres')!='manual' and not g.genres:g.genres=', '.join(genres) if isinstance(genres,list) else str(genres);sources['genres']='x360db';changed=True
   cover=row.get('boxart')
   if cover and not cover_is_local(g):
    cp=online.save_cover(cover,g.id,DATA)
    if cp:g.cover_source=cp;g.cover_provider='x360db';sources['cover']='x360db';out['covers']+=1;changed=True
   save_source_map(g,sources);out['changed']+=1 if changed else 0
  db.commit()
 return out

@app.get('/api/providers/status')
def provider_status():
 from .providers import online
 result={'igdb':{'configured':igdb.configured()},'orbispatches':orbispatches.health(),'ps4_catalog':{},'ps4_updates':{},'covers':{}}
 try:result['ps4_catalog']={'ok':True,'entries':len(online.ps4_catalog()),'source':'SerialStation-derived PS4 catalog'}
 except Exception as e:result['ps4_catalog']={'ok':False,'error':str(e)[:240]}
 try:result['ps4_updates']={'ok':True,'entries':len(online.ps4_updates()),'source':'PS4 update summary'}
 except Exception as e:result['ps4_updates']={'ok':False,'error':str(e)[:240]}
 with Session(engine) as db:
  gs=db.scalars(select(Game)).all();result['covers']={'local':sum(cover_is_local(g) for g in gs),'missing':sum(not cover_is_local(g) for g in gs)}
  result['library']={'games':len(gs),'igdb_linked':sum(bool(g.metadata_provider_id) for g in gs),'ps4_cusa':sum(g.platform=='PlayStation 4' and bool(g.title_id) for g in gs),'updates_available':sum(ps4_update_status(g)=='update_available' for g in gs)}
 return result

@app.post('/api/games/{game_id}/resolve-all')
def resolve_all(game_id:int):
 from .providers import online
 trace=[]
 with Session(engine) as db:
  g=db.get(Game,game_id)
  if not g:raise HTTPException(404)
  query=g.title
  if g.platform=='PlayStation 4' and g.title_id:
   try:
    row=online.ps4_match(online.ps4_catalog(),g.title_id,g.title);title=online.pick(row,'title','name') if row else None
    trace.append({'provider':'PS4 Catalog','ok':bool(title),'detail':title or 'kein Treffer'});add_resolver_event(g,'PS4 Catalog',bool(title),title or 'kein Treffer')
    if title:query=title
   except Exception as e:trace.append({'provider':'PS4 Catalog','ok':False,'detail':str(e)[:240]})
   try:
    op=orbispatches.resolve(g.title_id);trace.append({'provider':'ORBISPatches','ok':op.get('ok',False),'detail':op.get('title') or op.get('error') or 'Patchdaten'});add_resolver_event(g,'ORBISPatches',op.get('ok',False),op.get('title') or op.get('error') or 'Patchdaten')
    if op.get('title') and (not query or query.upper().startswith('CUSA')):query=op['title']
    latest=op.get('latest') or {};v=latest.get('version')
    if v:g.remote_latest_version=str(v);g.remote_update_checked_at=datetime.now(timezone.utc).isoformat()
   except Exception as e:trace.append({'provider':'ORBISPatches','ok':False,'detail':str(e)[:240]})
  try:
   hits=igdb.search(query,g.platform,10);best=igdb.map_record(hits[0]) if hits else None
   trace.append({'provider':'IGDB','ok':bool(best),'detail':best['title'] if best else 'kein Treffer'});add_resolver_event(g,'IGDB',bool(best),best['title'] if best else 'kein Treffer')
   if best and best['confidence']>=.90:apply_igdb(g,igdb.get_by_id(best['igdb_id']) or best,force=False)
   elif best:g.metadata_status='review';g.candidate_title=best['title'];g.candidate_provider_id=str(best['igdb_id'])
  except Exception as e:trace.append({'provider':'IGDB','ok':False,'detail':str(e)[:240]})
  db.commit();db.refresh(g);return {'trace':trace,'game':serial(g)}

@app.get('/api/export/games.json')
def export_games_json():
 with Session(engine) as db:return [serial(g) for g in db.scalars(select(Game).order_by(Game.title)).all()]

@app.get('/api/games/{game_id}/delete-preview')
def delete_game_preview(game_id:int):
 with Session(engine) as db:
  g=db.get(Game,game_id)
  if not g:raise HTTPException(404,'Spiel nicht gefunden')
  installed=db.scalars(select(InstalledGame).where(InstalledGame.game_id==game_id)).all()
  exclusions=db.scalar(select(func.count(DuplicateExclusion.id)).where((DuplicateExclusion.game_a_id==game_id)|(DuplicateExclusion.game_b_id==game_id))) or 0
  return {'id':g.id,'title':g.title,'platform':g.platform,'title_id':g.title_id,'packages':len(g.packages),'installed_links':len(installed),'local_cover':g.cover_source if cover_is_local(g) else None,'duplicate_exclusions':exclusions}

@app.delete('/api/games/{game_id}')
def delete_game(game_id:int):
 cover_path=None
 with Session(engine) as db:
  g=db.get(Game,game_id)
  if not g:raise HTTPException(404,'Spiel nicht gefunden')
  if cover_is_local(g):cover_path=Path(DATA)/'covers'/Path(g.cover_source).name
  packages=len(g.packages);links=db.scalars(select(InstalledGame).where(InstalledGame.game_id==game_id)).all()
  for x in links:x.game_id=None;x.match_method=None;x.match_confidence=None
  db.execute(text('DELETE FROM duplicate_exclusions WHERE game_a_id=:id OR game_b_id=:id'),{'id':game_id})
  db.delete(g);db.commit()
 if cover_path and cover_path.exists():
  try:cover_path.unlink()
  except Exception:pass
 return {'ok':True,'deleted_game_id':game_id,'packages_removed':packages,'console_links_released':len(links),'cover_removed':bool(cover_path)}

@app.post('/api/games')
def create_game(payload:dict):
 title=str(payload.get('title') or '').strip();platform=str(payload.get('platform') or '').strip()
 if not title:raise HTTPException(400,'Titel ist erforderlich')
 if not platform:raise HTTPException(400,'Plattform ist erforderlich')
 with Session(engine) as db:
  g=Game(platform=platform,title=title,title_id=(str(payload.get('title_id')).strip().upper() if payload.get('title_id') else None),identifier_type=payload.get('identifier_type'),collection_status=payload.get('collection_status') or 'In Sammlung',region=payload.get('region'),media_format=payload.get('media_format'),edition=payload.get('edition'),metadata_status='manual')
  sources={'title':'manual','platform':'manual'}
  if g.title_id:sources['title_id']='manual'
  save_source_map(g,sources);db.add(g);db.commit();db.refresh(g);return serial(g)

@app.post('/api/updates/ps4/refresh')
def refresh_ps4_updates():
 from .providers import online
 try:rows=online.ps4_updates()
 except Exception as e:raise HTTPException(502,f'PS4 Updatequelle nicht erreichbar: {e}')
 out={'checked':0,'matched':0,'update_available':0,'current':0,'unknown':0,'errors':0}
 with Session(engine) as db:
  games=db.scalars(select(Game).where(Game.platform=='PlayStation 4')).all()
  for g in games:
   out['checked']+=1
   try:
    r=online.update_match(rows,g.title_id) if g.title_id else None
    v=online.pick(r,'latest_version','latest version','version','app_ver','app version') if r else None
    if v:g.remote_latest_version=str(v);out['matched']+=1;add_resolver_event(g,'PS4 Update Summary',True,v)
    elif g.title_id:
     try:
      op=orbispatches.resolve(g.title_id);latest=op.get('latest') or {};ov=latest.get('version')
      if ov:g.remote_latest_version=str(ov);out['matched']+=1;add_resolver_event(g,'ORBISPatches Updates',True,ov)
      else:add_resolver_event(g,'ORBISPatches Updates',False,op.get('error') or 'kein Patch')
     except Exception as oe:add_resolver_event(g,'ORBISPatches Updates',False,str(oe)[:240])
    g.remote_update_checked_at=datetime.now(timezone.utc).isoformat()
    st=ps4_update_status(g);out[st]=out.get(st,0)+1
   except Exception:out['errors']+=1
  db.commit()
 return out

@app.get('/api/packages/size-audit')
def package_size_audit(threshold:float=500):
 with Session(engine) as db:
  rows=db.scalars(select(Package).where(Package.size_gb>threshold).order_by(Package.size_gb.desc())).all()
  return [{'id':p.id,'filename':p.filename,'name':p.name,'category':p.category,'size_gb':p.size_gb,'game_id':p.game_id,'suggested_div1000':round(p.size_gb/1000,3)} for p in rows]
@app.post('/api/packages/{package_id}/size-divide-1000')
def package_size_divide(package_id:int):
 with Session(engine) as db:
  p=db.get(Package,package_id)
  if not p:raise HTTPException(404,'Package nicht gefunden')
  if p.size_gb is None:raise HTTPException(400,'Keine Größe vorhanden')
  old=p.size_gb;p.size_gb=round(p.size_gb/1000,6);db.commit();return {'ok':True,'old':old,'new':p.size_gb}

@app.put('/api/packages/{package_id}')
def edit_package(package_id:int,payload:dict):
 with Session(engine) as db:
  pkg=db.get(Package,package_id)
  if not pkg:raise HTTPException(404,'Package nicht gefunden')
  category=normalize_package_category(payload.get('category',pkg.category));version=payload.get('version',pkg.version)
  version=(str(version).strip() or None) if version is not None else None
  if category=='DLC':version=None
  pkg.category=category;pkg.version=version
  if 'location' in payload:pkg.location=str(payload.get('location') or '').strip() or None
  if 'size_gb' in payload:pkg.size_gb=nfloat(payload.get('size_gb')) if payload.get('size_gb') not in (None,'') else None
  if 'decision' in payload:pkg.decision=str(payload.get('decision') or '').strip() or None
  db.commit();db.refresh(pkg);return {'id':pkg.id,'filename':pkg.filename,'category':pkg.category,'version':pkg.version,'location':pkg.location,'size_gb':pkg.size_gb,'decision':pkg.decision}

@app.get('/api/import/packages/schema')
def package_import_schema():
    return {'required':['Filename','Category'],'recommended':['Title ID','Name','Version','Version pkg','Location','Size (GB)'],'optional':['Newest Patch','Entscheidung'],'rules':{'Game':'version from Version pkg','Patch':'version from Version','DLC':'version is empty','Category':'Game, Patch/Update, DLC/Addon/Add-on'}}
@app.get('/api/import/packages/template.xlsx')
def package_import_template():
    from openpyxl import Workbook
    wb=Workbook();ws=wb.active;ws.title='Packages';headers=['Filename','Title ID','Name','Category','Version','Version pkg','Newest Patch','Entscheidung','Location','Size (GB)'];ws.append(headers)
    ws.append(['Example Game.pkg','CUSA00001','Example Game','Game','','1.00','','Keep','Volume1',35.5]);ws.append(['Example Patch.pkg','CUSA00001','Example Game','Patch','1.12','','1.12','Keep','Volume1',4.2]);ws.append(['Example DLC.pkg','CUSA00001','Example DLC','DLC','','','','Keep','Volume2',0.8])
    out=Path(DATA)/'cache'/'gamevault-package-import-template.xlsx';out.parent.mkdir(parents=True,exist_ok=True);wb.save(out);return FileResponse(out,filename='gamevault-package-import-template.xlsx')

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

def duplicate_pair_ids(a_id,b_id):return (min(int(a_id),int(b_id)),max(int(a_id),int(b_id)))
def duplicate_excluded(db,a_id,b_id):
 x,y=duplicate_pair_ids(a_id,b_id)
 return db.scalar(select(DuplicateExclusion.id).where(DuplicateExclusion.game_a_id==x,DuplicateExclusion.game_b_id==y)) is not None
def duplicate_score(a,b):
 from difflib import SequenceMatcher
 if a.platform!=b.platform:return 0.0,[]
 reasons=[]
 if a.title_id and b.title_id and a.title_id==b.title_id:return 1.0,['gleiche TitleID']
 if a.metadata_provider_id and b.metadata_provider_id:
  if a.metadata_provider_id==b.metadata_provider_id:return .99,['gleiche IGDB-ID']
  # Two distinct IGDB IDs are strong evidence against a duplicate.
  return 0.0,['unterschiedliche IGDB-IDs']
 title_score=SequenceMatcher(None,key(a.title),key(b.title)).ratio()
 if title_score>=.94:reasons.append(f'Titel {round(title_score*100)} %')
 ya=re.search(r'\d{4}',a.release_date or '');yb=re.search(r'\d{4}',b.release_date or '')
 if ya and yb and ya.group()!=yb.group():title_score=max(0,title_score-.12);reasons.append('unterschiedliche Releasejahre')
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
    if duplicate_excluded(db,a.id,b.id):continue
    score,reasons=duplicate_score(a,b)
    if score>=.94:
     keep,merge=preferred_merge_target(a,b)
     out.append({'keep':serial(keep),'merge':serial(merge),'score':round(score,3),'reasons':reasons,'conflicts':conflict_fields(keep,merge)})
  return sorted(out,key=lambda x:x['score'],reverse=True)

@app.post('/api/duplicates/not-duplicate/{game_a_id}/{game_b_id}')
def duplicate_not_duplicate(game_a_id:int,game_b_id:int):
 x,y=duplicate_pair_ids(game_a_id,game_b_id)
 if x==y:raise HTTPException(400,'Ungültiges Paar')
 with Session(engine) as db:
  if not db.get(Game,x) or not db.get(Game,y):raise HTTPException(404,'Spiel nicht gefunden')
  if not duplicate_excluded(db,x,y):db.add(DuplicateExclusion(game_a_id=x,game_b_id=y,created_at=datetime.now(timezone.utc).isoformat()))
  db.commit();return {'ok':True,'game_a_id':x,'game_b_id':y}

@app.delete('/api/duplicates/not-duplicate/{game_a_id}/{game_b_id}')
def duplicate_restore(game_a_id:int,game_b_id:int):
 x,y=duplicate_pair_ids(game_a_id,game_b_id)
 with Session(engine) as db:
  row=db.scalar(select(DuplicateExclusion).where(DuplicateExclusion.game_a_id==x,DuplicateExclusion.game_b_id==y))
  if row:db.delete(row);db.commit()
  return {'ok':True}

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
  save_source_map(a,sources);db.execute(text('DELETE FROM duplicate_exclusions WHERE game_a_id = :id OR game_b_id = :id'),{'id':b.id});db.flush();db.delete(b);db.commit()
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
 allowed={'title','title_id','identifier_type','publisher','developer','genres','release_date','description','current_value','collection_status','completeness','completed','game_modes','perspectives','themes','franchises','engines','pricecharting_url','cover_source','region','media_format','edition','storefront','tags','notes'}
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
  if not g.identifier_type:g.identifier_type={'PlayStation 4':'CUSA','PlayStation 3':'SERIAL','PlayStation 2':'SERIAL','PlayStation 1':'SERIAL','PlayStation Portable':'SERIAL','Xbox 360':'TITLEID','Xbox Classic':'TITLEID'}.get(g.platform,'OTHER')
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
*{box-sizing:border-box}html,body{height:100%;margin:0}body{background:#070d1a;color:#e7edf7;font:14px system-ui,Segoe UI,sans-serif;overflow:hidden}.top{height:72px;display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #1f2937;padding:0 28px;background:#08101e}.brand{font-size:22px;font-weight:800}.mut{color:#8996aa}.shell{height:calc(100vh - 72px);max-width:1500px;margin:auto;padding:18px 24px;display:grid;grid-template-rows:auto auto 1fr;gap:14px}.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}.card,.detail,.bar,.stat{background:#0c1424;border:1px solid #1f2b40;border-radius:16px}.stat{padding:14px 17px}.stat b{font-size:22px;display:block;margin-top:3px}.platform-stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px}.platform-stat{position:relative;min-height:116px;padding:14px 16px 14px 88px;cursor:pointer;overflow:hidden;border-left:5px solid var(--accent,#64748b)}.platform-stat:hover{border-color:var(--accent,#64748b);background:#101d34}.console-visual{position:absolute;left:12px;top:12px;width:62px;height:70px;border-radius:12px;background:linear-gradient(145deg,color-mix(in srgb,var(--accent,#64748b) 32%,#111827),#111827);display:flex;align-items:center;justify-content:center;color:var(--accent,#64748b);font-size:31px;font-weight:900}.console-visual img{width:100%;height:100%;object-fit:contain;padding:5px}.platform-stat b{font-size:20px;display:block;margin:3px 0}.platform-status{font-size:11px;line-height:1.35;color:#94a3b8}.backup-stats{display:flex;gap:16px;flex-wrap:wrap;padding:7px 4px 0;color:#8996aa;font-size:12px}.filtered-count{display:flex;align-items:center;white-space:nowrap;padding:0 8px;color:#cbd5e1;font-weight:700}.bar{display:flex;gap:8px;padding:10px}.btn,input,select{background:#111a2b;color:#eef;border:1px solid #283449;padding:10px 12px;border-radius:10px}.btn{cursor:pointer}.blue{background:#2563eb;border-color:#2563eb}.bar input{flex:1}.layout{min-height:0;display:grid;grid-template-columns:minmax(390px,.9fr) minmax(530px,1.35fr);gap:16px}.listpane,.detail{min-height:0;overflow-y:auto;scrollbar-color:#334155 transparent}.listpane{display:grid;grid-template-columns:1fr 1fr;gap:10px;align-content:start;padding-right:4px}.card{padding:0;overflow:hidden;cursor:pointer;min-height:148px;display:grid;grid-template-columns:82px 1fr}.card:hover,.card.on{border-color:#3b82f6;background:#101d34}.cover{background:linear-gradient(145deg,#1e3a5f,#111827);display:flex;align-items:center;justify-content:center;color:#7092ba;font-size:30px;position:relative}.cover img{width:100%;height:100%;object-fit:cover}.meta{padding:13px}.tag{display:inline-block;background:#1d4ed8;padding:4px 7px;border-radius:7px;font-size:10px}.warning{color:#fbbf24}.title{font-size:16px;font-weight:750;margin:10px 0 4px}.small{font-size:12px}.detail{padding:22px}.hero{display:grid;grid-template-columns:145px 1fr auto;gap:20px;align-items:start}.heroCover{width:145px;height:195px;background:linear-gradient(145deg,#1e3a5f,#111827);border-radius:14px;display:flex;align-items:center;justify-content:center;font-size:42px;color:#7092ba;overflow:hidden}.heroCover img{width:100%;height:100%;object-fit:cover}.detail h1{font-size:28px;margin:8px 0}.value{background:#111a2b;border-radius:14px;padding:12px 16px;text-align:right}.value b{font-size:19px}.infos{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin:18px 0}.info{background:#111a2b;border-radius:11px;padding:10px;min-height:59px}.desc{line-height:1.55;color:#bdc8d8;white-space:pre-line}.pkghead,.pkg{display:grid;grid-template-columns:1.55fr .5fr .5fr .6fr .5fr auto;gap:8px;align-items:center}.pkghead{color:#7f8da3;font-size:11px;padding:8px 0}.pkg{border-top:1px solid #263248;padding:10px 0}.modal{display:none;position:fixed;inset:0;background:#000b;z-index:10;align-items:center;justify-content:center}.modal.show{display:flex}.box{width:min(620px,92vw);background:#0c1424;border:1px solid #33415c;border-radius:18px;padding:20px}.up{border:1px dashed #405170;padding:14px;border-radius:12px;margin:10px 0}@media(max-width:1000px){body{overflow:auto}.shell{height:auto}.layout{grid-template-columns:1fr}.listpane,.detail{overflow:visible}.listpane{grid-template-columns:1fr 1fr}.infos{grid-template-columns:1fr 1fr}}@media(max-width:650px){.stats,.platform-stats,.listpane{grid-template-columns:1fr}.hero{grid-template-columns:100px 1fr}.heroCover{width:100px;height:140px}.value{grid-column:1/3}.pkghead{display:none}.pkg{grid-template-columns:1fr 1fr}}

.card{border-left:5px solid var(--accent,#64748b)}.card:hover,.card.on{border-color:var(--accent,#64748b)}.tag{background:var(--accent,#64748b)}.platform-mark{color:var(--accent,#64748b);font-size:16px;font-weight:800}.PS4{--accent:#2166d1}.PS3{--accent:#c33939}.PS2{--accent:#d6a51d}.X360{--accent:#269b45}.XCLASSIC{--accent:#4caf50}.OTHER{--accent:#64748b}
.editor-actions{display:flex;gap:8px;flex-wrap:wrap;margin:18px 0}.editor-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}.editor-grid label{display:flex;flex-direction:column;gap:4px}.editor-grid textarea{min-height:90px}.wide{grid-column:1/-1}.spinner{display:inline-block;width:15px;height:15px;border:2px solid #64748b;border-top-color:#fff;border-radius:50%;animation:spin .7s linear infinite}@keyframes spin{to{transform:rotate(360deg)}}.candidate{display:grid;grid-template-columns:60px 1fr auto;gap:10px;padding:9px;border-top:1px solid #263248}.candidate img{width:55px;height:75px;object-fit:cover}.actions{display:flex;justify-content:flex-end;gap:8px;margin-top:12px}.global-busy{display:none;position:fixed;right:20px;bottom:20px;z-index:99;background:#172238;border:1px solid #3b82f6;border-radius:12px;padding:12px 16px;box-shadow:0 8px 30px #0008}.global-busy.show{display:block}.field-card{border-left:4px solid #3b82f6}.field-critical{border-left-color:#ef4444;background:#281318}.field-optional{border-left-color:#eab308;background:#27220f}.field-manual{border-left-color:#f59e0b}.field-auto{border-left-color:#3b82f6}.qualitybar{height:8px;background:#172238;border-radius:99px;overflow:hidden}.qualitybar>span{display:block;height:100%;background:#3b82f6}.top-actions{display:flex;gap:7px;flex-wrap:wrap;justify-content:flex-end}.admin-only{display:none!important}body.admin-mode .admin-only{display:inline-flex!important}.auth-state{align-self:center;color:#94a3b8}.selection-btn.active{background:#7c3aed;border-color:#7c3aed}.selection-summary{padding:8px 12px;border:1px solid #3b2a62;background:#17102b;border-radius:12px;margin-bottom:12px}.app-dialog{display:none;position:fixed;inset:0;background:#000c;z-index:300;align-items:center;justify-content:center;padding:16px}.app-dialog.show{display:flex}.dialog-card{background:#0c1424;border:1px solid #33415c;border-radius:16px;padding:18px;width:min(580px,96vw);max-height:85vh;overflow:auto}.dialog-actions{display:flex;gap:8px;justify-content:flex-end;margin-top:14px}@media(max-width:700px){.top{height:auto;min-height:72px;padding:12px 14px;gap:10px;align-items:flex-start}.top-actions{max-width:60%}.shell{height:auto;padding:10px}.bar{position:sticky;top:0;z-index:4}.editor-grid{grid-template-columns:1fr}.wide{grid-column:auto}.dialog-card{width:100%}.btn{min-height:42px}.detail{padding:14px}}
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
.wide-dialog{width:min(980px,96vw)}.dq-row,.dup-row{border:1px solid #263248;border-radius:12px;padding:12px;margin:8px 0;background:#0a1220}.dup-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}.conflict{color:#fbbf24;font-size:12px}.score-pill{display:inline-block;padding:3px 7px;border-radius:99px;background:#17335d;color:#93c5fd}@media(max-width:700px){.dup-grid{grid-template-columns:1fr}.wide-dialog{width:100%}}
.managed-modal{padding:clamp(8px,2vh,20px);overflow:hidden;overscroll-behavior:contain}
.managed-box{padding:0!important;width:min(980px,96vw)!important;height:min(860px,calc(100vh - 24px));height:min(860px,calc(100dvh - 24px));max-height:calc(100vh - 24px)!important;max-height:calc(100dvh - 24px)!important;display:flex;flex-direction:column;overflow:hidden;border-radius:18px}
.managed-header{flex:0 0 auto;display:flex;align-items:center;justify-content:space-between;gap:12px;padding:14px 18px;border-bottom:1px solid #263248;background:#0c1424;z-index:2}.managed-header h2{margin:0}
.managed-scroll{flex:1 1 auto;min-height:0;overflow-y:auto;overflow-x:hidden;-webkit-overflow-scrolling:touch;overscroll-behavior:contain;touch-action:pan-y;padding:10px 18px 24px}
.managed-footer{flex:0 0 auto;display:flex;align-items:center;gap:8px;padding:12px 18px calc(12px + env(safe-area-inset-bottom));border-top:1px solid #263248;background:#0c1424;box-shadow:0 -8px 24px #0005;z-index:3}.managed-footer input{flex:1;min-width:0}.footer-end{justify-content:flex-end}
#duplicatesModal .managed-footer{justify-content:space-between}.candidate{grid-template-columns:60px minmax(0,1fr) auto}.candidate .btn{align-self:center}
@media(max-width:700px){.managed-modal{padding:0!important;align-items:stretch!important}.managed-box{width:100vw!important;height:100vh;height:100dvh;max-height:100vh!important;max-height:100dvh!important;border-radius:0!important}.managed-header{padding:12px 14px}.managed-scroll{padding:8px 12px 24px}.managed-footer{padding:10px 12px calc(10px + env(safe-area-inset-bottom));flex-wrap:wrap}.managed-footer input{flex-basis:100%}.managed-footer .btn{min-height:44px}.candidate{grid-template-columns:52px minmax(0,1fr);}.candidate img{width:48px;height:66px}.candidate .btn{grid-column:1/-1;width:100%}}
.dup-actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px}.dup-details{display:none;margin-top:10px;border-top:1px solid #263248;padding-top:10px}.dup-details.show{display:block}.compare-table{width:100%;border-collapse:collapse;font-size:12px}.compare-table th,.compare-table td{padding:6px 8px;border-bottom:1px solid #1f2b40;text-align:left;vertical-align:top}.compare-table th{color:#94a3b8;width:120px}.mini-cover{width:72px;height:98px;object-fit:cover;background:#111827;border-radius:7px}.no-duplicate{background:#374151;border-color:#4b5563}@media(max-width:700px){.compare-table th{width:88px}.dup-actions .btn{flex:1 1 100%}}.provider-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.provider-card{background:#0a1220;border:1px solid #263248;border-radius:12px;padding:12px}.provider-ok{border-left:4px solid #22c55e}.provider-bad{border-left:4px solid #ef4444}.resolver-event{padding:6px 0;border-bottom:1px solid #1f2b40}@media(max-width:700px){.provider-grid{grid-template-columns:1fr}}.console-card{position:relative;min-height:150px;padding-left:150px!important;border:1px solid #263248;border-radius:14px;background:#0a1220;padding:14px;margin:8px 0}.console-image{position:absolute;left:14px;top:14px;width:120px;height:92px;border-radius:12px;background:#111827;display:flex;align-items:center;justify-content:center;overflow:hidden;color:#64748b;font-weight:800}.console-image img{width:100%;height:100%;object-fit:contain;padding:4px}.console-actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px}.installed-row{display:grid;grid-template-columns:1.5fr .7fr .55fr .8fr;gap:8px;padding:9px;border-bottom:1px solid #1f2b40}.status-ok{color:#4ade80}.status-error{color:#f87171}@media(max-width:700px){.installed-row{grid-template-columns:1fr 1fr}.console-actions .btn{flex:1 1 45%}}.install-badge{display:inline-block;background:#14532d;color:#86efac;padding:3px 7px;border-radius:7px}.suggestions{grid-column:1/-1;background:#111a2b;padding:8px;border-radius:8px}.suggestion-btn{margin:3px}.storage-pill{display:inline-block;background:#1e293b;padding:2px 6px;border-radius:6px}.installed-toolbar{display:flex;align-items:center;gap:8px;padding:10px 18px;border-bottom:1px solid #263248;background:#0c1424;flex-wrap:wrap}.installed-toolbar input[type=text],.installed-toolbar>input{flex:1;min-width:220px}.library-result{display:grid;grid-template-columns:54px 1fr auto;gap:10px;align-items:center;padding:9px;border-bottom:1px solid #1f2b40}.library-result img{width:48px;height:66px;object-fit:cover;border-radius:6px}@media(max-width:700px){.library-result{grid-template-columns:48px 1fr}.library-result .btn{grid-column:1/-1}.installed-toolbar>*{flex:1 1 100%}}.installed-parent{border:1px solid #263248;border-radius:12px;margin:9px 0;overflow:hidden;background:#0a1220}.installed-parent>.installed-row{border-bottom:0}.installed-children{margin:0 10px 10px 34px;border-left:3px solid #334155;padding-left:10px}.installed-child{display:grid;grid-template-columns:1.5fr .65fr .55fr;gap:8px;padding:8px;border-top:1px solid #1f2b40;background:#0d1728}.installed-child:first-child{border-top:0}.child-title{color:#cbd5e1}.unmatch-btn{border-color:#7f1d1d;background:#31131a}@media(max-width:700px){.installed-children{margin-left:10px}.installed-child{grid-template-columns:1fr 1fr}.installed-child>span:first-child{grid-column:1/-1}}.console-content-group{margin:10px 0;background:#0a1220;border:1px solid #263248;border-radius:12px;padding:12px}.console-content-group h4{margin:0 0 8px}.console-content-line{display:grid;grid-template-columns:1.6fr .55fr .55fr .65fr;gap:8px;padding:7px 0;border-top:1px solid #1f2b40}.console-content-line:first-of-type{border-top:0}.delete-summary{background:#281318;border:1px solid #7f1d1d;padding:12px;border-radius:10px}@media(max-width:700px){.console-content-line{grid-template-columns:1fr 1fr}.console-content-line>span:first-child{grid-column:1/-1}}</style></head><body><header class="top"><div><div class="brand">GameVault</div><div class="mut small">Sammlung, Backups und Metadaten · v1.2.0-dev30</div></div><div class="top-actions"><button class="btn" onclick="openSelections()">Meine Auswahl <span id="selectionCount"></span></button><span id="authState" class="auth-state small">Besuchermodus</span><button id="authButton" class="btn" onclick="toggleAdmin()">Verwaltung freischalten</button><span class="admin-only"><button class="btn" onclick="openConsoles()">Meine Konsolen</button><button class="btn" onclick="openPlatformImages()">Plattformbilder</button><button class="btn blue" onclick="openNewGame()">+ Spiel</button><button class="btn" onclick="openProviders()">Quellen & Resolver</button><button class="btn" onclick="refreshUpdates()">PS4 Updates</button><button class="btn" onclick="openSizeAudit()">Größenprüfung</button><button class="btn" onclick="openQuality()">Datenqualität</button><button class="btn" onclick="openDuplicates()">Duplikate</button><button class="btn" onclick="igdbRefresh()">IGDB aktualisieren</button><button class="btn" onclick="localizeCovers()">Cover lokal speichern</button><button class="btn" onclick="covers()">Cover aktualisieren</button><button class="btn blue" onclick="modal(true)">Import</button></span></div></header><main class="shell"><section id="platformStats" class="platform-stats"></section><div id="backupStats" class="backup-stats"></div><div class="bar"><input id="q" placeholder="Titel oder TitleID suchen ..." oninput="render()"><select id="pf" onchange="render()"><option value="">Alle Plattformen</option></select><select id="mf" onchange="render()"><option value="">Alle Metadaten</option><option value="missing">Metadaten fehlen</option><option value="review">Zuordnung prüfen</option><option value="cover">Cover fehlt</option><option value="id">TitleID / Serial fehlt</option><option value="localmp">Local Multiplayer</option><option value="localcoop">Local Co-op</option><option value="onlinemp">Online Multiplayer</option><option value="updates">Update verfügbar</option><option value="ps3installed">Auf PS3 verfügbar</option><option value="ps3notinstalled">Nicht auf PS3 verfügbar</option><option value="x360installed">Auf Xbox 360 verfügbar</option><option value="x360notinstalled">Nicht auf Xbox 360 verfügbar</option><option value="xclassicinstalled">Auf Xbox Classic verfügbar</option><option value="xclassicnotinstalled">Nicht auf Xbox Classic verfügbar</option></select><span id="filteredCount" class="filtered-count">- Spiele</span></div><div class="layout"><section class="listpane" id="list"></section><aside class="detail" id="detail"><span class="mut">Spiel auswählen</span></aside></div></main><div id="modal" class="modal"><div class="box"><h2>Daten importieren</h2><p class="mut">Game Collector XML zuerst, danach PS4 XLSX. Re-Import aktualisiert vorhandene Datensätze.</p><div class="up"><b>Game Collector XML</b><br><input type="file" id="xml" accept=".xml"><button class="btn" onclick="upload('xml','/api/import/gamecollector')">Importieren</button></div><div class="up"><b>PS4 Paketliste (XLSX)</b><br><span class="mut small">Spezialimport für Package-Inventar.</span><br><input type="file" id="xlsx" accept=".xlsx"><button class="btn" onclick="upload('xlsx','/api/import/packages')">Importieren</button> <a class="btn" href="/api/import/packages/template.xlsx">Vorlage laden</a> <button class="btn" onclick="showPackageSchema()">Spalten anzeigen</button></div><p id="msg"></p><button class="btn" onclick="modal(false)">Schließen</button></div></div><div id="editorModal" class="modal editor-modal"><div class="box editor-box"><div class="editor-header"><h2>Metadaten bearbeiten</h2><button type="button" class="btn editor-close" onclick="closeEditor()" aria-label="Schließen">Schließen</button></div><div class="editor-scroll"><div class="editor-grid"><label>Titel<input id="edTitle"></label><label>Plattform<input id="edPlatform" disabled></label><label>Identifier<select id="edType"><option>CUSA</option><option>SERIAL</option><option>TITLEID</option><option>OTHER</option></select></label><label>TitleID / Serial<input id="edTid"></label><label>IGDB ID<input id="edIgdb"></label><label>Publisher<input id="edPublisher"></label><label>Developer<input id="edDeveloper"></label><label>Genre<input id="edGenres"></label><label>Release<input id="edRelease"></label><label>Wert<input id="edValue"></label><label>Game Modes<input id="edModes"></label><label>Perspektive<input id="edPerspective"></label><label>Themes<input id="edThemes"></label><label>Franchise<input id="edFranchise"></label><label>Engine<input id="edEngine"></label><label>Sammlungsstatus<input id="edCollection"></label><label>Vollständigkeit<input id="edCompleteness"></label><label>Region<select id="edRegion"><option value="">–</option><option>PAL</option><option>NTSC-U/C</option><option>NTSC-J</option><option>Region Free</option></select></label><label>Format<select id="edFormat"><option value="">–</option><option>Physisch</option><option>Digital</option><option>PKG-Backup</option><option>ISO</option><option>ROM</option><option>Ordner/Extracted</option></select></label><label>Edition<input id="edEdition" placeholder="Standard, GOTY, Collector’s..."></label><label>Storefront<input id="edStorefront"></label><label class="wide">Tags<input id="edTags" placeholder="Partyabend, VR, Favorit"></label><label class="wide">Notizen<textarea id="edNotes"></textarea></label><label>PriceCharting URL<input id="edPriceUrl"></label><label>Cover URL<input id="edCoverUrl" placeholder="https://..."></label><label class="wide">Beschreibung<textarea id="edDescription"></textarea></label></div></div><div class="actions editor-footer"><button class="btn" onclick="closeEditor()">Abbrechen</button><button class="btn blue" id="saveBtn" onclick="saveMetadata()">Speichern</button></div></div></div><div id="igdbModal" class="modal managed-modal"><div class="box managed-box"><div class="managed-header"><h2>IGDB suchen</h2><div id="igdbState" class="mut"></div></div><div class="managed-scroll"><div id="igdbResults"></div></div><div class="managed-footer"><input id="directId" placeholder="IGDB ID direkt" inputmode="numeric"><button class="btn" onclick="directLoad()">ID laden</button><button class="btn" onclick="closeIgdb()">Schließen</button></div></div></div><div id="traceModal" class="modal"><div class="box"><h2>ID / IGDB auflösen</h2><div id="traceState"><span class="spinner"></span> Suche läuft ...</div><div id="traceRows"></div><div class="actions"><button class="btn" onclick="traceModal.classList.remove('show')">Schließen</button></div></div></div><div id="globalBusy" class="global-busy"><span class="spinner"></span> <span id="busyText">Abfrage läuft ...</span></div><div id="platformImagesModal" class="app-dialog managed-modal"><div class="dialog-card wide-dialog managed-box"><div class="managed-header"><h2>Plattformbilder</h2></div><div class="managed-scroll"><div id="platformImagesBody"></div></div><div class="managed-footer"><button class="btn" onclick="platformImagesModal.classList.remove('show')">Schließen</button></div></div></div><div id="consolesModal" class="app-dialog managed-modal"><div class="dialog-card wide-dialog managed-box"><div class="managed-header"><h2>Meine Konsolen</h2><button class="btn blue" onclick="openConsoleEditor()">+ Konsole</button></div><div class="managed-scroll"><div id="consolesBody"></div></div><div class="managed-footer"><button class="btn" onclick="consolesModal.classList.remove('show')">Schließen</button></div></div></div><div id="consoleEditorModal" class="app-dialog"><div class="dialog-card"><h2>Konsole hinzufügen</h2><div class="editor-grid"><label>Typ<select id="conProvider" onchange="consoleProviderChanged()"><option value="ps3">PlayStation 3 / webMAN</option><option value="xbox360_aurora">Xbox 360 / Aurora</option><option value="xboxclassic_xbmc4gamers">Xbox Classic / XBMC4Gamers</option><option value="ps4_goldhen">PlayStation 4 / GoldHEN</option></select></label><label>Name<input id="conName" placeholder="Konsole"></label><label>IP / Host<input id="conHost" placeholder="192.168.1.50"></label><label>FTP Port<input id="conPort" value="21" inputmode="numeric"></label><label>FTP Benutzer<input id="conUser" value="anonymous"></label><label>FTP Passwort<input id="conPass" type="password"></label><label id="webmanLabel">webMAN URL (optional)<input id="conWebman" placeholder="http://192.168.1.50/"></label><label id="novaUrlLabel">NOVA URL (optional)<input id="conNovaUrl" placeholder="http://192.168.1.60:9999"></label><label id="novaUserLabel">NOVA Benutzer<input id="conNovaUser" value="xboxhttp"></label><label id="novaPassLabel">NOVA Passwort<input id="conNovaPass" type="password" value="xboxhttp"></label><label id="dbPathLabel">Datenbankpfad<input id="conDbPath" value="/E/XBMC4Gamers/system/UserData/profiles/Dominic/Database/MyPrograms6.db"></label><label>Bild (JPG/PNG/WebP)<input id="conImage" type="file" accept="image/jpeg,image/png,image/webp"></label></div><p class="mut small">GameVault verwendet FTP und webMAN ausschließlich lesend. Das Passwort wird in dev1 noch in der PostgreSQL-Datenbank gespeichert; nutze nach Möglichkeit anonymen FTP-Zugriff oder einen separaten Read-only-Zugang.</p><div class="dialog-actions"><button class="btn" onclick="consoleEditorModal.classList.remove('show')">Abbrechen</button><button class="btn blue" onclick="saveConsole()">Speichern</button></div></div></div><div id="installedModal" class="app-dialog managed-modal"><div class="dialog-card wide-dialog managed-box"><div class="managed-header"><h2 id="installedTitle">Installierte Inhalte</h2></div><div class="installed-toolbar"><select id="installedStatus" onchange="renderInstalled()"><option value="unknown">Unbekannt</option><option value="all">Alle</option><option value="matched">Zugeordnet</option></select><select id="installedType" onchange="renderInstalled()"><option value="">Alle Typen</option></select><span id="installedCounts" class="mut small"></span></div><div class="managed-scroll"><div id="installedBody"></div></div><div class="managed-footer"><button class="btn" onclick="installedModal.classList.remove('show')">Schließen</button></div></div></div><div id="libraryMatchModal" class="app-dialog managed-modal"><div class="dialog-card wide-dialog managed-box"><div class="managed-header"><h2 id="libraryMatchTitle">Bibliothekseintrag suchen</h2></div><div class="installed-toolbar"><input id="libraryMatchQuery" placeholder="Titel oder TitleID suchen ..." oninput="searchLibraryMatch()"><label class="small"><input type="checkbox" id="libraryHideLinked" checked onchange="searchLibraryMatch()"> bereits zugeordnete ausblenden</label></div><div class="managed-scroll"><div id="libraryMatchBody"></div></div><div class="managed-footer"><button class="btn" onclick="libraryMatchModal.classList.remove('show')">Schließen</button></div></div></div><div id="providersModal" class="app-dialog managed-modal"><div class="dialog-card wide-dialog managed-box"><div class="managed-header"><h2>Quellen & Resolver</h2></div><div class="managed-scroll"><div id="providersBody"></div></div><div class="managed-footer"><button class="btn" onclick="enrichX360()">x360db anreichern</button><button class="btn" onclick="refreshUpdates()">PS4 Updates prüfen</button><button class="btn" onclick="providersModal.classList.remove('show')">Schließen</button></div></div></div><div id="sizeAuditModal" class="app-dialog managed-modal"><div class="dialog-card wide-dialog managed-box"><div class="managed-header"><h2>Verdächtige Package-Größen</h2></div><div class="managed-scroll"><div id="sizeAuditBody"></div></div><div class="managed-footer"><button class="btn" onclick="sizeAuditModal.classList.remove('show')">Schließen</button></div></div></div><div id="qualityModal" class="app-dialog managed-modal"><div class="dialog-card wide-dialog managed-box"><div class="managed-header"><h2>Datenqualität</h2></div><div class="managed-scroll"><div id="qualityBody"></div></div><div class="managed-footer footer-end"><button class="btn" onclick="qualityModal.classList.remove('show')">Schließen</button></div></div></div><div id="duplicatesModal" class="app-dialog managed-modal"><div class="dialog-card wide-dialog managed-box"><div class="managed-header"><h2>Mögliche Duplikate</h2><span id="duplicateCount" class="mut small"></span></div><div class="managed-scroll"><div id="duplicatesBody"></div></div><div class="managed-footer"><button class="btn" onclick="openDuplicates(true)">Neu analysieren</button><button class="btn" onclick="duplicatesModal.classList.remove('show')">Schließen</button></div></div></div><div id="newGameModal" class="app-dialog"><div class="dialog-card"><h2>Neues Spiel</h2><div class="editor-grid"><label>Titel<input id="newTitle"></label><label>Plattform<select id="newPlatform"><option>PlayStation 4</option><option>PlayStation 3</option><option>PlayStation 2</option><option>Xbox 360</option><option>Xbox Classic</option></select></label><label>Identifier-Typ<select id="newType"><option>CUSA</option><option>SERIAL</option><option>TITLEID</option><option>OTHER</option></select></label><label>TitleID / Serial<input id="newTid"></label><label>Region<select id="newRegion"><option value="">–</option><option>PAL</option><option>NTSC-U/C</option><option>NTSC-J</option><option>Region Free</option></select></label><label>Format<select id="newFormat"><option>Physisch</option><option>Digital</option><option>PKG-Backup</option><option>ISO</option><option>ROM</option></select></label><label>Edition<input id="newEdition" placeholder="Standard"></label></div><p class="mut small">Nach dem Anlegen kannst du direkt IGDB suchen oder den vollständigen Metadateneditor verwenden.</p><div class="dialog-actions"><button class="btn" onclick="newGameModal.classList.remove('show')">Abbrechen</button><button class="btn blue" onclick="createGame()">Anlegen</button></div></div></div><div id="packageModal" class="app-dialog"><div class="dialog-card"><h2>Backup-Paket bearbeiten</h2><div class="editor-grid"><label>Datei<input id="pkgFilename" disabled></label><label>Typ<select id="pkgCategory"><option>Game</option><option>Patch</option><option>DLC</option></select></label><label>Version<input id="pkgVersion" placeholder="z.B. 1.05"></label><label>Speicherort<input id="pkgLocation"></label><label>Größe [GB]<input id="pkgSize" inputmode="decimal"></label><label>Entscheidung<input id="pkgDecision"></label></div><p class="mut small">DLC hat keine Version. Der lokale PS4-Versionsstand ist die höchste Version aus Game und Patch.</p><div class="dialog-actions"><button class="btn" onclick="packageModal.classList.remove('show')">Abbrechen</button><button class="btn blue" onclick="savePackage()">Speichern</button></div></div></div><div id="authModal" class="app-dialog"><div class="dialog-card"><h2>Verwaltung freischalten</h2><p class="mut">Das Passwort aktiviert alle Verwaltungsfunktionen für diese Browser-Sitzung.</p><input id="adminPassword" type="password" placeholder="Admin-Passwort" style="width:100%"><div class="dialog-actions"><button class="btn" onclick="authModal.classList.remove('show')">Abbrechen</button><button class="btn blue" onclick="loginAdmin()">Freischalten</button></div></div></div><div id="selectionsModal" class="app-dialog managed-modal"><div class="dialog-card wide-dialog managed-box"><div class="managed-header"><h2 id="selectionsTitle">Meine Auswahl</h2><span id="selectionsCount" class="mut small"></span></div><div class="managed-scroll"><div id="selectionsBody"></div></div><div class="managed-footer"><button class="btn" onclick="selectionsModal.classList.remove('show')">Schließen</button></div></div></div><div id="appDialog" class="app-dialog"><div class="dialog-card"><h2 id="appDialogTitle">GameVault</h2><div id="appDialogBody"></div><div class="dialog-actions"><button id="appDialogCancel" class="btn">Abbrechen</button><button id="appDialogOk" class="btn blue">OK</button></div></div></div><script>
let data=[],selected=null,statsData=null,platformImages={},isAdmin=false,selectionIds=new Set(),selectionData=null;
  async function loadAuth(){let r=await fetch('/api/auth/status'),x=await r.json();isAdmin=!!x.admin;document.body.classList.toggle('admin-mode',isAdmin);authState.textContent=isAdmin?'Verwaltungsmodus':'Besuchermodus';authButton.textContent=isAdmin?'Wieder sperren':'Verwaltung freischalten'}
  async function toggleAdmin(){if(isAdmin){await fetch('/api/auth/logout',{method:'POST'});await loadAuth();if(selected)show(selected);return}adminPassword.value='';authModal.classList.add('show');setTimeout(()=>adminPassword.focus(),50)}
  async function loginAdmin(){let r=await fetch('/api/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({password:adminPassword.value})});if(!r.ok){await appMessage('Anmeldung fehlgeschlagen','<pre>'+E(await r.text())+'</pre>');return}authModal.classList.remove('show');await loadAuth();if(selected)show(selected)}
  async function loadSelections(){let r=await fetch('/api/selections');selectionData=await r.json();selectionIds=new Set(selectionData.game_ids||[]);selectionCount.textContent=selectionData.count?'('+selectionData.count+')':''}
  async function toggleSelection(id){let active=selectionIds.has(id),r=await fetch('/api/selections/'+id,{method:active?'DELETE':'POST'});if(!r.ok){await appMessage('Auswahl','<pre>'+E(await r.text())+'</pre>');return}await loadSelections();render();show(id);if(selectionsModal.classList.contains('show'))renderSelections()}
  async function openSelections(){await loadSelections();selectionsModal.classList.add('show');renderSelections()}
  function renderSelections(){let rows=(selectionData?.games||[]),p=selectionData?.platforms||{};selectionsTitle.textContent=selectionData?.name||'Meine Auswahl';selectionsCount.textContent=rows.length+' Spiele';selectionsBody.innerHTML='<div class="selection-summary">'+(Object.entries(p).map(([k,v])=>E(k)+': <b>'+v+'</b>').join(' · ')||'Noch keine Spiele vorgemerkt.')+'</div>'+rows.map(g=>`<div class="dq-row"><b>${E(g.title)}</b> · ${E(g.platform)}<br><span class="mut small">${E(g.title_id||'keine ID')}</span><div class="dialog-actions"><button class="btn" onclick="selectionsModal.classList.remove('show');show(${g.id})">Öffnen</button><button class="btn unmatch-btn" onclick="toggleSelection(${g.id})">Entfernen</button></div></div>`).join('')}

function appMessage(title,html){return new Promise(resolve=>{appDialogTitle.textContent=title;appDialogBody.innerHTML=html;appDialogCancel.style.display='none';appDialogOk.textContent='OK';appDialogOk.onclick=()=>{appDialog.classList.remove('show');resolve(true)};appDialog.classList.add('show')})}
function appConfirm(title,html){return new Promise(resolve=>{appDialogTitle.textContent=title;appDialogBody.innerHTML=html;appDialogCancel.style.display='inline-block';appDialogOk.textContent='Bestätigen';appDialogCancel.onclick=()=>{appDialog.classList.remove('show');resolve(false)};appDialogOk.onclick=()=>{appDialog.classList.remove('show');resolve(true)};appDialog.classList.add('show')})}
function fieldClass(g,key,value,critical=false){let src=(g.metadata_sources||{})[key];if(src==='manual')return 'field-card field-manual';if(!value)return 'field-card '+(critical?'field-critical':'field-optional');return 'field-card field-auto'}

let busyCount=0;function busy(on,text='Abfrage läuft ...'){busyCount=Math.max(0,busyCount+(on?1:-1));if(text)busyText.textContent=text;globalBusy.classList.toggle('show',busyCount>0)}
const PC=p=>p==='PlayStation 4'?'PS4':p==='PlayStation 3'?'PS3':p==='PlayStation 2'?'PS2':p==='PlayStation 1'?'PS1':p==='PlayStation Portable'?'PSP':p==='Xbox 360'?'X360':p==='Xbox Classic'?'XCLASSIC':'OTHER';const E=s=>(s??'').toString().replace(/[&<>\"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));function img(src,cls){if(!src||!src.startsWith('/covers/'))return `<div class='${cls} platform-mark'>GV</div>`;return `<div class='${cls}'><img src='${E(src)}' onerror="this.parentElement.classList.add('platform-mark');this.parentElement.innerHTML='GV'"></div>`}function platformIcon(p){return p==='PlayStation 4'?'PS4':p==='PlayStation 3'?'PS3':p==='PlayStation 2'?'PS2':p==='PlayStation 1'?'PS1':p==='PlayStation Portable'?'PSP':p==='Xbox 360'?'360':p==='Xbox Classic'?'XBOX':'GV'}function platformReview(p){let rows=data.filter(g=>g.platform===p),review=rows.filter(g=>g.metadata_status==='review').length,missing=rows.filter(g=>g.metadata_missing).length;return {review,missing}}function renderPlatformStats(){if(!statsData)return;let order=['PlayStation 4','PlayStation 3','PlayStation 2','PlayStation 1','PlayStation Portable','Xbox 360','Xbox Classic'],platforms=Object.keys(statsData.platforms||{}).sort((a,b)=>{let ai=order.indexOf(a),bi=order.indexOf(b);return (ai<0?99:ai)-(bi<0?99:bi)||a.localeCompare(b)});platformStats.innerHTML=platforms.map(p=>{let st=platformReview(p);return `<div class='stat platform-stat ${PC(p)}' onclick="setPlatformFilter('${E(p).replace(/'/g,"&#39;")}')"><div class='console-visual'>${platformImages[p]?`<img src='${E(platformImages[p])}'>`:platformIcon(p)}</div><span class='mut small'>${E(p)}</span><b>${(statsData.platforms[p]||0).toLocaleString('de-DE')} Spiele</b><div class='platform-status'>${st.missing} Metadaten fehlen · ${st.review} Zuordnung prüfen</div></div>`}).join('');backupStats.innerHTML=`Gesamt <b>${statsData.games.toLocaleString('de-DE')} Spiele</b> · Backup-Pakete <b>${statsData.packages.toLocaleString('de-DE')}</b> · Backup-Größe <b>${statsData.size_gb.toLocaleString('de-DE')} GB</b>`}function setPlatformFilter(p){pf.value=p;render()}async function openPlatformImages(){platformImagesModal.classList.add('show');await renderPlatformImages()}async function renderPlatformImages(){let ps=[...new Set(data.map(g=>g.platform))].sort();platformImagesBody.innerHTML=ps.map((p,i)=>`<div class="dq-row"><b>${E(p)}</b><br>${platformImages[p]?`<img src="${E(platformImages[p])}" style="width:140px;height:90px;object-fit:contain;background:#111827;border-radius:10px;margin:8px 0"><br>`:''}<input type="file" id="pimg${i}" accept="image/jpeg,image/png,image/webp"> <button class="btn" onclick="uploadPlatformImage('${E(p).replace(/'/g,"&#39;")}',${i})">Bild speichern</button></div>`).join('')}async function uploadPlatformImage(p,i){let f=document.getElementById('pimg'+i).files[0];if(!f)return;let fd=new FormData();fd.append('file',f);busy(true,'Plattformbild wird gespeichert ...');try{let r=await fetch('/api/platform-images/'+encodeURIComponent(p),{method:'POST',body:fd});if(!r.ok)return appMessage('Bildfehler','<pre>'+E(await r.text())+'</pre>');platformImages=await fetch('/api/platform-images').then(r=>r.json());renderPlatformStats();renderPlatformImages()}finally{busy(false)}}
async function load(){await Promise.all([loadAuth(),loadSelections()]);data=await fetch('/api/games').then(r=>r.json());statsData=await fetch('/api/stats').then(r=>r.json());platformImages=await fetch('/api/platform-images').then(r=>r.json());pf.innerHTML='<option value="">Alle Plattformen</option>'+Object.keys(statsData.platforms).sort().map(x=>`<option>${E(x)}</option>`).join('');renderPlatformStats();render()}function render(){let term=q.value.toLowerCase(),pl=pf.value,missing=mf.value==='missing';let review=mf.value==='review',cover=mf.value==='cover',noid=mf.value==='id',lmp=mf.value==='localmp',lcoop=mf.value==='localcoop',omp=mf.value==='onlinemp',upd=mf.value==='updates',ps3i=mf.value==='ps3installed',ps3n=mf.value==='ps3notinstalled',x360i=mf.value==='x360installed',x360n=mf.value==='x360notinstalled',xci=mf.value==='xclassicinstalled',xcn=mf.value==='xclassicnotinstalled';let a=data.filter(g=>(!pl||g.platform===pl)&&(!missing||g.metadata_missing)&&(!review||g.metadata_status==='review')&&(!cover||!g.cover_local)&&(!noid||!g.title_id)&&(!lmp||g.local_multiplayer)&&(!lcoop||g.local_coop)&&(!omp||g.online_multiplayer)&&(!upd||g.update_status==='update_available')&&(!ps3i||g.installed_on.length>0)&&(!ps3n||g.platform!=='PlayStation 3'||g.installed_on.length===0)&&(!x360i||g.platform==='Xbox 360'&&g.installed_on.some(x=>!['DLC','Title Update'].includes(x.category)))&&(!x360n||g.platform!=='Xbox 360'||!g.installed_on.some(x=>!['DLC','Title Update'].includes(x.category)))&&(!xci||g.platform==='Xbox Classic'&&g.installed_on.some(x=>x.category==='Xbox Classic'))&&(!xcn||g.platform!=='Xbox Classic'||!g.installed_on.some(x=>x.category==='Xbox Classic'))&&(!term||(g.title+' '+(g.title_id||'')).toLowerCase().includes(term)));filteredCount.textContent=a.length===data.length?`${a.length.toLocaleString('de-DE')} Spiele`:`${a.length.toLocaleString('de-DE')} / ${data.length.toLocaleString('de-DE')} Spiele`;list.innerHTML=a.map(g=>`<div class='card ${PC(g.platform)} ${selected===g.id?'on':''}' onclick='show(${g.id})'>${img(g.cover_source,'cover')}<div class='meta'><span class='tag'>${E(g.platform)}</span>${g.metadata_missing?` <span class='warning small'>Metadaten fehlen</span>`:''}${g.metadata_status==='review'?` <span class='warning small'>Zuordnung prüfen</span>`:''}${g.update_status==='update_available'?` <span class='warning small'>Update verfügbar</span>`:''}${g.installed_on.length?` <span class='status-ok small'>${E([...new Set(g.installed_on.map(x=>x.platform))].join(' / '))} verfügbar</span>`:''}<div class='title'>${E(g.title)} ${selectionIds.has(g.id)?'<span title="Vorgemerkt">💜</span>':''}</div><div class='small'>${E(g.title_id||'Keine TitleID')}</div><div class='mut small'>${E(g.publisher||'')}${g.packages.length?' · '+g.packages.length+' Pakete':''}</div></div></div>`).join('')}function show(id){selected=id;let g=data.find(x=>x.id===id);render();detail.scrollTop=0;detail.className='detail '+PC(g.platform);let pk=g.packages.map(p=>`<div class='pkg'><span><b>${E(p.name||p.filename)}</b><br><span class='mut small'>${E(p.filename)}</span></span><span>${E(p.category||'–')}</span><span>${E(p.version||'–')}</span><span>${E(p.location||'–')}</span><span>${p.size_gb==null?'–':p.size_gb.toLocaleString('de-DE')+' GB'}</span><span><button class='btn admin-only' onclick='event.stopPropagation();openPackageEditor(${g.id},${p.id})'>Bearbeiten</button></span></div>`).join('');detail.innerHTML=`<div class='hero'>${img(g.cover_source,'heroCover')}<div><span class='tag'>${E(g.platform)}</span>${g.metadata_missing?` <span class='warning'>Metadaten fehlen</span>`:''}<h1>${E(g.title)}</h1><div class='mut'>${E(g.publisher||'Unbekannter Publisher')}${g.developer?' · '+E(g.developer):''}</div></div><div class='value'><span class='mut small'>Aktueller Wert</span><br><b>${E(g.current_value||'–')}</b></div></div><div class='info'><span class='mut small'>Metadatenqualität</span><br><b>${g.metadata_quality.score} % · ${g.metadata_quality.status==='complete'?'Vollständig':g.metadata_quality.status==='partial'?'Unvollständig':'Kritisch'}</b><div class='qualitybar'><span style='width:${g.metadata_quality.score}%'></span></div></div><div class='infos'><div class='info ${fieldClass(g,'title_id',g.title_id,true)}'><span class='mut small'>TitleID</span><br><b>${E(g.title_id||'–')}</b></div><div class='info ${fieldClass(g,'genres',g.genres,true)}'><span class='mut small'>Genre</span><br><b>${E(g.genres||'–')}</b></div><div class='info ${fieldClass(g,'release_date',g.release_date,false)}'><span class='mut small'>Release</span><br><b>${E(g.release_date||'–')}</b></div><div class='info'><span class='mut small'>Sammlung</span><br><b>${E(g.collection_status||'–')}</b></div><div class='info'><span class='mut small'>Vollständigkeit</span><br><b>${E(g.completeness||'–')}</b></div><div class='info'><span class='mut small'>Durchgespielt</span><br><b>${g.completed?'Ja':'Nein'}</b></div><div class='info ${fieldClass(g,'developer',g.developer,false)}'><span class='mut small'>Entwickler</span><br><b>${E(g.developer||'–')}</b></div><div class='info'><span class='mut small'>Backups</span><br><b>${g.packages.length}</b></div>${g.platform==='PlayStation 4'?`<div class='info'><span class='mut small'>Lokaler Versionsstand</span><br><b>${E(g.local_patch_version||'–')}</b></div><div class='info'><span class='mut small'>Online aktuell</span><br><b>${E(g.remote_latest_version||'–')}</b></div><div class='info ${g.update_status==='update_available'?'field-critical':g.update_status==='current'?'field-auto':'field-optional'}'><span class='mut small'>Update-Status</span><br><b>${g.update_status==='update_available'?'Update verfügbar':g.update_status==='current'?'Aktuell':'Unbekannt'}</b></div>`:''}</div>${g.description?`<h3>Beschreibung</h3><p class='desc'>${E(g.description.replace(/<[^>]*>/g,' ')).slice(0,4000)}</p>`:''}${g.metadata_status==='review'?`<h3>IGDB-Zuordnung prüfen</h3><p class='warning'>Vorschlag: ${E(g.candidate_title||'')} (${Math.round((g.metadata_confidence||0)*100)} %)</p><button class='btn' onclick='openIgdb(${g.id})'>Treffer anzeigen</button>`:''}<div class='infos'><div class='info ${fieldClass(g,'game_modes',g.game_modes,false)}'><span class='mut small'>Game Modes</span><br><b>${E(g.game_modes||'–')}</b></div><div class='info ${fieldClass(g,'perspectives',g.perspectives,false)}'><span class='mut small'>Perspektive</span><br><b>${E(g.perspectives||'–')}</b></div><div class='info ${fieldClass(g,'themes',g.themes,false)}'><span class='mut small'>Themes</span><br><b>${E(g.themes||'–')}</b></div><div class='info ${fieldClass(g,'franchises',g.franchises,false)}'><span class='mut small'>Franchise</span><br><b>${E(g.franchises||'–')}</b></div><div class='info ${fieldClass(g,'engines',g.engines,false)}'><span class='mut small'>Engine</span><br><b>${E(g.engines||'–')}</b></div><div class='info'><span class='mut small'>Local Multiplayer</span><br><b>${g.local_multiplayer?'Ja':'Nein'}</b></div><div class='info'><span class='mut small'>Local Co-op</span><br><b>${g.local_coop?'Ja':'Nein'}</b></div><div class='info'><span class='mut small'>Online Multiplayer</span><br><b>${g.online_multiplayer?'Ja':'Nein'}</b></div></div><div class='info' style='margin-top:12px'><span class='mut small'>Datenquellen</span><br><span class='small'>${Object.entries(g.metadata_sources||{}).map(([k,v])=>E(k)+': '+E(v)).join(' · ')||'noch nicht zugeordnet'}</span></div>${g.pricecharting_url?`<div class='info' style='margin-top:8px'><span class='mut small'>PriceCharting</span><br><a href='${E(g.pricecharting_url)}' target='_blank' rel='noopener' style='color:#60a5fa'>Preis-/Spieleintrag öffnen</a></div>`:''}<div class='info' style='margin-top:8px'><span class='mut small'>Ausgabe</span><br><b>${E([g.region,g.media_format,g.edition,g.storefront].filter(Boolean).join(' · ')||'–')}</b>${g.tags.length?`<br><span class='small'>Tags: ${E(g.tags.join(', '))}</span>`:''}</div><div id='consoleContentDetail'></div>${g.installed_on.length?`<h3>Installationen</h3>${g.installed_on.map(x=>`<div class='info field-auto'><b>${E(x.console_name)}</b> · <span class='status-ok'>${E(x.category||'verfügbar')}</span><br><span class='small'><b>Installierter/verfügbarer Stand: ${E(x.version||'–')}</b> · ${E(x.storage||'–')}<br>Größe: <b>${E(x.installed_size||'nicht berechnet')}</b>${x.size_checked_at?` · geprüft ${E(x.size_checked_at)}`:''}<br>${E(x.path)}${x.title_updates?`<br>${x.title_updates} Title Update${x.title_updates===1?'':'s'}`:''}${x.dlc_count?` · ${x.dlc_count} DLC`:''}<br>Quelle ${E(x.source)} · Scan ${E(x.last_seen_at)}</span></div>`).join('')}`:''}<div class='editor-actions'><button class='btn selection-btn ${selectionIds.has(g.id)?'active':''}' onclick='toggleSelection(${g.id})'>${selectionIds.has(g.id)?'✓ Vorgemerkt':'Für meine Konsole vormerken'}</button><span class='admin-only'><button class='btn blue' onclick='openEditor(${g.id})'>Metadaten bearbeiten</button><button class='btn' onclick='openIgdb(${g.id})'>IGDB suchen</button><button class='btn' onclick='resolveAll(${g.id})'>Alle Resolver ausführen</button><button class='btn unmatch-btn' onclick='deleteGame(${g.id})'>Spiel löschen</button></span></div><h3>Backup-Pakete</h3><div class='pkghead'><span>Datei</span><span>Typ</span><span>Version</span><span>Speicherort</span><span>Größe</span><span></span></div>${pk||'<p class="mut">Keine Backup-Pakete zugeordnet.</p>'}`;loadGameConsoleContent(g.id);}function modal(v){document.getElementById('modal').classList.toggle('show',v)}async function upload(i,u){let f=document.getElementById(i).files[0];if(!f)return;let d=new FormData();d.append('file',f);msg.textContent='Import läuft ...';let r=await fetch(u,{method:'POST',body:d});msg.textContent=r.ok?'OK '+JSON.stringify(await r.json()):'Fehler: '+await r.text();if(r.ok)await load()}load();
async function covers(){let b=document.querySelector('button[onclick=\"covers()\"]');if(!await appConfirm('Cover aktualisieren','Cover für PS4, PS3 und PS2 über die Provider-Kaskade suchen?'))return;b.disabled=true;b.textContent='Cover-Suche läuft ...';try{let r=await fetch('/api/covers/refresh',{method:'POST'});let x=r.ok?await r.json():await r.text();await appMessage('Cover Ergebnis','<pre>'+E(typeof x==='string'?x:JSON.stringify(x,null,2))+'</pre>');if(r.ok)await load()}finally{b.disabled=false;b.textContent='Cover aktualisieren'}}
async function igdbRefresh(){if(!await appConfirm('IGDB aktualisieren','Alle Spiele wie mit <b>ID / IGDB auflösen</b> aktualisieren? Manuell bearbeitete Felder bleiben geschützt.'))return;busy(true,'IGDB aktualisiert die gesamte Bibliothek ...');try{let r=await fetch('/api/metadata/igdb/refresh',{method:'POST'});let result=r.ok?await r.json():await r.text();await appMessage('IGDB Ergebnis','<pre>'+E(typeof result==='string'?result:JSON.stringify(result,null,2))+'</pre>');if(r.ok){await load();if(selected)show(selected)}}finally{busy(false)}}
async function showCandidates(id){return openIgdb(id)}
let activeGame=null;
function openEditor(id){let g=data.find(x=>x.id===id);activeGame=id;edTitle.value=g.title||'';edPlatform.value=g.platform||'';edType.value=g.identifier_type||(g.platform==='PlayStation 4'?'CUSA':['Xbox 360','Xbox Classic'].includes(g.platform)?'TITLEID':'SERIAL');edTid.value=g.title_id||'';edIgdb.value=g.metadata_provider==='IGDB'?(g.metadata_provider_id||''):'';edPublisher.value=g.publisher||'';edDeveloper.value=g.developer||'';edGenres.value=g.genres||'';edRelease.value=g.release_date||'';edValue.value=g.current_value||'';edModes.value=g.game_modes||'';edPerspective.value=g.perspectives||'';edThemes.value=g.themes||'';edFranchise.value=g.franchises||'';edEngine.value=g.engines||'';edCollection.value=g.collection_status||'';edCompleteness.value=g.completeness||'';edRegion.value=g.region||'';edFormat.value=g.media_format||'';edEdition.value=g.edition||'';edStorefront.value=g.storefront||'';edTags.value=(g.tags||[]).join(', ');edNotes.value=g.notes||'';edPriceUrl.value=g.pricecharting_url||'';edCoverUrl.value='';edDescription.value=g.description||'';editorModal.classList.add('show');document.body.classList.add('editor-open');setTimeout(()=>{let sc=editorModal.querySelector('.editor-scroll');if(sc)sc.scrollTop=0},0)}
function closeEditor(){editorModal.classList.remove('show');document.body.classList.remove('editor-open')}
async function saveMetadata(){saveBtn.disabled=true;saveBtn.innerHTML='<span class="spinner"></span> Speichern';let P={title:edTitle.value,title_id:edTid.value,identifier_type:edType.value,publisher:edPublisher.value,developer:edDeveloper.value,genres:edGenres.value,release_date:edRelease.value,current_value:edValue.value,game_modes:edModes.value,perspectives:edPerspective.value,themes:edThemes.value,franchises:edFranchise.value,engines:edEngine.value,collection_status:edCollection.value,completeness:edCompleteness.value,region:edRegion.value,media_format:edFormat.value,edition:edEdition.value,storefront:edStorefront.value,tags:edTags.value,notes:edNotes.value,pricecharting_url:edPriceUrl.value,description:edDescription.value};try{let r=await fetch(`/api/games/${activeGame}/metadata`,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(P)});if(!r.ok){await appMessage('Fehler','<pre>'+E(await r.text())+'</pre>');return}let saved=await r.json();if(edIgdb.value){r=await fetch(`/api/games/${activeGame}/igdb-direct/${edIgdb.value}`,{method:'POST'});if(!r.ok){await appMessage('IGDB Fehler','<pre>'+E(await r.text())+'</pre>')}}if(edCoverUrl.value.trim()){r=await fetch(`/api/games/${activeGame}/cover-from-url`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url:edCoverUrl.value.trim()})});if(!r.ok){await appMessage('Cover Fehler','<pre>'+E(await r.text())+'</pre>')}}closeEditor();await load();show(activeGame)}finally{saveBtn.disabled=false;saveBtn.textContent='Speichern'}}
async function openIgdb(id){busy(true,'IGDB-Suche läuft ...');try{activeGame=id;igdbModal.classList.add('show');let isc=igdbModal.querySelector('.managed-scroll');if(isc)isc.scrollTop=0;igdbResults.innerHTML='';igdbState.innerHTML='<span class="spinner"></span> IGDB wird durchsucht ...';let r=await fetch(`/api/games/${id}/igdb-candidates`);if(!r.ok){igdbState.textContent=await r.text();return}let rows=await r.json();igdbState.textContent=rows.length+' Treffer';igdbResults.innerHTML=rows.map(x=>`<div class="candidate">${x.cover_url?`<img src="${E(x.cover_url)}">`:'<div></div>'}<div><b>${E(x.title)}</b><br><span class="mut">IGDB ${x.igdb_id} · ${Math.round(x.confidence*100)} %</span></div><button class="btn" onclick="acceptId(${x.igdb_id})">Übernehmen</button></div>`).join('')}
finally{busy(false)}}function closeIgdb(){igdbModal.classList.remove('show')}
async function acceptId(i){busy(true,'IGDB-Daten werden übernommen ...');try{igdbState.innerHTML='<span class="spinner"></span> Übernahme ...';let r=await fetch(`/api/games/${activeGame}/igdb-direct/${i}`,{method:'POST'});if(!r.ok){igdbState.textContent=await r.text();return}let result=await r.json();if(result.changed)await appMessage('IGDB übernommen','Aktualisiert: '+E(result.changed.join(', ')||'keine Änderungen'));closeIgdb();await load();show(activeGame)}
finally{busy(false)}}async function directLoad(){if(!/^\d+$/.test(directId.value.trim()))return await appMessage('IGDB','Numerische IGDB-ID eingeben');await acceptId(directId.value.trim())}
async function resolveTrace(id){busy(true,'ID / IGDB wird aufgelöst ...');try{activeGame=id;traceModal.classList.add('show');traceRows.innerHTML='';traceState.innerHTML='<span class="spinner"></span> Suche läuft ...';let r=await fetch(`/api/games/${id}/resolve-trace`,{method:'POST'});if(!r.ok){traceState.textContent=await r.text();return}let x=await r.json();traceState.textContent='Fertig';traceRows.innerHTML=x.trace.map(t=>`<p><b>${t.ok?'✓':'✗'} ${E(t.step)}</b><br><span class="mut">${E(t.detail)}</span></p>`).join('');await load();show(id)}finally{busy(false)}}
async function localizeCovers(){if(!await appConfirm('Cover lokal speichern','Alle Cover lokal speichern? Alte Game-Collector-Pfade werden verworfen und über Provider/IGDB neu gesucht.'))return;busy(true,'Cover werden lokalisiert ...');try{let r=await fetch('/api/covers/localize',{method:'POST'});let x=r.ok?await r.json():await r.text();await appMessage('Cover Ergebnis','<pre>'+E(typeof x==='string'?x:JSON.stringify(x,null,2))+'</pre>');if(r.ok)await load()}finally{busy(false)}}
async function openQuality(){qualityModal.classList.add('show');let qsc=qualityModal.querySelector('.managed-scroll');if(qsc)qsc.scrollTop=0;qualityBody.innerHTML='<span class="spinner"></span> Datenqualität wird geladen ...';let r=await fetch('/api/data-quality');if(!r.ok){qualityBody.textContent=await r.text();return}let rows=await r.json();qualityBody.innerHTML=rows.length?rows.map(x=>`<div class="dq-row" onclick="qualityModal.classList.remove('show');show(${x.id})"><b>${E(x.title)}</b> · ${E(x.platform)} <span class="score-pill">${x.quality.score}%</span><br><span class="small">${x.quality.missing_critical.length?'Kritisch: '+E(x.quality.missing_critical.join(', ')):''}${x.quality.missing_optional.length?' · Optional: '+E(x.quality.missing_optional.join(', ')):''}${x.without_id?' · ID fehlt':''}${x.without_cover?' · Cover fehlt':''}${x.review?' · Review':''}</span></div>`).join(''):'<p>Keine Problemfälle.</p>'}
async function openDuplicates(force=false){duplicatesModal.classList.add('show');if(!force&&duplicatesBody.dataset.loaded==='1')return;duplicatesBody.innerHTML='<span class="spinner"></span> Duplikate werden analysiert ...';let r=await fetch('/api/duplicates');if(!r.ok){duplicatesBody.textContent=await r.text();return}let rows=await r.json();duplicatesBody.dataset.loaded='1';duplicateCount.textContent=rows.length+' Kandidaten';duplicatesBody.innerHTML=rows.length?rows.map((x,i)=>`<div class="dup-row" id="dup-${i}"><div><span class="score-pill">${Math.round(x.score*100)} %</span> ${E((x.reasons||[]).join(' · '))}</div><div class="dup-grid"><div><b>Behalten</b><br>${E(x.keep.title)}<br><span class="small">${E(x.keep.title_id||'keine ID')} · ${x.keep.packages.length} Pakete ${x.keep.current_value?'· Wert '+E(x.keep.current_value):''}</span></div><div><b>Vergleichen</b><br>${E(x.merge.title)}<br><span class="small">${E(x.merge.title_id||'keine ID')} · ${x.merge.packages.length} Pakete</span></div></div>${x.conflicts.length?`<div class="conflict">Konflikte: ${E(x.conflicts.map(c=>c.field).join(', '))}</div>`:''}<div class="dup-details" id="dupdetail-${i}">${duplicateDetails(x.keep,x.merge)}</div><div class="dup-actions"><button class="btn" onclick="toggleDuplicateDetails(${i},this)">Details vergleichen</button><button class="btn no-duplicate" onclick="markNotDuplicate(${x.keep.id},${x.merge.id},${i})">Kein Duplikat</button><button class="btn blue" onclick="mergeDuplicate(${x.keep.id},${x.merge.id},${i})">Zusammenführen</button></div></div>`).join(''):'<p>Keine möglichen Duplikate gefunden.</p>'}
function duplicateDetails(a,b){let rows=[['Cover',img(a.cover_source,'mini-cover'),img(b.cover_source,'mini-cover')],['Titel',E(a.title),E(b.title)],['Plattform',E(a.platform),E(b.platform)],['TitleID / Serial',E(a.title_id||'–'),E(b.title_id||'–')],['IGDB-ID',E(a.metadata_provider_id||'–'),E(b.metadata_provider_id||'–')],['Release',E(a.release_date||'–'),E(b.release_date||'–')],['Publisher',E(a.publisher||'–'),E(b.publisher||'–')],['Developer',E(a.developer||'–'),E(b.developer||'–')],['Genre',E(a.genres||'–'),E(b.genres||'–')],['Franchise',E(a.franchises||'–'),E(b.franchises||'–')],['Wert',E(a.current_value||'–'),E(b.current_value||'–')],['Durchgespielt',a.completed?'Ja':'Nein',b.completed?'Ja':'Nein'],['Packages',String(a.packages.length),String(b.packages.length)]];return `<table class="compare-table"><thead><tr><th>Feld</th><th>Behalten</th><th>Vergleichen</th></tr></thead><tbody>${rows.map(r=>`<tr><th>${r[0]}</th><td>${r[1]}</td><td>${r[2]}</td></tr>`).join('')}</tbody></table>`}
function toggleDuplicateDetails(row,button){let el=document.getElementById('dupdetail-'+row);let show=!el.classList.contains('show');el.classList.toggle('show',show);button.textContent=show?'Details schließen':'Details vergleichen'}
async function markNotDuplicate(a,b,row){if(!await appConfirm('Kein Duplikat','Dieses Paar dauerhaft aus der Duplikatsuche ausschließen?'))return;busy(true,'Entscheidung wird gespeichert ...');try{let r=await fetch(`/api/duplicates/not-duplicate/${a}/${b}`,{method:'POST'});if(!r.ok){await appMessage('Fehler','<pre>'+E(await r.text())+'</pre>');return}removeDuplicateRow(row,'Als kein Duplikat gespeichert.')}finally{busy(false)}}
function removeDuplicateRow(row,emptyText){let el=document.getElementById('dup-'+row);if(el)el.remove();let left=duplicatesBody.querySelectorAll('.dup-row').length;duplicateCount.textContent=left+' Kandidaten';if(left===0)duplicatesBody.innerHTML=`<p>${emptyText||'Keine weiteren Kandidaten in dieser Analyse.'}</p>`}
async function mergeDuplicate(keepId,mergeId,row){if(!await appConfirm('Duplikate zusammenführen','Packages und fehlende Felder werden auf den bevorzugten Datensatz übertragen. Der zweite Datensatz wird danach gelöscht.'))return;busy(true,'Duplikate werden zusammengeführt ...');try{let r=await fetch(`/api/duplicates/merge/${keepId}/${mergeId}`,{method:'POST'});let x=r.ok?await r.json():await r.text();if(!r.ok){await appMessage('Merge-Fehler','<pre>'+E(x)+'</pre>');return}await appMessage('Zusammengeführt',`Packages verschoben: ${x.packages_moved}<br>Übernommene Felder: ${E((x.fields_inherited||[]).join(', ')||'keine')}`);removeDuplicateRow(row,'Keine weiteren Kandidaten in dieser Analyse. Mit <b>Neu analysieren</b> erneut prüfen.');await load()}finally{busy(false)}}
function openNewGame(){newTitle.value='';newTid.value='';newPlatform.value='PlayStation 4';newType.value='CUSA';newGameModal.classList.add('show')}
async function createGame(){let title=newTitle.value.trim();if(!title)return await appMessage('Neues Spiel','Titel ist erforderlich.');busy(true,'Spiel wird angelegt ...');try{let r=await fetch('/api/games',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({title,platform:newPlatform.value,title_id:newTid.value.trim(),identifier_type:newType.value,region:newRegion.value,media_format:newFormat.value,edition:newEdition.value})});if(!r.ok){await appMessage('Fehler','<pre>'+E(await r.text())+'</pre>');return}let g=await r.json();newGameModal.classList.remove('show');await load();show(g.id);await appMessage('Spiel angelegt','Das Spiel wurde angelegt. Du kannst jetzt IGDB suchen oder Metadaten bearbeiten.')}finally{busy(false)}}
async function refreshUpdates(){if(!await appConfirm('PS4 Updates','Online-Updatestände für alle PS4-Spiele prüfen und mit deinen archivierten Patch-Paketen vergleichen?'))return;busy(true,'PS4 Updatestände werden geprüft ...');try{let r=await fetch('/api/updates/ps4/refresh',{method:'POST'});let x=r.ok?await r.json():await r.text();await appMessage('PS4 Updateprüfung','<pre>'+E(typeof x==='string'?x:JSON.stringify(x,null,2))+'</pre>');if(r.ok){await load();if(selected)show(selected)}}finally{busy(false)}}
async function openProviders(){providersModal.classList.add('show');providersBody.innerHTML='<span class="spinner"></span> Quellen werden geprüft ...';let r=await fetch('/api/providers/status');if(!r.ok){providersBody.textContent=await r.text();return}let x=await r.json();let cards=[['IGDB',x.igdb.configured,'Konfiguriert: '+(x.igdb.configured?'Ja':'Nein')],['PS4 Catalog',x.ps4_catalog.ok,(x.ps4_catalog.entries||0)+' Einträge'],['ORBISPatches',x.orbispatches.ok,x.orbispatches.ok?'Erreichbar':E(x.orbispatches.error||'Fehler')],['PS4 Updates',x.ps4_updates.ok,(x.ps4_updates.entries||0)+' Einträge'],['Lokale Cover',true,`${x.covers.local} lokal · ${x.covers.missing} fehlen`],['Bibliothek',true,`${x.library.games} Spiele · ${x.library.igdb_linked} IGDB · ${x.library.updates_available} Updates`]];providersBody.innerHTML=`<div class="provider-grid">${cards.map(c=>`<div class="provider-card ${c[1]?'provider-ok':'provider-bad'}"><b>${E(c[0])}</b><br><span class="mut">${c[2]}</span></div>`).join('')}</div>`}
async function resolveAll(id){busy(true,'Alle Resolver werden ausgeführt ...');try{let r=await fetch(`/api/games/${id}/resolve-all`,{method:'POST'});let x=r.ok?await r.json():await r.text();if(!r.ok){await appMessage('Resolver-Fehler','<pre>'+E(x)+'</pre>');return}await appMessage('Resolver-Ergebnis',x.trace.map(t=>`${t.ok?'✓':'✗'} <b>${E(t.provider)}</b>: ${E(t.detail)}`).join('<br>'));await load();show(id)}finally{busy(false)}}
async function showPackageSchema(){let r=await fetch('/api/import/packages/schema');let x=r.ok?await r.json():await r.text();await appMessage('XLSX Package-Import','<pre>'+E(typeof x==='string'?x:JSON.stringify(x,null,2))+'</pre>')}
let packageGameId=null,packageId=null;function openPackageEditor(gameId,id){let g=data.find(x=>x.id===gameId),p=g?.packages.find(x=>x.id===id);if(!p)return;packageGameId=gameId;packageId=id;pkgFilename.value=p.filename||'';pkgCategory.value=p.category||'Game';pkgVersion.value=p.version||'';pkgVersion.disabled=pkgCategory.value==='DLC';pkgLocation.value=p.location||'';pkgSize.value=p.size_gb??'';pkgDecision.value=p.decision||'';pkgCategory.onchange=()=>{pkgVersion.disabled=pkgCategory.value==='DLC';if(pkgVersion.disabled)pkgVersion.value=''};packageModal.classList.add('show')}async function savePackage(){busy(true,'Package wird gespeichert ...');try{let r=await fetch(`/api/packages/${packageId}`,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({category:pkgCategory.value,version:pkgVersion.value,location:pkgLocation.value,size_gb:pkgSize.value,decision:pkgDecision.value})});if(!r.ok){await appMessage('Package-Fehler','<pre>'+E(await r.text())+'</pre>');return}packageModal.classList.remove('show');await load();show(packageGameId);await appMessage('Gespeichert','Package wurde aktualisiert. Lokaler Versionsstand und Update-Status wurden neu berechnet.')}finally{busy(false)}}
let currentConsoleId=null,currentConsole=null;
async function openConsoles(){consolesModal.classList.add('show');await loadConsoles()}
let currentConsoleRows=[];async function loadConsoles(){consolesBody.innerHTML='<span class="spinner"></span> Konsolen werden geladen ...';let r=await fetch('/api/consoles');if(!r.ok){consolesBody.textContent=await r.text();return}let rows=await r.json();currentConsoleRows=rows;consolesBody.innerHTML=rows.length?rows.map(c=>`<div class="console-card"><div class="console-image">${c.image_source?`<img src="${E(c.image_source)}">`:E(c.platform)}</div><b>${E(c.name)}</b> · ${E(c.platform)}<br><span class="mut">${E(c.host)}:${c.ftp_port} · ${c.provider_type==='xbox360_aurora'?'Aurora/NOVA':c.provider_type==='xboxclassic_xbmc4gamers'?'XBMC4Gamers DB':c.provider_type==='ps4_goldhen'?'GoldHEN app.db + addcont.db':`webMAN ${c.webman_url?'konfiguriert':'optional'}`}</span><br><span class="small ${c.last_scan_status==='ok'?'status-ok':c.last_scan_status==='error'?'status-error':''}">${c.last_scan_at?'Letzter Scan '+E(c.last_scan_at):'Noch nicht gescannt'} · ${c.installed_count} Inhalte · ${c.matched_count} zugeordnet${c.installed_size?`<br><b>Installierte Gesamtgröße: ${E(c.installed_size)}</b> · ${c.sizes_checked} Größen`:''}${Object.keys(c.content_counts||{}).length?'<br>'+Object.entries(c.content_counts).map(([k,v])=>E(k)+': '+v).join(' · '):''}</span><div class="console-actions"><button class="btn" onclick="editConsole(${c.id})">Bearbeiten</button><button class="btn" onclick="testConsole(${c.id})">Verbindung testen</button><button class="btn blue" onclick="scanConsole(${c.id})">Inventar scannen</button>${['xbox360_aurora','ps3'].includes(c.provider_type||'ps3')?`<button class="btn" onclick="scanConsoleSizes(${c.id})">Größen aktualisieren</button>`:''}<button class="btn" onclick="showInstalled(${c.id},'${E(c.name)}')">Inhalte</button><button class="btn" onclick="bulkImportConsole(${c.id},'${E(c.name)}')">Unbekannte übernehmen</button><button class="btn" onclick="deleteConsole(${c.id})">Löschen</button></div></div>`).join(''):'<p>Noch keine Konsolen. Lege eine PS3 oder Xbox 360 an.</p>'}
function editConsole(id){conImage.value='';let c=currentConsoleRows.find(x=>x.id===id);if(!c)return;currentConsoleId=id;currentConsole=c;conProvider.value=c.provider_type||'ps3';conProvider.disabled=true;conName.value=c.name||'';conHost.value=c.host||'';conPort.value=c.ftp_port||21;conUser.value=c.ftp_username||'';conPass.value='';conWebman.value=c.webman_url||'';conNovaUrl.value=c.nova_url||'';conNovaUser.value=c.nova_username||'';conNovaPass.value='';conDbPath.value=c.database_path||'/E/XBMC4Gamers/system/UserData/profiles/Dominic/Database/MyPrograms6.db';consoleProviderChanged(false);consoleEditorModal.classList.add('show')}
function openConsoleEditor(){conImage.value='';currentConsoleId=null;currentConsole=null;conProvider.disabled=false;conProvider.value='ps3';conName.value='PS3 Wohnzimmer';conHost.value='';conPort.value='21';conUser.value='anonymous';conPass.value='';conWebman.value='';conNovaUrl.value='';conNovaUser.value='xboxhttp';conNovaPass.value='xboxhttp';conDbPath.value='/E/XBMC4Gamers/system/UserData/profiles/Dominic/Database/MyPrograms6.db';consoleProviderChanged();consoleEditorModal.classList.add('show')}function consoleProviderChanged(reset=true){let xbox=conProvider.value==='xbox360_aurora',classic=conProvider.value==='xboxclassic_xbmc4gamers',ps4=conProvider.value==='ps4_goldhen';webmanLabel.style.display=(!xbox&&!classic&&!ps4)?'flex':'none';novaUrlLabel.style.display=xbox?'flex':'none';novaUserLabel.style.display=xbox?'flex':'none';novaPassLabel.style.display=xbox?'flex':'none';dbPathLabel.style.display=(classic||ps4)?'flex':'none';if(reset&&xbox){conName.value='Xbox 360 Spielzimmer';conPort.value='21';conUser.value='xboxftp';conPass.value='xboxftp';conDbPath.value=''}else if(reset&&classic){conName.value='Xbox Classic';conPort.value='21';conUser.value='xbox';conPass.value='xbox';conDbPath.value='/E/XBMC4Gamers/system/UserData/profiles/Dominic/Database/MyPrograms6.db'}else if(reset&&ps4){conName.value='PS4 Spielzimmer';conPort.value='2121';conUser.value='anonymous';conPass.value='';conDbPath.value='/system_data/priv/mms/app.db'}else if(reset){conName.value='PS3 Wohnzimmer';conPort.value='21';conUser.value='anonymous';conPass.value='';conDbPath.value=''}}
async function saveConsole(){busy(true,'Konsole wird gespeichert ...');try{let payload={provider_type:conProvider.value,name:conName.value,host:conHost.value,ftp_port:conPort.value,ftp_username:conUser.value,webman_url:conWebman.value,nova_url:conNovaUrl.value,nova_username:conNovaUser.value,database_path:conDbPath.value};if(conPass.value)payload.ftp_password=conPass.value;if(conNovaPass.value)payload.nova_password=conNovaPass.value;let r=await fetch(currentConsoleId?`/api/consoles/${currentConsoleId}`:'/api/consoles',{method:currentConsoleId?'PUT':'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});if(!r.ok){await appMessage('Fehler','<pre>'+E(await r.text())+'</pre>');return}let saved=await r.json();if(conImage.files[0]){let fd=new FormData();fd.append('file',conImage.files[0]);let ir=await fetch(`/api/consoles/${saved.id}/image`,{method:'POST',body:fd});if(!ir.ok)await appMessage('Bildfehler','<pre>'+E(await ir.text())+'</pre>')}conImage.value='';consoleEditorModal.classList.remove('show');await loadConsoles()}finally{busy(false)}}
async function testConsole(id){busy(true,'Konsolenverbindungen werden getestet ...');try{let r=await fetch(`/api/consoles/${id}/test`,{method:'POST'});let x=r.ok?await r.json():await r.text();await appMessage('Verbindungstest','<pre>'+E(typeof x==='string'?x:JSON.stringify(x,null,2))+'</pre>')}finally{busy(false)}}
async function scanConsole(id){let c=currentConsoleRows.find(x=>x.id===id);if(!c)return;let type=c.provider_type||'ps3',text='',busyText='Konsoleninventar wird gelesen ...';if(type==='xbox360_aurora'){text='Aurora-Inventar über FTP aus <b>content.db</b> und <b>settings.db</b> laden?<br><br>Xbox-360-Spiele, XBLA, Xbox Classic und Title Updates werden strukturiert eingelesen. NOVA dient ergänzend zur Diagnose.';busyText='Aurora-Datenbanken werden über FTP eingelesen ...'}else if(type==='ps4_goldhen'){text='PS4-Inventar über <b>GoldHEN FTP</b> aus <b>app.db</b> und <b>addcont.db</b> laden?<br><br>GameVault liest installierte CUSA-Titel, APP_VER, Größe, Speicherort und DLC read-only.';busyText='PS4 app.db und addcont.db werden über FTP eingelesen ...'}else if(type==='xboxclassic_xbmc4gamers'){text='Xbox-Classic-Inventar aus der <b>XBMC4Gamers MyPrograms6.db</b> über FTP laden?<br><br>GameVault liest Titel, TitleID, Pfad, Größe und vorhandene XBMC4Gamers-Metadaten. Dateien auf der Xbox werden nicht verändert.';busyText='XBMC4Gamers-Datenbank wird über FTP eingelesen ...'}else{text='PS3-Inventar über FTP und optional <b>webMAN MOD</b> scannen?<br><br>GameVault liest PARAM.SFO aus /dev_hdd0/game, erkennt PS1 Classics, PS2 Classics, PSP Minis/Remaster und liest metadata_db_hdd diagnostisch aus und protokolliert die XMB/MMS-Daten unter /dev_hdd0/mms/db. metadata_db_plus und metadata_db_system werden bewusst ignoriert. Alle Zugriffe sind read-only.';busyText='PS3-Inventar wird gelesen ...'}if(!await appConfirm('Konsoleninventar',text))return;busy(true,busyText);try{let r=await fetch(`/api/consoles/${id}/scan`,{method:'POST'});let x=r.ok?await r.json():await r.text();await appMessage('Konsolenscan','<pre>'+E(typeof x==='string'?x:JSON.stringify(x,null,2))+'</pre>');if(r.ok)await loadConsoles()}finally{busy(false)}}
async function scanConsoleSizes(id){let c=currentConsoleRows.find(x=>x.id===id);if(!c)return;let xbox=c.provider_type==='xbox360_aurora';let text=xbox?'Standardmäßig werden nur Spiele ohne bereits gespeicherte Größe geprüft.<br><br>Bei neuen Aurora-Spielen ist dadurch nur der neue Pfad zu traversieren.':'Standardmäßig werden nur PS3-Inhalte ohne Größe geprüft.<br><br>Lokale PS3ISO-Dateien und lokale Folder-Games werden über FTP gemessen. <b>net0/net1</b> werden als Remote-Pfade übersprungen.';if(!await appConfirm((xbox?'Xbox':'PS3')+'-Spielgrößen',text))return;let forceAll=await appConfirm('Größenmodus','<b>Nur fehlende Größen</b> ist der schnelle Standard.<br><br>Mit „Bestätigen“ werden ausnahmsweise <b>alle Größen neu berechnet</b>.<br>Mit „Abbrechen“ werden nur fehlende Größen ermittelt.');busy(true,forceAll?'Alle Spielgrößen werden neu berechnet ...':'Fehlende Spielgrößen werden berechnet ...');try{let r=await fetch(`/api/consoles/${id}/scan-sizes`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({force_all:forceAll})});let x=r.ok?await r.json():await r.text();if(!r.ok){await appMessage('Größenscan fehlgeschlagen','<pre>'+E(x)+'</pre>');return}let diag=(x.failure_examples||[]).map(f=>`<div class="dq-row"><b>${E(f.title)}</b><br>${E(f.source_path||'')}<br><span class="warning small">${E(f.error||'nicht messbar')}</span></div>`).join('');await appMessage('Größenscan abgeschlossen',`Modus: <b>${x.force_all?'Alle neu':'Nur fehlende'}</b><br>Geprüft: ${x.checked}<br>Neu aktualisiert: ${x.updated}<br>Bereits im Cache: ${x.already_cached}<br>Remote übersprungen: ${x.remote_skipped}<br>Fehler: ${x.failed}<br>Gesamtgröße: <b>${E(x.total)}</b>${diag?'<h3>Hinweise</h3>'+diag:''}`);await loadConsoles();await load();if(selected)show(selected)}finally{busy(false)}}
function formatBytesJs(value){let n=Number(value||0),units=['B','KB','MB','GB','TB'],i=0;while(n>=1024&&i<units.length-1){n/=1024;i++}return (i===0?Math.round(n):n.toFixed(2).replace('.',','))+' '+units[i]}
async function bulkImportConsole(id,name){busy(true,'Importvorschau wird erstellt ...');let preview;try{let r=await fetch(`/api/consoles/${id}/bulk-import-preview`);preview=r.ok?await r.json():await r.text();if(!r.ok){await appMessage('Importfehler','<pre>'+E(preview)+'</pre>');return}}finally{busy(false)}let examples=(preview.examples||[]).slice(0,12).map(x=>`<li>${E(x.title)}${x.identifier?' · '+E(x.identifier):''}${x.size?' · '+E(x.size):''}</li>`).join('');let text=`<b>${E(name)}</b><br><br>Unbekannte Inventareinträge: ${preview.unknown_rows}<br>Als neue Spiele importierbar: <b>${preview.importable}</b><br>Bereits vorhandene IDs: ${preview.already_existing}<br>TU/DLC übersprungen: ${preview.children_skipped}${examples?`<br><br><b>Beispiele</b><ul>${examples}</ul>`:''}<br>Die Spiele werden mit ihrer Konsolen-ID angelegt und sofort verknüpft. Für große Bibliotheken erfolgt IGDB-Anreicherung anschließend separat über die bestehenden Resolver.`;if(!await appConfirm('Unbekannte gesammelt übernehmen',text))return;busy(true,'Unbekannte Konsolenspiele werden übernommen ...');try{let r=await fetch(`/api/consoles/${id}/bulk-import`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({igdb:false})});let x=r.ok?await r.json():await r.text();if(!r.ok){await appMessage('Massenimport fehlgeschlagen','<pre>'+E(x)+'</pre>');return}await load();await loadConsoles();await appMessage('Massenimport abgeschlossen',`Neu angelegt: <b>${x.created}</b><br>Mit vorhandenen IDs verknüpft: ${x.linked_existing}<br>Fehler: ${x.failed}${x.errors?.length?'<br><pre>'+E(x.errors.join('\n'))+'</pre>':''}`)}finally{busy(false)}}
let installedRows=[],installedConsoleId=null,installedConsoleName='',matchInstalledId=null,matchInstalledPlatform='';
async function showInstalled(id,name){installedConsoleId=id;installedConsoleName=name;installedModal.classList.add('show');installedTitle.textContent='Installierte Inhalte · '+name;installedBody.innerHTML='<span class="spinner"></span> Inhalte werden geladen ...';let r=await fetch(`/api/consoles/${id}/installed`);if(!r.ok){installedBody.textContent=await r.text();return}installedRows=await r.json();let types=[...new Set(installedRows.map(x=>x.category||x.content_type).filter(Boolean))].sort();installedType.innerHTML='<option value="">Alle Typen</option>'+types.map(x=>`<option>${E(x)}</option>`).join('');installedStatus.value='unknown';renderInstalled()}
function installedChildHtml(x){return `<div class="installed-child"><span><b class="child-title">${E(x.title)}</b><br><span class="small mut">${E(x.content_id||x.identifier||'keine ID')} · ${E(x.path)}</span></span><span>${E(x.installed_version||'–')}<br><span class="storage-pill">${E(x.storage||'–')}</span>${x.installed_size_bytes!=null?`<br><span class="small">${formatBytesJs(x.installed_size_bytes)}</span>`:''}</span><span>${E(x.category||x.content_type||'–')}<br>${x.game_id?'<span class="status-ok small">über Spiel zugeordnet</span>':'<span class="warning small">ohne Parent</span>'}</span></div>`}
function installedParentHtml(x,children){return `<div class="installed-parent"><div class="installed-row"><span><b>${E(x.title)}</b><br><span class="small mut">${E(x.identifier||'keine ID')} · ${E(x.path)}</span></span><span>${E(x.installed_version||'–')}<br><span class="storage-pill">${E(x.storage||'–')}</span></span><span>${E(x.category||x.content_type||'–')}</span><span>${x.game_id?`<span class="status-ok">zugeordnet</span><br><span class="small">${E(x.linked_game?.title||'')}</span>`:'<span class="warning">unbekannt</span>'}<br><span class="small">${E(x.source)}</span>${x.game_id?`<br><button class="btn unmatch-btn" onclick="unmatchInstalled(${x.id})">Zuordnung lösen</button>`:''}</span>${!x.game_id?`<div class="suggestions"><b>Aktionen</b><br>${x.suggestions.length?x.suggestions.map(s=>`<button class="btn suggestion-btn" onclick="matchInstalled(${x.id},${s.id},${installedConsoleId},'${E(installedConsoleName)}','${E(x.platform)}','${E(x.identifier||'')}')">Zuordnen: ${E(s.title)} · ${Math.round(s.score*100)} %</button>`).join(''):''}<button class="btn suggestion-btn" onclick="openLibraryMatch(${x.id},'${E(x.platform)}','${E(x.title)}','${E(x.identifier||'')}')">Vorhandenes Spiel suchen</button><button class="btn blue suggestion-btn" onclick="createFromInstalled(${x.id},${installedConsoleId},'${E(installedConsoleName)}','${E(x.title)}','${E(x.identifier||'')}')">Als neues Spiel übernehmen</button></div>`:''}</div>${children.length?`<div class="installed-children">${children.map(installedChildHtml).join('')}</div>`:''}</div>`}
function renderInstalled(){let status=installedStatus.value,type=installedType.value;let childCats=['DLC','Title Update'];let parents=installedRows.filter(x=>!childCats.includes(x.category)),children=installedRows.filter(x=>childCats.includes(x.category));let unknown=parents.filter(x=>!x.game_id).length,matched=parents.length-unknown;installedCounts.textContent=`Spiele ${parents.length} · Unbekannt ${unknown} · Zugeordnet ${matched} · TU/DLC ${children.length}`;let directChildren=type&&childCats.includes(type);if(directChildren){let rows=children.filter(x=>(x.category||x.content_type)===type&&(status==='all'||(status==='unknown'&&!x.game_id)||(status==='matched'&&x.game_id)));installedBody.innerHTML=rows.length?`<div class="installed-children">${rows.map(installedChildHtml).join('')}</div>`:'<p>Keine Inhalte für diesen Filter.</p>';return}let rows=parents.filter(x=>(status==='all'||(status==='unknown'&&!x.game_id)||(status==='matched'&&x.game_id))&&(!type||(x.category||x.content_type)===type));installedBody.innerHTML=rows.length?rows.map(x=>{let kids=children.filter(c=>(c.game_id&&x.game_id&&c.game_id===x.game_id)||(!c.game_id&&c.identifier&&c.identifier===x.identifier));return installedParentHtml(x,kids)}).join(''):'<p>Keine Inhalte für diesen Filter.</p>'}
async function unmatchInstalled(installedId){let x=installedRows.find(r=>r.id===installedId);if(!x)return;let text=`Zuordnung von <b>${E(x.title)}</b> zu <b>${E(x.linked_game?.title||'GameVault-Spiel')}</b> lösen?`;if(x.identifier)text+=`<br><br>Eine durch den Konsolenscan übernommene ${x.platform==='PlayStation 3'?'Serial':'TitleID'} wird ebenfalls entfernt. Manuell gepflegte IDs bleiben erhalten.`;if(!await appConfirm('Zuordnung lösen',text))return;let r=await fetch(`/api/installed-games/${installedId}/unmatch`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({remove_scan_identifier:true})});let out=r.ok?await r.json():await r.text();if(!r.ok){await appMessage('Fehler','<pre>'+E(out)+'</pre>');return}await load();await showInstalled(installedConsoleId,installedConsoleName);await appMessage('Zuordnung gelöst',out.identifier_removed?'Zuordnung und scanübernommene ID wurden entfernt.':'Zuordnung wurde entfernt. Eine manuell gepflegte ID blieb erhalten.')}
async function matchInstalled(installedId,gameId,consoleId,name,platform,identifier){let idLabel=platform==='PlayStation 3'?'Serial':'TitleID';let text=`Installierten ${E(platform)}-Titel mit dem gewählten GameVault-Spiel verknüpfen?${identifier?`<br><br>Fehlende ${idLabel} übernehmen: <b>${E(identifier)}</b>`:''}`;if(!await appConfirm(platform+' zuordnen',text))return;let r=await fetch(`/api/installed-games/${installedId}/match/${gameId}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({apply_identifier:true})});if(!r.ok){await appMessage('Fehler','<pre>'+E(await r.text())+'</pre>');return}libraryMatchModal.classList.remove('show');await load();await showInstalled(consoleId,name)}
async function openLibraryMatch(installedId,platform,title,identifier){matchInstalledId=installedId;matchInstalledPlatform=platform;libraryMatchTitle.textContent=platform+'-Bibliothek zuordnen';libraryMatchQuery.value=title||'';libraryHideLinked.checked=true;libraryMatchModal.classList.add('show');await searchLibraryMatch()}
let librarySearchTimer=null;function searchLibraryMatch(){clearTimeout(librarySearchTimer);librarySearchTimer=setTimeout(runLibraryMatchSearch,180)}
async function runLibraryMatchSearch(){libraryMatchBody.innerHTML='<span class="spinner"></span> Bibliothek wird durchsucht ...';let url=`/api/library/search?platform=${encodeURIComponent(matchInstalledPlatform)}&q=${encodeURIComponent(libraryMatchQuery.value)}&exclude_linked=${libraryHideLinked.checked?'true':'false'}&limit=100`;let r=await fetch(url);if(!r.ok){libraryMatchBody.textContent=await r.text();return}let rows=await r.json();libraryMatchBody.innerHTML=rows.length?rows.map(g=>`<div class="library-result">${g.cover_source?`<img src="${E(g.cover_source)}">`:'<div class="mini-cover platform-mark">GV</div>'}<div><b>${E(g.title)}</b><br><span class="mut small">${E(g.title_id||'keine ID')} ${g.publisher?'· '+E(g.publisher):''} ${g.release_date?'· '+E(g.release_date):''}</span></div><button class="btn blue" onclick="matchInstalled(${matchInstalledId},${g.id},${installedConsoleId},'${E(installedConsoleName)}','${E(matchInstalledPlatform)}','')">Zuordnen</button></div>`).join(''):'<p>Keine Bibliothekstreffer. Suche kürzer, z. B. nur nach „Dirt“.</p>'}
async function createFromInstalled(installedId,consoleId,consoleName,title,identifier){let text=`Neues Konsolenspiel anlegen?<br><br><b>${E(title)}</b><br>${E(identifier||'keine Serial')}<br><br>Der Konsoleneintrag wird direkt verknüpft. Danach versucht GameVault automatisch IGDB-Metadaten und ein lokales Cover zu laden.`;if(!await appConfirm('Von Konsole übernehmen',text))return;busy(true,'Konsolenspiel wird übernommen und mit IGDB angereichert ...');try{let r=await fetch(`/api/installed-games/${installedId}/create-game`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({title})});let x=r.ok?await r.json():await r.text();if(!r.ok){await appMessage('Übernahme fehlgeschlagen','<pre>'+E(x)+'</pre>');return}await load();await showInstalled(consoleId,consoleName);let info=x.created?'Spiel wurde neu angelegt.':'Ein Spiel mit dieser Serial existierte bereits und wurde verknüpft.';if(x.igdb?.matched)info+=`<br>IGDB: ${E(x.igdb.title)} · ${Math.round((x.igdb.confidence||0)*100)} %`;else if(x.igdb?.review)info+=`<br>IGDB-Vorschlag muss geprüft werden: ${E(x.igdb.title)} · ${Math.round((x.igdb.confidence||0)*100)} %`;else if(x.igdb?.detail)info+=`<br>IGDB: ${E(x.igdb.detail)}`;await appMessage('Konsolenspiel übernommen',info)}finally{busy(false)}}
async function deleteConsole(id){if(!await appConfirm('Konsole löschen','Konsole und Scanergebnisse entfernen?'))return;let r=await fetch(`/api/consoles/${id}`,{method:'DELETE'});if(!r.ok)await appMessage('Fehler','<pre>'+E(await r.text())+'</pre>');else await loadConsoles()}
async function openSizeAudit(){sizeAuditModal.classList.add('show');sizeAuditBody.innerHTML='<span class="spinner"></span> Größen werden geprüft ...';let r=await fetch('/api/packages/size-audit?threshold=500');if(!r.ok){sizeAuditBody.textContent=await r.text();return}let rows=await r.json();sizeAuditBody.innerHTML=rows.length?rows.map(x=>`<div class="dq-row" id="size-${x.id}"><b>${E(x.name||x.filename)}</b><br><span class="warning">${x.size_gb.toLocaleString('de-DE')} GB</span> · möglicher Dezimalfehler: ${x.suggested_div1000.toLocaleString('de-DE')} GB<br><span class="mut small">${E(x.filename)}</span><br><button class="btn" onclick="fixPackageSize(${x.id})">Durch 1000 teilen</button>${x.game_id?` <button class="btn" onclick="sizeAuditModal.classList.remove('show');show(${x.game_id})">Spiel öffnen</button>`:''}</div>`).join(''):'<p>Keine Packages über 500 GB gefunden.</p>'}
async function fixPackageSize(id){if(!await appConfirm('Größe korrigieren','Diese Package-Größe durch 1000 teilen?'))return;let r=await fetch(`/api/packages/${id}/size-divide-1000`,{method:'POST'});if(!r.ok){await appMessage('Fehler','<pre>'+E(await r.text())+'</pre>');return}document.getElementById('size-'+id)?.remove();await load();await appMessage('Korrigiert','Die Größe wurde korrigiert und die Gesamtsumme neu berechnet.')}
function versionKeyJs(v){let n=(String(v||'').match(/\d+/g)||[]).map(Number);return n.reduce((a,x)=>a*1000+x,0)}function consoleChildLine(x){return `<div class="console-content-line"><span><b>${E(x.title)}</b><br><span class="small mut">MediaID ${E(x.content_id||'–')} · ${E(x.path||'')}</span></span><span>${E(x.category||'–')}</span><span><b>${E(x.installed_version||'–')}</b></span><span>${E(x.file_size||'–')}<br><span class="small">${E(x.storage||'')}</span></span></div>`}
async function loadGameConsoleContent(gameId){let target=document.getElementById('consoleContentDetail');if(!target)return;let r=await fetch(`/api/games/${gameId}/console-content`);if(!r.ok||selected!==gameId)return;let rows=await r.json();let children=rows.filter(x=>['DLC','Title Update'].includes(x.category));if(!children.length){target.innerHTML='';return}let groups={};children.forEach(x=>{let k=x.console_name||x.platform;(groups[k]??=[]).push(x)});target.innerHTML='<h3>Updates und Zusatzinhalte</h3>'+Object.entries(groups).map(([name,items])=>{let tus=items.filter(x=>x.category==='Title Update').sort((a,b)=>versionKeyJs(b.installed_version)-versionKeyJs(a.installed_version)),dlc=items.filter(x=>x.category==='DLC');return `<div class="console-content-group"><h4>${E(name)}</h4>${tus.length?`<h4 class="mut">Title Updates</h4>${tus.map(consoleChildLine).join('')}`:''}${dlc.length?`<h4 class="mut">DLC</h4>${dlc.map(consoleChildLine).join('')}`:''}</div>`}).join('')}
async function deleteGame(id){let r=await fetch(`/api/games/${id}/delete-preview`);if(!r.ok){await appMessage('Löschen fehlgeschlagen','<pre>'+E(await r.text())+'</pre>');return}let x=await r.json();let text=`<div class="delete-summary"><b>${E(x.title)}</b><br>${E(x.platform)}${x.title_id?' · '+E(x.title_id):''}<br><br>Aus GameVault entfernen:<br>• ${x.packages} Backup-Package-Datensätze<br>• ${x.installed_links} Konsolen-Zuordnungen<br>• ${x.local_cover?'lokales Cover<br>':''}• ${x.duplicate_exclusions} Duplikat-Ausschlüsse<br><br><b>Nicht gelöscht:</b> Dateien auf NAS/HDD oder Inhalte auf einer Konsole.</div>`;if(!await appConfirm('Spiel endgültig aus GameVault löschen?',text))return;busy(true,'Spiel wird aus GameVault gelöscht ...');try{r=await fetch(`/api/games/${id}`,{method:'DELETE'});if(!r.ok){await appMessage('Löschen fehlgeschlagen','<pre>'+E(await r.text())+'</pre>');return}selected=null;detail.innerHTML='<span class="mut">Spiel auswählen</span>';await load();await appMessage('Spiel gelöscht','Der GameVault-Eintrag wurde gelöscht. Vorhandene Konsoleninhalte erscheinen beim nächsten Scan wieder als unbekannt.')}finally{busy(false)}}
async function enrichX360(){busy(true,'x360db reichert Xbox-360-Spiele an ...');try{let r=await fetch('/api/x360db/enrich',{method:'POST'});let x=r.ok?await r.json():await r.text();await appMessage('x360db','<pre>'+E(typeof x==='string'?x:JSON.stringify(x,null,2))+'</pre>');if(r.ok)await load()}finally{busy(false)}}
</script></body></html>'''

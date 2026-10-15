"""Contentless FTS5 bases and exact CAS-backed delta replay, memory metadata v2."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import zlib

from .core import digest,valid_hash
from .store import _publish

PROFILES=("full-v1","compact-full-v2","compact-delta-v2")
MAX_DELTAS=8
MAX_DELTA_BYTES=64<<20
LOCATORS="key,path,offset,length,lower(hex(sha)),kind"


def profile(memory):
    path=memory.root/"indexes/config.json"
    if not path.exists():return "full-v1"
    if path.is_symlink():raise ValueError("Linked memory index configuration")
    value=json.loads(path.read_bytes())
    if value.get("version")!=2 or value.get("profile") not in PROFILES[1:]:
        raise ValueError("Invalid memory index profile")
    return value["profile"]


def source_files(memory,sid):
    with memory.store.snapshot(sid) as snap:
        return {p:{"bytes":e["size"],"sha256":e["sha256"]} for p,e in snap.files.items()}


def parse_record(memory,sid,meta):
    from .memory import records
    key,path,offset,length,sha,kind=meta
    with memory.store.snapshot(sid) as snap:raw=snap.read_range(path,offset,length)
    if digest(raw)!=sha:raise ValueError("Retrieved original record SHA mismatch")
    parsed=list(records(path,raw))
    if len(parsed)!=1 or parsed[0][0]!=key or parsed[0][5]!=kind:
        raise ValueError("Evidence locator differs from immutable source")
    return parsed[0]


def load_delta(memory,desc):
    sha=desc.get("sha256");size=desc.get("raw_bytes")
    if not valid_hash(sha) or type(size) is not int or not 0<size<=MAX_DELTA_BYTES:
        raise ValueError("Invalid memory delta descriptor")
    path=memory.root/"indexes"/(sha+".delta")
    raw=path.read_bytes() if not path.is_symlink() else b""
    if digest(raw)!=sha:raise ValueError("Memory index delta SHA mismatch")
    decoder=zlib.decompressobj();content=decoder.decompress(raw,size+1)
    if len(content)!=size or not decoder.eof or decoder.unused_data:
        raise ValueError("Invalid compressed memory delta")
    value=json.loads(content)
    if value.get("version")!=2 or any(value.get(k)!=desc.get(k) for k in ("parent_snapshot","snapshot_id")):
        raise ValueError("Memory delta identity mismatch")
    return value


def validate(memory,sid,value):
    base=value.get("base_snapshot_id")
    if not valid_hash(base) or not valid_hash(value.get("index_sha256")):
        raise ValueError("Invalid compact memory base")
    path=memory.root/"indexes"/(base+".sqlite")
    if path.is_symlink() or digest(path.read_bytes())!=value["index_sha256"]:
        raise ValueError("Memory index SHA mismatch")
    if not isinstance(value.get("deltas"),list) or len(value["deltas"])>MAX_DELTAS:
        raise ValueError("Invalid memory delta chain")
    previous=source_files(memory,base)
    for desc in value["deltas"]:
        # A label-only snapshot may alias an existing view, but its source tree
        # must equal that view before the next delta can be applied.
        if not valid_hash(desc.get("parent_snapshot")) or not valid_hash(desc.get("snapshot_id")):
            raise ValueError("Invalid memory delta snapshot")
        if source_files(memory,desc["parent_snapshot"])!=previous:
            raise ValueError("Memory delta parent source mismatch")
        load_delta(memory,desc)
        previous=source_files(memory,desc["snapshot_id"])
    if previous!=value["source_files"] or previous!=source_files(memory,sid):
        raise ValueError("Memory manifest does not bind current CAS snapshot")


def schema(db):
    db.execute("CREATE TABLE locators(rowid INTEGER PRIMARY KEY,key TEXT UNIQUE NOT NULL,path TEXT NOT NULL,offset INTEGER NOT NULL,length INTEGER NOT NULL,sha BLOB NOT NULL CHECK(length(sha)=32),kind TEXT NOT NULL)")
    # Keep all token positions and column sizes: same BM25 semantics as v0.15.
    db.execute("CREATE VIRTUAL TABLE evidence USING fts5(title,body,content='', tokenize='porter unicode61')")


def insert(db,meta,title,sentences,rowid=None):
    if rowid is None:rowid=db.execute("SELECT coalesce(max(rowid),0)+1 FROM locators").fetchone()[0]
    db.execute("INSERT INTO locators VALUES(?,?,?,?,?,?,?)",(rowid,*meta[:4],bytes.fromhex(meta[4]),meta[5]))
    db.execute("INSERT INTO evidence(rowid,title,body) VALUES(?,?,?)",(rowid,title,"\n".join(sentences)))


def replay(memory,db,delta):
    for key in delta["removed"]:
        old=db.execute("SELECT rowid,"+LOCATORS+" FROM locators WHERE key=?",(key,)).fetchone()
        if old is None:raise ValueError("Memory delta removes absent record")
        rowid,*meta=old;_,title,sentences,_,_,_=parse_record(memory,delta["parent_snapshot"],meta)
        db.execute("INSERT INTO evidence(evidence,rowid,title,body) VALUES('delete',?,?,?)",(rowid,title,"\n".join(sentences)))
        db.execute("DELETE FROM locators WHERE rowid=?",(rowid,))
    for meta in delta["upserted"]:
        old=db.execute("SELECT rowid,"+LOCATORS+" FROM locators WHERE key=?",(meta[0],)).fetchone()
        if old and old[5]==meta[4]:
            # Same exact record, relocated by a preceding edit: postings unchanged.
            db.execute("UPDATE locators SET path=?,offset=?,length=?,sha=?,kind=? WHERE rowid=?",(*meta[1:4],bytes.fromhex(meta[4]),meta[5],old[0]))
            continue
        rowid=old[0] if old else None
        if old:
            _,title,sentences,_,_,_=parse_record(memory,delta["parent_snapshot"],old[1:])
            db.execute("INSERT INTO evidence(evidence,rowid,title,body) VALUES('delete',?,?,?)",(rowid,title,"\n".join(sentences)))
            db.execute("DELETE FROM locators WHERE rowid=?",(rowid,))
        _,title,sentences,_,_,_=parse_record(memory,delta["snapshot_id"],meta)
        insert(db,meta,title,sentences,rowid)
    db.commit()


@contextmanager
def view(memory,value,*,writable=False):
    path=memory.root/"indexes"/(value["base_snapshot_id"]+".sqlite")
    source=sqlite3.connect(path.as_uri()+"?mode=ro",uri=True);db=source
    try:
        if value["deltas"] or writable:
            db=sqlite3.connect(":memory:");source.backup(db)
            for desc in value["deltas"]:replay(memory,db,load_delta(memory,desc))
        if db.execute("SELECT count(*) FROM locators").fetchone()[0]!=value["records"]:
            raise ValueError("Memory index record count mismatch")
        yield db
    finally:
        if db is not source:db.close()
        source.close()


def scan(memory,sid):
    from .memory import records
    result={}
    with memory.store.snapshot(sid) as snap:
        for path,entry in snap.files.items():
            if entry["size"]>64<<20:raise ValueError("Memory source file exceeds 64 MiB prototype limit")
            for key,title,sentences,offset,raw,kind in records(path,snap.read_range(path)):
                if key in result:raise ValueError("Duplicate evidence document key")
                result[key]=([key,path,offset,len(raw),digest(raw),kind],title,sentences)
    if not result:raise ValueError("Evidence index must not be empty")
    return result


def build(memory,sid,selected):
    from .memory import _json
    current=scan(memory,sid);previous=None;ops=None
    if selected=="compact-delta-v2" and (memory.root/"HEAD.json").exists():
        old_sid=memory.current();old=memory._manifest(old_sid)
        if old["version"]==2:
            with view(memory,old) as db:prior={r[0]:list(r) for r in db.execute("SELECT "+LOCATORS+" FROM locators")}
            removed=sorted(set(prior)-set(current))
            upserted=[meta for key,(meta,_,_) in current.items() if prior.get(key)!=meta]
            # Locator relocation also costs replay work. Rebuild a checkpoint if
            # more than 25% of records move/change, or after eight deltas.
            changed=len(removed)+len(upserted)
            if len(old["deltas"])<MAX_DELTAS and changed<=max(1,len(prior)//4):
                previous=old
                if removed or upserted:ops={"version":2,"parent_snapshot":old_sid,"snapshot_id":sid,"removed":removed,"upserted":upserted}
    new_bytes=0
    if previous is None:
        fd,temp=tempfile.mkstemp(prefix=".compact-index-",dir=memory.root/"indexes");os.close(fd)
        db=None
        try:
            db=sqlite3.connect(temp);schema(db)
            for meta,title,sentences in current.values():insert(db,meta,title,sentences)
            db.commit();db.close();db=None
            with open(temp,"r+b") as stream:os.fsync(stream.fileno())
            raw=Path(temp).read_bytes();target=memory.root/"indexes"/(sid+".sqlite")
            if target.exists():
                if target.is_symlink() or target.read_bytes()!=raw:raise ValueError("Memory orphan base identity differs")
            else:os.link(temp,target);new_bytes=len(raw)
            base=sid;sha=digest(raw);deltas=[]
        finally:
            if db is not None:db.close()
            if Path(temp).exists():Path(temp).unlink()
    else:
        base=previous["base_snapshot_id"];sha=previous["index_sha256"];deltas=list(previous["deltas"])
        if ops is not None:
            raw=_json(ops)
            if len(raw)>MAX_DELTA_BYTES:raise ValueError("Memory delta too large")
            encoded=zlib.compress(raw,6);key=digest(encoded);target=memory.root/"indexes"/(key+".delta")
            if not target.exists():_publish(target,encoded);new_bytes=len(encoded)
            elif target.read_bytes()!=encoded:raise ValueError("Memory delta identity differs")
            deltas.append({"sha256":key,"raw_bytes":len(raw),"parent_snapshot":ops["parent_snapshot"],"snapshot_id":sid})
    value={"version":2,"snapshot_id":sid,"base_snapshot_id":base,"index_sha256":sha,"deltas":deltas,
           "records":len(current),"source_files":source_files(memory,sid),"retriever":"SQLite FTS5 BM25, porter unicode61; contentless base plus exact global delta replay"}
    # Validate/replay before publishing HEAD: bad deletions must never become current.
    validate(memory,sid,value)
    with view(memory,value):pass
    _publish(memory.root/"manifests"/(sid+".json"),_json(value))
    active=(memory.root/"indexes"/(base+".sqlite")).stat().st_size+sum((memory.root/"indexes"/(d["sha256"]+".delta")).stat().st_size for d in deltas)
    return {"indexed_records":len(current),"index_bytes":active,"new_index_bytes":new_bytes,"index_reused":new_bytes==0,"delta_depth":len(deltas),"index_profile":selected}


def search(memory,value,query,top_k):
    with view(memory,value) as db:
        return db.execute("SELECT l.key,l.path,l.offset,l.length,lower(hex(l.sha)),l.kind,bm25(evidence) FROM evidence JOIN locators l ON l.rowid=evidence.rowid WHERE evidence MATCH ? ORDER BY bm25(evidence),l.key LIMIT ?",(query,top_k)).fetchall()

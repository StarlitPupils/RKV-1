"""Contentless FTS5 bases, exact replay and query-local evidence resources."""
from contextlib import contextmanager,closing,ExitStack,nullcontext
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import zlib

from .core import digest,valid_hash
from .store import _publish

PROFILES=("full-v1","compact-full-v2","compact-delta-v2","compact-base-v3","compact-budget-v3")
V3_PROFILES=("compact-base-v3","compact-budget-v3")
MAX_DELTAS=8
MAX_RELOCATIONS=256
MAX_DELTA_BYTES=64<<20
LOCATORS="key,path,offset,length,lower(hex(sha)),kind"


class QueryResources:
    """Verify each immutable snapshot/delta once per request, never across queries.

    Decoded CAS blocks and SQLite views are deliberately not cached. Every range
    read still verifies stored/raw object hashes, and every hit its record hash.
    """
    def __init__(self,memory):
        self.memory=memory;self.stack=ExitStack();self.snapshots={};self.deltas={}

    def snapshot(self,sid):
        if sid not in self.snapshots:
            self.snapshots[sid]=self.stack.enter_context(self.memory.store.snapshot(sid))
        return self.snapshots[sid]

    def __enter__(self):return self

    def __exit__(self,*args):
        try:return self.stack.__exit__(*args)
        finally:self.snapshots.clear();self.deltas.clear()


def snapshot(memory,sid,query=None):
    return memory.store.snapshot(sid) if query is None else nullcontext(query.snapshot(sid))


def configuration(memory):
    path=memory.root/"indexes/config.json"
    if not path.exists():return {"version":1,"profile":"full-v1"}
    if path.is_symlink():raise ValueError("Linked memory index configuration")
    value=json.loads(path.read_bytes())
    if type(value) is not dict:raise ValueError("Invalid memory index configuration")
    expected=3 if value.get("profile") in V3_PROFILES else 2
    if value.get("version")!=expected or value.get("profile") not in PROFILES[1:]:
        raise ValueError("Invalid memory index profile")
    if value["profile"]=="compact-budget-v3":
        from .memory_budget import budget
        if type(value.get("replay_budget")) is not dict:raise ValueError("Invalid memory replay budget")
        value["replay_budget"]=budget(value["replay_budget"])
    return value


def profile(memory):return configuration(memory)["profile"]


def source_files(memory,sid,query=None):
    with snapshot(memory,sid,query) as snap:
        return {p:{"bytes":e["size"],"sha256":e["sha256"]} for p,e in snap.files.items()}


def parse_record(memory,sid,meta,query=None):
    from .memory import records
    key,path,offset,length,sha,kind=meta
    with snapshot(memory,sid,query) as snap:raw=snap.read_range(path,offset,length)
    if digest(raw)!=sha:raise ValueError("Retrieved original record SHA mismatch")
    parsed=list(records(path,raw))
    if len(parsed)!=1 or parsed[0][0]!=key or parsed[0][5]!=kind:
        raise ValueError("Evidence locator differs from immutable source")
    return parsed[0]


def load_delta(memory,desc,query=None):
    sha=desc.get("sha256");size=desc.get("raw_bytes")
    if not valid_hash(sha) or type(size) is not int or not 0<size<=MAX_DELTA_BYTES:
        raise ValueError("Invalid memory delta descriptor")
    # The complete descriptor is part of the key: an alias with different
    # identity fields must be checked rather than reusing a different overlay.
    key=json.dumps(desc,sort_keys=True,separators=(",",":"))
    if query is not None and key in query.deltas:return query.deltas[key]
    path=memory.root/"indexes"/(sha+".delta")
    raw=path.read_bytes() if not path.is_symlink() else b""
    if digest(raw)!=sha:raise ValueError("Memory index delta SHA mismatch")
    decoder=zlib.decompressobj();content=decoder.decompress(raw,size+1)
    if len(content)!=size or not decoder.eof or decoder.unused_data:
        raise ValueError("Invalid compressed memory delta")
    value=json.loads(content)
    if value.get("version")!=desc.get("version",2) or any(value.get(k)!=desc.get(k) for k in ("parent_snapshot","snapshot_id")):
        raise ValueError("Memory delta identity mismatch")
    if query is not None:query.deltas[key]=value
    return value


def validate(memory,sid,value,query=None):
    base=value.get("base_snapshot_id")
    if not valid_hash(base) or not valid_hash(value.get("index_sha256")):
        raise ValueError("Invalid compact memory base")
    path=memory.root/"indexes"/(base+".sqlite")
    if path.is_symlink() or digest(path.read_bytes())!=value["index_sha256"]:
        raise ValueError("Memory index SHA mismatch")
    limit=1 if value["version"]==3 else MAX_DELTAS
    if not isinstance(value.get("deltas"),list) or len(value["deltas"])>limit:
        raise ValueError("Invalid memory delta chain")
    previous=source_files(memory,base,query)
    for desc in value["deltas"]:
        if desc.get("version",2)!=value["version"] or (value["version"]==3 and desc.get("parent_snapshot")!=base):
            raise ValueError("Memory overlay format/base mismatch")
        # A label-only snapshot may alias an existing view, but its source tree
        # must equal that view before the next delta can be applied.
        if not valid_hash(desc.get("parent_snapshot")) or not valid_hash(desc.get("snapshot_id")):
            raise ValueError("Invalid memory delta snapshot")
        if source_files(memory,desc["parent_snapshot"],query)!=previous:
            raise ValueError("Memory delta parent source mismatch")
        load_delta(memory,desc,query)
        previous=source_files(memory,desc["snapshot_id"],query)
    if previous!=value["source_files"] or previous!=source_files(memory,sid,query):
        raise ValueError("Memory manifest does not bind current CAS snapshot")


def schema(db):
    db.execute("CREATE TABLE locators(rowid INTEGER PRIMARY KEY,key TEXT UNIQUE NOT NULL,path TEXT NOT NULL,offset INTEGER NOT NULL,length INTEGER NOT NULL,sha BLOB NOT NULL CHECK(length(sha)=32),kind TEXT NOT NULL)")
    # Keep all token positions and column sizes: same BM25 semantics as v0.15.
    db.execute("CREATE VIRTUAL TABLE evidence USING fts5(title,body,content='', tokenize='porter unicode61')")


def insert(db,meta,title,sentences,rowid=None):
    if rowid is None:rowid=db.execute("SELECT coalesce(max(rowid),0)+1 FROM locators").fetchone()[0]
    db.execute("INSERT INTO locators VALUES(?,?,?,?,?,?,?)",(rowid,*meta[:4],bytes.fromhex(meta[4]),meta[5]))
    db.execute("INSERT INTO evidence(rowid,title,body) VALUES(?,?,?)",(rowid,title,"\n".join(sentences)))


def relocate(db,moves):
    """Select every old row before moving any: ranges may cross after a shift."""
    if not isinstance(moves,list) or len(moves)>MAX_RELOCATIONS:raise ValueError("Invalid relocation ranges")
    if not moves:return
    db.execute("CREATE TEMP TABLE offset_moves(rowid INTEGER PRIMARY KEY,new_offset INTEGER NOT NULL CHECK(new_offset>=0))")
    for path,start,end,shift,count in moves:
        if any(type(x) is not int for x in (start,end,shift,count)) or not 0<=start<end or not count>0:
            raise ValueError("Invalid relocation interval")
        cursor=db.execute("INSERT INTO offset_moves SELECT rowid,offset+? FROM locators WHERE path=? AND offset>=? AND offset<?",(shift,path,start,end))
        if cursor.rowcount!=count:raise ValueError("Memory relocation record count mismatch")
    db.execute("UPDATE locators SET offset=(SELECT new_offset FROM offset_moves WHERE offset_moves.rowid=locators.rowid) WHERE rowid IN(SELECT rowid FROM offset_moves)")
    db.execute("DROP TABLE offset_moves")


def relocation_ranges(db,moves):
    """Validate old-row membership without rewriting every unchanged locator."""
    if not isinstance(moves,list) or len(moves)>MAX_RELOCATIONS:raise ValueError("Invalid relocation ranges")
    result={}
    for path,start,end,shift,count in moves:
        if any(type(x) is not int for x in (start,end,shift,count)) or not 0<=start<end or not count>0:
            raise ValueError("Invalid relocation interval")
        actual,lowest=db.execute("SELECT count(*),min(offset) FROM locators WHERE path=? AND offset>=? AND offset<?",(path,start,end)).fetchone()
        if actual!=count:raise ValueError("Memory relocation record count mismatch")
        if lowest+shift<0:raise ValueError("Negative memory relocation offset")
        ranges=result.setdefault(path,[])
        for old_start,old_end,_ in ranges:
            left,right=max(start,old_start),min(end,old_end)
            if left<right and db.execute("SELECT 1 FROM locators WHERE path=? AND offset>=? AND offset<? LIMIT 1",(path,left,right)).fetchone():
                raise ValueError("Overlapping memory relocation rows")
        ranges.append((start,end,shift))
    return result


def moved(meta,ranges):
    key,path,offset,length,sha,kind=meta
    for start,end,shift in ranges.get(path,()):
        if start<=offset<end:return key,path,offset+shift,length,sha,kind
    return tuple(meta)


def replay(memory,db,delta,*,query=None,deferred=False):
    for key in delta["removed"]:
        old=db.execute("SELECT rowid,"+LOCATORS+" FROM locators WHERE key=?",(key,)).fetchone()
        if old is None:raise ValueError("Memory delta removes absent record")
        rowid,*meta=old;_,title,sentences,_,_,_=parse_record(memory,delta["parent_snapshot"],meta,query)
        db.execute("INSERT INTO evidence(evidence,rowid,title,body) VALUES('delete',?,?,?)",(rowid,title,"\n".join(sentences)))
        db.execute("DELETE FROM locators WHERE rowid=?",(rowid,))
    ranges={}
    if delta["version"]==3:
        if deferred:ranges=relocation_ranges(db,delta["relocations"])
        else:relocate(db,delta["relocations"])
    for meta in delta["upserted"]:
        old=db.execute("SELECT rowid,"+LOCATORS+" FROM locators WHERE key=?",(meta[0],)).fetchone()
        if old and old[5]==meta[4]:
            # Same exact record, relocated by a preceding edit: postings unchanged.
            db.execute("UPDATE locators SET path=?,offset=?,length=?,sha=?,kind=? WHERE rowid=?",(*meta[1:4],bytes.fromhex(meta[4]),meta[5],old[0]))
            continue
        rowid=old[0] if old else None
        if old:
            _,title,sentences,_,_,_=parse_record(memory,delta["parent_snapshot"],moved(old[1:],ranges),query)
            db.execute("INSERT INTO evidence(evidence,rowid,title,body) VALUES('delete',?,?,?)",(rowid,title,"\n".join(sentences)))
            db.execute("DELETE FROM locators WHERE rowid=?",(rowid,))
        _,title,sentences,_,_,_=parse_record(memory,delta["snapshot_id"],meta,query)
        insert(db,meta,title,sentences,rowid)
    db.commit()
    return ranges,{meta[0] for meta in delta["upserted"]}


@contextmanager
def view(memory,value,*,writable=False,query=None,deferred=False):
    if deferred and (value["version"]!=3 or writable):raise ValueError("Deferred locators require a read-only v3 query")
    path=memory.root/"indexes"/(value["base_snapshot_id"]+".sqlite")
    source=sqlite3.connect(path.as_uri()+"?mode=ro",uri=True);db=source
    try:
        projection=({},set())
        if value["deltas"] or writable:
            db=sqlite3.connect(":memory:");source.backup(db)
            for desc in value["deltas"]:projection=replay(memory,db,load_delta(memory,desc,query),query=query,deferred=deferred)
        if db.execute("SELECT count(*) FROM locators").fetchone()[0]!=value["records"]:
            raise ValueError("Memory index record count mismatch")
        yield (db,projection) if deferred else db
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


def differences(prior,current):
    """Separate unchanged record bytes that moved from actual record changes."""
    removed=sorted(set(prior)-set(current));upserted=[];moved={}
    for key,(meta,_,_) in current.items():
        old=prior.get(key)
        if old==meta:continue
        if old and old[:2]==meta[:2] and old[3:]==meta[3:]:moved[key]=meta[2]-old[2]
        else:upserted.append(meta)
    ranges=[];pending=None
    for key,old in sorted(prior.items(),key=lambda item:(item[1][1],item[1][2])):
        shift=moved.get(key)
        if shift is None:
            pending=None;continue
        if pending is not None and pending[0]==old[1] and pending[3]==shift:
            pending[2]=old[2]+old[3];pending[4]+=1
        else:
            pending=[old[1],old[2],old[2]+old[3],shift,1];ranges.append(pending)
    return removed,upserted,ranges


def build(memory,sid,selected):
    from .memory import _json
    current=scan(memory,sid);previous=None;ops=None;version=3 if selected in V3_PROFILES else 2
    replay_budget=None;checkpoint_reason="initial" if not (memory.root/"HEAD.json").exists() else "full-profile"
    if version==3 and (memory.root/"HEAD.json").exists():
        old_sid=memory.current();old=memory._manifest(old_sid)
        if old["version"]==3:
            base_sid=old["base_snapshot_id"]
            with closing(sqlite3.connect((memory.root/"indexes"/(base_sid+".sqlite")).as_uri()+"?mode=ro",uri=True)) as db:
                prior={r[0]:list(r) for r in db.execute("SELECT "+LOCATORS+" FROM locators")}
            removed,upserted,moves=differences(prior,current)
            allowed=len(removed)+len(upserted)<=max(1,len(prior)//4) and len(moves)<=MAX_RELOCATIONS
            checkpoint_reason="legacy-change-limit" if len(removed)+len(upserted)>max(1,len(prior)//4) else "relocation-limit"
            if allowed and selected=="compact-budget-v3":
                from .memory_budget import evaluate
                replay_budget=evaluate(memory,base_sid,sid,prior,removed,upserted,configuration(memory)["replay_budget"])
                allowed=replay_budget["reason"] is None
                if not allowed:checkpoint_reason="budget-"+replay_budget["reason"]
            if allowed:
                previous={**old,"deltas":[]}
                checkpoint_reason=None
                if removed or upserted or moves or source_files(memory,base_sid)!=source_files(memory,sid):
                    ops={"version":3,"parent_snapshot":base_sid,"snapshot_id":sid,"removed":removed,"upserted":upserted,"relocations":moves}
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
                if removed or upserted or source_files(memory,old_sid)!=source_files(memory,sid):
                    ops={"version":2,"parent_snapshot":old_sid,"snapshot_id":sid,"removed":removed,"upserted":upserted}
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
            if version==3:deltas[-1]["version"]=3
    value={"version":version,"snapshot_id":sid,"base_snapshot_id":base,"index_sha256":sha,"deltas":deltas,
           "records":len(current),"source_files":source_files(memory,sid),"retriever":"SQLite FTS5 BM25, porter unicode61; contentless base plus exact global delta replay"}
    # Validate/replay before publishing HEAD: bad deletions must never become current.
    validate(memory,sid,value)
    with view(memory,value):pass
    _publish(memory.root/"manifests"/(sid+".json"),_json(value))
    active=(memory.root/"indexes"/(base+".sqlite")).stat().st_size+sum((memory.root/"indexes"/(d["sha256"]+".delta")).stat().st_size for d in deltas)
    return {"indexed_records":len(current),"index_bytes":active,"new_index_bytes":new_bytes,"index_reused":new_bytes==0,"delta_depth":len(deltas),"index_profile":selected,
            "relocation_ranges":len(ops.get("relocations",[])) if ops else 0,"overlay_upserts":len(ops["upserted"]) if ops else 0,
            "checkpoint_reason":checkpoint_reason if previous is None else None,"replay_budget":replay_budget}


def search(memory,value,match,top_k,query=None):
    deferred=value["version"]==3
    with view(memory,value,query=query,deferred=deferred) as prepared:
        db,(ranges,upserted)=prepared if deferred else (prepared,({},set()))
        rows=db.execute("SELECT l.key,l.path,l.offset,l.length,lower(hex(l.sha)),l.kind,bm25(evidence) FROM evidence JOIN locators l ON l.rowid=evidence.rowid WHERE evidence MATCH ? ORDER BY bm25(evidence),l.key LIMIT ?",(match,top_k)).fetchall()
        return [(*moved(row[:6],ranges),row[6]) if row[0] not in upserted else row for row in rows]

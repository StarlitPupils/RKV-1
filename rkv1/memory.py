"""Disposable lexical indexes over immutable, byte-verifiable CAS evidence."""
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import tempfile
import time

from .core import digest,files_in,valid_hash
from .store import Store,_publish

MAX_RECORD=1<<20
STOP=set("a an the is are was were be been of to in on for and or with by as at from that this these those it its".split())


def _json(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8")


def _head(path,value):
    fd,name=tempfile.mkstemp(prefix=".memory-head-",dir=path.parent)
    try:
        with os.fdopen(fd,"wb") as stream:
            stream.write(_json(value));stream.flush();os.fsync(stream.fileno())
        os.replace(name,path)
    finally:
        if Path(name).exists():Path(name).unlink()


def records(path,raw):
    """Locators refer to exact original byte records, including JSON escaping."""
    if path.lower().endswith(".jsonl"):
        offset=0
        for line in raw.splitlines(keepends=True):
            if line.strip():
                if len(line)>MAX_RECORD:raise ValueError("Evidence record exceeds 1 MiB")
                obj=json.loads(line)
                if (not isinstance(obj,dict) or type(obj.get("doc_id")) not in (str,int)
                        or not isinstance(obj.get("title"),str) or not isinstance(obj.get("abstract"),list)
                        or not all(isinstance(s,str) for s in obj["abstract"])):
                    raise ValueError("JSONL requires SciFact doc_id/title/abstract records; do not ingest claim labels")
                key="doc:"+str(obj["doc_id"])
                yield key,obj["title"],obj["abstract"],offset,line,"scifact-jsonl"
            offset+=len(line)
    elif path.lower().endswith((".txt",".md")):
        if len(raw)>MAX_RECORD:raise ValueError("Text evidence file exceeds 1 MiB")
        text=raw.decode("utf-8",errors="strict")
        yield "file:"+path,path,[text],0,raw,"text"
    else:
        raise ValueError("Memory evidence supports .txt/.md or SciFact-format .jsonl only")


class Memory:
    def __init__(self,root):
        self.root=Path(root).resolve();self.store=Store(self.root/"cas")
        for name in ("indexes","manifests","answers"):
            path=self.root/name
            if not path.is_dir() or path.is_symlink():raise ValueError("Invalid memory directories")

    @classmethod
    def create(cls,root,*,compression="zlib",index_profile="compact-base-v3",chunker="fixed",chunk_size=65536):
        from .memory_index import PROFILES
        if index_profile not in PROFILES:raise ValueError("Unknown memory index profile")
        root=Path(root).resolve();root.mkdir(parents=True,exist_ok=False)
        for name in ("indexes","manifests","answers"):(root/name).mkdir()
        Store.create(root/"cas",compression=compression,chunker=chunker,chunk_size=chunk_size)
        if index_profile!="full-v1":_publish(root/"indexes/config.json",_json({"version":3 if index_profile=="compact-base-v3" else 2,"profile":index_profile}))
        return cls(root)

    def add(self,source,*,label="evidence",chunker_backend="python",native_library=None):
        """Replace current evidence snapshot; old snapshots/indexes remain addressable."""
        source=Path(source).resolve()
        if source.is_relative_to(self.root) or self.root.is_relative_to(source):
            raise ValueError("Evidence source and memory root must not overlap; answers are derived records")
        started=time.perf_counter()
        added=self.store.add(source,label=label,chunker_backend=chunker_backend,native_library=native_library);sid=added["snapshot_id"]
        target=self.root/"indexes"/(sid+".sqlite")
        manifest_path=self.root/"manifests"/(sid+".json")
        if manifest_path.exists():
            manifest=self._manifest(sid)
            _head(self.root/"HEAD.json",{"version":1,"snapshot_id":sid})
            base=manifest.get("base_snapshot_id",sid)
            size=(self.root/"indexes"/(base+".sqlite")).stat().st_size
            size+=sum((self.root/"indexes"/(d["sha256"]+".delta")).stat().st_size for d in manifest.get("deltas",[]))
            return {**added,"indexed_records":manifest["records"],"index_bytes":size,"new_index_bytes":0,"index_reused":True,"wall_s":time.perf_counter()-started}
        from .memory_index import profile,build
        selected=profile(self)
        if selected!="full-v1":
            result=build(self,sid,selected)
            _head(self.root/"HEAD.json",{"version":1,"snapshot_id":sid})
            return {**added,**result,"wall_s":time.perf_counter()-started}
        fd,temp=tempfile.mkstemp(prefix=".memory-index-",suffix=".sqlite",dir=target.parent);os.close(fd)
        db=None;count=0
        try:
            db=sqlite3.connect(temp)
            db.execute("CREATE VIRTUAL TABLE evidence USING fts5(key UNINDEXED,path UNINDEXED,offset UNINDEXED,length UNINDEXED,record_sha256 UNINDEXED,kind UNINDEXED,title,body, tokenize='porter unicode61')")
            seen=set()
            with self.store.snapshot(sid) as snap:
                for path,entry in snap.files.items():
                    if entry["size"]>64<<20:raise ValueError("Memory source file exceeds 64 MiB prototype limit")
                    raw=snap.read_range(path)
                    for key,title,sentences,offset,line,kind in records(path,raw):
                        if key in seen:raise ValueError("Duplicate evidence document key")
                        seen.add(key);count+=1
                        db.execute("INSERT INTO evidence VALUES(?,?,?,?,?,?,?,?)",(key,path,offset,len(line),digest(line),kind,title,"\n".join(sentences)))
            if count==0:raise ValueError("Evidence index must not be empty")
            db.commit();db.close();db=None
            with open(temp,"r+b") as stream:os.fsync(stream.fileno())
            sha=digest(Path(temp).read_bytes())
            os.link(temp,target)
            manifest={"version":1,"snapshot_id":sid,"index_sha256":sha,"records":count,
                      "retriever":"SQLite FTS5 BM25, porter unicode61; lexical, no embeddings",
                      "source_files":{p:{"bytes":e["size"],"sha256":e["sha256"]} for p,e in self.store.snapshot(sid).files.items()}}
            _publish(manifest_path,_json(manifest))
            _head(self.root/"HEAD.json",{"version":1,"snapshot_id":sid})
        finally:
            if db is not None:db.close()
            if Path(temp).exists():Path(temp).unlink()
        return {**added,"indexed_records":count,"index_bytes":target.stat().st_size,"index_reused":False,"wall_s":time.perf_counter()-started}

    def current(self):
        head=json.loads((self.root/"HEAD.json").read_bytes())
        if head.get("version")!=1 or not valid_hash(head.get("snapshot_id")):raise ValueError("Invalid memory HEAD")
        return head["snapshot_id"]

    def _manifest(self,sid,query=None):
        if not valid_hash(sid):raise ValueError("Invalid memory snapshot")
        path=self.root/"manifests"/(sid+".json")
        if path.is_symlink():raise ValueError("Linked memory manifest")
        value=json.loads(path.read_bytes())
        if value.get("version") not in (1,2,3) or value.get("snapshot_id")!=sid:raise ValueError("Memory manifest identity mismatch")
        if value["version"] in (2,3):
            from .memory_index import validate
            validate(self,sid,value,query)
            return value
        index=self.root/"indexes"/(sid+".sqlite")
        if index.is_symlink() or digest(index.read_bytes())!=value["index_sha256"]:raise ValueError("Memory index SHA mismatch")
        snap=self.store.snapshot(sid) if query is None else query.snapshot(sid)
        if value["source_files"]!={p:{"bytes":e["size"],"sha256":e["sha256"]} for p,e in snap.files.items()}:
            raise ValueError("Memory manifest does not bind current CAS snapshot")
        return value

    def search(self,question,*,top_k=5,snapshot=None):
        if not isinstance(question,str) or not 1<=len(question)<=4096 or type(top_k) is not int or not 1<=top_k<=20:
            raise ValueError("Invalid memory query or top_k")
        from .memory_index import QueryResources
        with QueryResources(self) as query:
            return self._search(question,top_k,snapshot,query)

    def _search(self,question,top_k,snapshot,resources):
        started=time.perf_counter();sid=snapshot or self.current();manifest=self._manifest(sid,resources)
        tokens=list(dict.fromkeys(t.lower() for t in re.findall(r"[\w]+",question,re.UNICODE) if t.lower() not in STOP and len(t)>1))[:64]
        if not tokens:return {"snapshot_id":sid,"question":question,"hits":[],"wall_s":time.perf_counter()-started}
        query=" OR ".join('"'+t+'"' for t in tokens)
        if manifest["version"] in (2,3):
            from .memory_index import search
            rows=[(*r[:6],None,None,r[6]) for r in search(self,manifest,query,top_k,resources)]
        else:
            db=sqlite3.connect((self.root/"indexes"/(sid+".sqlite")).as_uri()+"?mode=ro",uri=True)
            try:
                rows=db.execute("SELECT key,path,offset,length,record_sha256,kind,title,body,bm25(evidence) FROM evidence WHERE evidence MATCH ? ORDER BY bm25(evidence),key LIMIT ?",(query,top_k)).fetchall()
            finally:db.close()
        hits=[]
        from .memory_index import snapshot as open_snapshot
        with open_snapshot(self,sid,resources) as snap:
            for key,path,offset,length,sha,kind,title,body,rank in rows:
                raw=snap.read_range(path,int(offset),int(length))
                if digest(raw)!=sha:raise ValueError("Retrieved original record SHA mismatch")
                parsed=list(records(path,raw))
                if len(parsed)!=1:raise ValueError("Evidence locator is not one record")
                actual_key,actual_title,sentences,_,_,actual_kind=parsed[0]
                if actual_key!=key or kind!=actual_kind or (manifest["version"]==1 and (title,body)!=(actual_title,"\n".join(sentences))):
                    raise ValueError("Index text differs from immutable evidence")
                title=actual_title
                hits.append({"citation_id":f"D{len(hits)}","key":key,"title":title,"sentences":sentences,"rank":rank,
                    "source_bytes_verified":True,"locator":{"snapshot_id":sid,"path":path,"offset":int(offset),"length":int(length),"sha256":sha}})
        return {"snapshot_id":sid,"question":question,"hits":hits,"wall_s":time.perf_counter()-started}

    def remember(self,record):
        """Persist derived output separately. It is never indexed as primary evidence."""
        raw=_json({**record,"record_type":"derived-model-answer","primary_evidence":False})
        key=digest(raw);path=self.root/"answers"/(key+".json")
        if not path.exists():_publish(path,raw)
        elif path.read_bytes()!=raw:raise ValueError("Derived record identity differs")
        return {"answer_id":key,"bytes":len(raw),"primary_evidence":False}

    def stats(self):
        groups={name:sum(path.stat().st_size for path,_ in files_in(self.root/name)) for name in ("cas","indexes","manifests","answers")}
        head=(self.root/"HEAD.json").stat().st_size if (self.root/"HEAD.json").exists() else 0
        return {"logical_file_bytes":sum(groups.values())+head,"by_directory_bytes":groups,"head_bytes":head,
                "cas":self.store.stats(),"snapshot_id":self.current() if head else None,
                "scope":"Includes all retained CAS objects, indexes, manifests and derived answers; excludes runtime/model/server and filesystem metadata"}

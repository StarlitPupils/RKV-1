"""Explicit, immutable paragraph-first lexical sidecar; never uses QA labels."""
import json
import os
from pathlib import Path
import re
import sqlite3
import time

from .core import digest, valid_hash
from .memory import STOP, _json
from .memory_index import QueryResources, parse_record, scan
from .memory_projection import fingerprint
from .memory_qasper import unique
from .store import _publish

FORMAT='rkv1-paragraph-ftsv1'


class ParagraphIndex:
    """A disposable, exact-snapshot sidecar, not a new Memory storage profile."""
    def __init__(self,root):
        self.root=Path(root).absolute()
        if self.root.is_symlink() or not self.root.is_dir():raise ValueError('Invalid paragraph index directory')
        for name in ('index.sqlite','manifest.json'):
            p=self.root/name
            if p.is_symlink() or not p.is_file():raise ValueError('Invalid paragraph index files')

    @classmethod
    def create(cls,memory,root,*,snapshot=None):
        """Build title-once and original paragraph units from all exact sources."""
        started=time.perf_counter();root=Path(root).absolute()
        resolved=root.resolve()
        if resolved.is_relative_to(memory.root) or memory.root.is_relative_to(resolved):
            raise ValueError('Paragraph index and Memory root must not overlap')
        sid=snapshot or memory.current()
        with QueryResources(memory) as resources:manifest=memory._manifest(sid,resources)
        current=scan(memory,sid)
        if len(current)!=manifest['records']:raise ValueError('Paragraph source record count differs from Memory')
        root.mkdir(parents=True,exist_ok=False)
        path=root/'index.sqlite';db=sqlite3.connect(path);units=0
        try:
            db.execute('CREATE TABLE papers(id INTEGER PRIMARY KEY,key TEXT UNIQUE NOT NULL,path TEXT NOT NULL,offset INTEGER NOT NULL,length INTEGER NOT NULL,sha BLOB NOT NULL,kind TEXT NOT NULL,projection BLOB NOT NULL)')
            db.execute('CREATE TABLE positions(id INTEGER PRIMARY KEY,parent INTEGER NOT NULL,sentence INTEGER NOT NULL)')
            db.execute("CREATE VIRTUAL TABLE terms USING fts5(title,body,content='',tokenize='porter unicode61')")
            for parent,(key,(meta,title,sentences)) in enumerate(sorted(current.items()),1):
                if key!=meta[0]:raise ValueError('Paragraph source key mismatch')
                db.execute('INSERT INTO papers VALUES(?,?,?,?,?,?,?,?)',(parent,*meta[:4],bytes.fromhex(meta[4]),meta[5],bytes.fromhex(fingerprint(title,sentences))))
                # A separate title row avoids duplicating the title per body row.
                for sentence,t,b in [(-1,title,''),*((i,'',s) for i,s in enumerate(sentences))]:
                    units+=1;db.execute('INSERT INTO positions VALUES(?,?,?)',(units,parent,sentence))
                    db.execute('INSERT INTO terms(rowid,title,body) VALUES(?,?,?)',(units,t,b))
            db.commit()
        finally:db.close()
        with path.open('r+b') as f:os.fsync(f.fileno())
        value={'format':FORMAT,'snapshot_id':sid,'index_sha256':digest(path.read_bytes()),'papers':len(current),
               'units':units,'source_files':manifest['source_files']}
        _publish(root/'manifest.json',_json(value))
        result=cls(root)
        return {'index':result,'snapshot_id':sid,'papers':len(current),'units':units,
                'logical_file_bytes':sum(p.stat().st_size for p in root.iterdir()),'wall_s':time.perf_counter()-started}

    def _validate(self,memory,sid,resources):
        # Recheck each query: no cross-query integrity or database cache.
        if self.root.is_symlink():raise ValueError('Linked paragraph index directory')
        for name in ('manifest.json','index.sqlite'):
            if (self.root/name).is_symlink():raise ValueError('Linked paragraph index')
        value=json.loads((self.root/'manifest.json').read_bytes(),object_pairs_hook=unique)
        if (set(value)!={'format','snapshot_id','index_sha256','papers','units','source_files'}
                or value['format']!=FORMAT or not valid_hash(value['snapshot_id'])
                or not valid_hash(value['index_sha256']) or type(value['papers']) is not int or value['papers']<1
                or type(value['units']) is not int or value['units']<value['papers']):
            raise ValueError('Invalid paragraph index manifest')
        if value['snapshot_id']!=sid:raise ValueError('Paragraph index snapshot mismatch; explicitly rebuild or select its retained snapshot')
        original=memory._manifest(sid,resources)
        if value['papers']!=original['records'] or value['source_files']!=original['source_files']:
            raise ValueError('Paragraph index source binding mismatch')
        if digest((self.root/'index.sqlite').read_bytes())!=value['index_sha256']:
            raise ValueError('Paragraph index SHA mismatch')
        return value

    def search(self,memory,question,*,top_k=20,snapshot=None):
        """Rank unique papers by their best title/body-unit BM25, without gold."""
        if not isinstance(question,str) or not 1<=len(question)<=4096 or type(top_k) is not int or not 1<=top_k<=20:
            raise ValueError('Invalid paragraph query or top_k')
        started=time.perf_counter();sid=snapshot or memory.current()
        with QueryResources(memory) as resources:
            value=self._validate(memory,sid,resources)
            tokens=list(dict.fromkeys(t.lower() for t in re.findall(r'[\w]+',question,re.UNICODE) if t.lower() not in STOP and len(t)>1))[:64]
            hits=[];winning=[]
            if tokens:
                match=' OR '.join('"'+t+'"' for t in tokens)
                db=sqlite3.connect((self.root/'index.sqlite').as_uri()+'?mode=ro',uri=True)
                try:
                    if db.execute('SELECT count(*) FROM papers').fetchone()[0]!=value['papers'] or db.execute('SELECT count(*) FROM positions').fetchone()[0]!=value['units']:
                        raise ValueError('Paragraph index count mismatch')
                    rows=db.execute('SELECT p.key,p.path,p.offset,p.length,lower(hex(p.sha)),p.kind,lower(hex(p.projection)),bm25(terms),u.sentence FROM terms JOIN positions u ON u.id=terms.rowid JOIN papers p ON p.id=u.parent WHERE terms MATCH ? ORDER BY bm25(terms),p.key,u.sentence',(match,))
                    seen=set()
                    for *meta,projection,rank,sentence in rows:
                        if meta[0] in seen:continue
                        _,title,body,_,_,_=parse_record(memory,sid,meta,resources)
                        if fingerprint(title,body)!=projection:raise ValueError('Paragraph projection differs from immutable source')
                        if type(sentence) is not int or not -1<=sentence<len(body):raise ValueError('Invalid paragraph source position')
                        seen.add(meta[0]);key,path,offset,length,sha,_=meta
                        hits.append({'citation_id':'D'+str(len(hits)),'key':key,'title':title,'sentences':body,'rank':rank,
                            'source_bytes_verified':True,'locator':{'snapshot_id':sid,'path':path,'offset':offset,'length':length,'sha256':sha}})
                        winning.append({'key':key,'sentence':sentence})
                        if len(hits)==top_k:break
                finally:db.close()
        return {'snapshot_id':sid,'question':question,'retriever':FORMAT,'hits':hits,'winning_source_units':winning,'wall_s':time.perf_counter()-started}

"""v4 paper-text fingerprints with exact current-member locator rebinding."""
from contextlib import contextmanager,closing
import os
from pathlib import Path
import sqlite3
import tempfile
import zlib

from .core import digest,valid_hash
from .store import _publish

PROFILE='compact-projection-v4'
PROJECTION='qasper-paper-text-v1'
MAX_REBINDINGS=4096
KIND='qasper-json-member-v1'


def fingerprint(title,sentences):
    from .memory import _json
    return digest(_json({'version':1,'title':title,'sentences':sentences}))


def update_locator(db,meta,rowid):
    db.execute('UPDATE locators SET path=?,offset=?,length=?,sha=?,kind=? WHERE rowid=?',
               (*meta[1:4],bytes.fromhex(meta[4]),meta[5],rowid))


def replay(memory,db,delta,*,query=None,deferred=False):
    from .memory_index import LOCATORS,parse_record,insert,relocate,relocation_ranges,moved
    if (set(delta)!={'version','parent_snapshot','snapshot_id','removed','upserted','relocations','rebound'}
            or delta['version']!=4 or not isinstance(delta['rebound'],list) or len(delta['rebound'])>MAX_REBINDINGS):
        raise ValueError('Invalid projection overlay')
    keys=[]
    for meta,sha in delta['rebound']:
        if (len(meta)!=6 or meta[5]!=KIND or not valid_hash(sha) or not valid_hash(meta[4])
                or not isinstance(meta[0],str) or not isinstance(meta[1],str)
                or type(meta[2]) is not int or meta[2]<0 or type(meta[3]) is not int or meta[3]<1):
            raise ValueError('Invalid projection rebinding')
        keys.append(meta[0])
    all_keys=delta['removed']+[m[0] for m in delta['upserted']]+keys
    if len(set(all_keys))!=len(all_keys):raise ValueError('Overlapping projection operations')
    for key in delta['removed']:
        old=db.execute('SELECT rowid,'+LOCATORS+' FROM locators WHERE key=?',(key,)).fetchone()
        if old is None:raise ValueError('Projection overlay removes absent record')
        _,title,body,_,_,_=parse_record(memory,delta['parent_snapshot'],old[1:],query)
        db.execute("INSERT INTO evidence(evidence,rowid,title,body) VALUES('delete',?,?,?)",(old[0],title,'\n'.join(body)))
        db.execute('DELETE FROM locators WHERE rowid=?',(old[0],));db.execute('DELETE FROM projections WHERE key=?',(key,))
    ranges={}
    if deferred:ranges=relocation_ranges(db,delta['relocations'])
    else:relocate(db,delta['relocations'])
    for meta in delta['upserted']:
        old=db.execute('SELECT rowid,'+LOCATORS+' FROM locators WHERE key=?',(meta[0],)).fetchone()
        if old and old[5]==meta[4]:
            update_locator(db,meta,old[0]);continue
        rowid=old[0] if old else None
        if old:
            _,title,body,_,_,_=parse_record(memory,delta['parent_snapshot'],moved(old[1:],ranges),query)
            db.execute("INSERT INTO evidence(evidence,rowid,title,body) VALUES('delete',?,?,?)",(rowid,title,'\n'.join(body)))
            db.execute('DELETE FROM locators WHERE rowid=?',(rowid,))
        _,title,body,_,_,_=parse_record(memory,delta['snapshot_id'],meta,query)
        insert(db,meta,title,body,rowid)
        db.execute('INSERT OR REPLACE INTO projections VALUES(?,?)',(meta[0],bytes.fromhex(fingerprint(title,body))))
    # Equality is checked against the fingerprint bound by the full base SHA.
    # Original bytes are scanned and verified at commit, and checked again for
    # each query hit. No FTS delete/insert or old/new CAS replay for these rows.
    for meta,sha in delta['rebound']:
        old=db.execute('SELECT l.rowid,l.kind,lower(hex(p.sha)) FROM locators l JOIN projections p ON p.key=l.key WHERE l.key=?',(meta[0],)).fetchone()
        if old is None or old[1]!=KIND or old[2]!=sha:raise ValueError('Projection rebinding fingerprint mismatch')
        update_locator(db,meta,old[0])
    db.commit()
    return ranges,{m[0] for m in delta['upserted']}|set(keys)


@contextmanager
def view(memory,value,*,writable=False,query=None,deferred=False):
    from .memory_index import load_delta
    path=memory.root/'indexes'/(value['base_snapshot_id']+'.sqlite')
    source=sqlite3.connect(path.as_uri()+'?mode=ro',uri=True);db=source
    try:
        projection=({},set())
        if value['deltas'] or writable:
            db=sqlite3.connect(':memory:');source.backup(db)
            for desc in value['deltas']:projection=replay(memory,db,load_delta(memory,desc,query),query=query,deferred=deferred)
        count=db.execute('SELECT count(*) FROM locators l JOIN projections p ON p.key=l.key').fetchone()[0]
        if count!=value['records'] or db.execute('SELECT count(*) FROM projections').fetchone()[0]!=count or db.execute('SELECT count(*) FROM locators').fetchone()[0]!=count:
            raise ValueError('Projection index record count mismatch')
        yield (db,projection) if deferred else db
    finally:
        if db is not source:db.close()
        source.close()


def build(memory,sid):
    from .memory import _json
    from .memory_budget import evaluate
    from .memory_index import scan,source_files,differences,configuration,LOCATORS,MAX_RELOCATIONS,MAX_DELTA_BYTES,schema,insert,validate
    current=scan(memory,sid);old=None;ops=None;meter=None;rebound=[]
    reason='initial' if not (memory.root/'HEAD.json').exists() else 'format-checkpoint'
    if (memory.root/'HEAD.json').exists():
        candidate=memory._manifest(memory.current())
        if candidate['version']==4:
            base=candidate['base_snapshot_id']
            with closing(sqlite3.connect((memory.root/'indexes'/(base+'.sqlite')).as_uri()+'?mode=ro',uri=True)) as db:
                prior={r[0]:list(r) for r in db.execute('SELECT '+LOCATORS+' FROM locators')}
                hashes=dict(db.execute('SELECT key,lower(hex(sha)) FROM projections'))
            removed,changed,moves=differences(prior,current);upserted=[]
            for meta in changed:
                before=prior.get(meta[0]);_,title,body=current[meta[0]]
                sha=fingerprint(title,body)
                if before and before[5]==meta[5]==KIND and hashes.get(meta[0])==sha:rebound.append([meta,sha])
                else:upserted.append(meta)
            reason=None
            if len(removed)+len(upserted)>max(1,len(prior)//4):reason='legacy-change-limit'
            elif len(moves)>MAX_RELOCATIONS:reason='relocation-limit'
            elif len(rebound)>MAX_REBINDINGS:reason='rebinding-limit'
            else:
                meter=evaluate(memory,base,sid,prior,removed,upserted,configuration(memory)['replay_budget'])
                if meter['reason']:reason='budget-'+meter['reason']
            if reason is None:
                old=candidate
                if removed or upserted or moves or rebound or source_files(memory,base)!=source_files(memory,sid):
                    ops={'version':4,'parent_snapshot':base,'snapshot_id':sid,'removed':removed,'upserted':upserted,'relocations':moves,'rebound':rebound}
    new_bytes=0
    if old is None:
        fd,temp=tempfile.mkstemp(prefix='.projection-index-',dir=memory.root/'indexes');os.close(fd)
        db=None
        try:
            db=sqlite3.connect(temp);schema(db)
            db.execute('CREATE TABLE projections(key TEXT PRIMARY KEY,sha BLOB NOT NULL CHECK(length(sha)=32))')
            for meta,title,body in current.values():
                insert(db,meta,title,body)
                db.execute('INSERT INTO projections VALUES(?,?)',(meta[0],bytes.fromhex(fingerprint(title,body))))
            db.commit();db.close();db=None
            with open(temp,'r+b') as stream:os.fsync(stream.fileno())
            raw=Path(temp).read_bytes();target=memory.root/'indexes'/(sid+'.sqlite')
            if target.exists():
                if target.is_symlink() or target.read_bytes()!=raw:raise ValueError('Projection orphan base identity differs')
            else:os.link(temp,target);new_bytes=len(raw)
            base=sid;sha=digest(raw);deltas=[]
        finally:
            if db is not None:db.close()
            if Path(temp).exists():Path(temp).unlink()
    else:
        base=old['base_snapshot_id'];sha=old['index_sha256'];deltas=[]
        if ops is not None:
            raw=_json(ops)
            if len(raw)>MAX_DELTA_BYTES:raise ValueError('Projection overlay too large')
            encoded=zlib.compress(raw,6);key=digest(encoded);target=memory.root/'indexes'/(key+'.delta')
            if not target.exists():_publish(target,encoded);new_bytes=len(encoded)
            elif target.read_bytes()!=encoded:raise ValueError('Projection overlay identity differs')
            deltas=[{'version':4,'sha256':key,'raw_bytes':len(raw),'parent_snapshot':base,'snapshot_id':sid}]
    value={'version':4,'projection':PROJECTION,'snapshot_id':sid,'base_snapshot_id':base,'index_sha256':sha,'deltas':deltas,
           'records':len(current),'source_files':source_files(memory,sid),'retriever':'SQLite FTS5 BM25, porter unicode61; v4 paper-text fingerprints and exact locator rebinding'}
    validate(memory,sid,value)
    with view(memory,value):pass
    _publish(memory.root/'manifests'/(sid+'.json'),_json(value))
    active=(memory.root/'indexes'/(base+'.sqlite')).stat().st_size+sum((memory.root/'indexes'/(d['sha256']+'.delta')).stat().st_size for d in deltas)
    return {'indexed_records':len(current),'index_bytes':active,'new_index_bytes':new_bytes,'index_reused':new_bytes==0,'delta_depth':len(deltas),'index_profile':PROFILE,
            'relocation_ranges':len(ops['relocations']) if ops else 0,'overlay_upserts':len(ops['upserted']) if ops else 0,
            'overlay_rebindings':len(ops['rebound']) if ops else 0,'checkpoint_reason':reason if old is None else None,'replay_budget':meter}


def search(memory,value,match,top_k,query=None):
    from .memory_index import moved
    with view(memory,value,query=query,deferred=True) as (db,(ranges,updated)):
        rows=db.execute('SELECT l.key,l.path,l.offset,l.length,lower(hex(l.sha)),l.kind,bm25(evidence),lower(hex(p.sha)) FROM evidence JOIN locators l ON l.rowid=evidence.rowid JOIN projections p ON p.key=l.key WHERE evidence MATCH ? ORDER BY bm25(evidence),l.key LIMIT ?',(match,top_k)).fetchall()
        return [(*moved(r[:6],ranges),*r[6:]) if r[0] not in updated else r for r in rows]

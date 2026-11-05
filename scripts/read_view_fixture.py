"""Owned three-revision source, independent of all original scientific inputs."""
import hashlib,json,os,time
from pathlib import Path

ROLES=('pinned','explicit','current')

def source(n,epoch):
    if type(n) is not int or n not in (9,17,129,513) or type(epoch) is not int or epoch not in (0,1,2):
        raise ValueError('Fixed owned sizes/revisions required')
    rows=[]
    for i in range(n):
        sentences=[f'RKV98PROBE revision{epoch} original evidence {i}.','Escaped 雪; same repeated.','Escaped 雪; same repeated.'] if i<4 else [f'Background {i}.']
        rows.append({'doc_id':i,'title':f'Owned revision{epoch} record {i}','abstract':sentences})
    return b''.join(json.dumps(r,ensure_ascii=True,sort_keys=True,separators=(',',':')).encode()+b'\r\n' for r in rows)

def sha(b):return hashlib.sha256(b).hexdigest()

def meta(p):
    raw=Path(p).read_bytes();return {'bytes':len(raw),'sha256':sha(raw)}

def ledger(root):return {p.relative_to(root).as_posix():meta(p) for p in Path(root).rglob('*') if p.is_file()}

def publish(path,v):
    path=Path(path);raw=(json.dumps(v,ensure_ascii=False,sort_keys=True,allow_nan=False)+'\n').encode()
    temporary=path.with_name('.'+path.name+'.tmp')
    with temporary.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
    temporary.rename(path)

def wait(path,deadline=None):
    end=time.monotonic()+45 if deadline is None else deadline
    while not Path(path).exists():
        if time.monotonic()>end:raise TimeoutError('Owned barrier timeout: '+Path(path).name)
        time.sleep(.005)
    return json.loads(Path(path).read_bytes())

def flatten(result):
    return result.get('hits') if 'hits' in result else [hit for group in result['results'] for hit in group['hits']]

def check_authorization(root,n):
    if n==9:return
    entries=sorted(Path(root).glob('AUTH-*.json'))
    if not entries:raise ValueError('Missing external ordinary quota evidence')
    v=json.loads(entries[-1].read_bytes());now=time.time()
    if (v.get('ordinaryUsageAllowed') is not True or type(v.get('usedPercent')) is not int
        or not 0<=v['usedPercent']<100 or type(v.get('authorized_reference')) is not int
        or type(v.get('server_resets_at')) is not int
        or abs(v['authorized_reference']-v['server_resets_at'])>60
        or not 0<=now-v.get('checked_at_epoch',0)<=30 or now>=v['authorized_reference']):
        raise ValueError('No current ordinary authorization; no later owned operation')

def check_result(memory,result,raw,sid,operation):
    if result['snapshot_id']!=sid:raise ValueError('Fixed/current SID differs')
    with memory.store.snapshot(sid) as snap:restored=snap.read_range('corpus.jsonl')
    if restored!=raw:raise ValueError('Whole source differs')
    records={};offset=0
    for line in raw.splitlines(keepends=True):
        obj=json.loads(line);records['doc:'+str(obj['doc_id'])]=(offset,line,obj);offset+=len(line)
    hits=flatten(result)
    keys=[h['key'] for h in hits]
    if operation=='search' and (len(keys)!=4 or set(keys)!={'doc:0','doc:1','doc:2','doc:3'}):raise ValueError('Probe set differs')
    if operation=='lookup' and keys!=['doc:2']:raise ValueError('Single lookup differs')
    if operation=='batch' and (keys!=['doc:0','doc:1','doc:0'] or [x['source_key'] for x in result['results']]!=keys):raise ValueError('Repeated batch occurrences differ')
    for h in hits:
        offset,line,obj=records[h['key']]
        if h['locator']!={'snapshot_id':sid,'path':'corpus.jsonl','offset':offset,'length':len(line),'sha256':sha(line)}:raise ValueError('Original locator differs')
        if h['title']!=obj['title'] or h['sentences']!=obj['abstract'] or h['source_bytes_verified'] is not True:raise ValueError('Original evidence differs')
    return {'whole_source_application_return_B':len(restored),'source_SHA':sha(restored),'record_occurrences':len(hits)}

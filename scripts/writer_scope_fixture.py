"""Owned source and bounded atomic barriers, never original scientific data."""
import hashlib,json,os,time
from pathlib import Path

PHASES=('before_HEAD','after_HEAD','clean_close')
def source(n,epoch):
    if type(n) is not int or n not in (9,17,129,513) or type(epoch) is not int or epoch not in (0,1,2):raise ValueError('Fixed owned sources required')
    rows=[{'doc_id':i,'title':f'Owned {i} revision {epoch}','abstract':[f'RKV99PROBE epoch{epoch} original evidence {i}.','Escaped 雪; duplicate.','Escaped 雪; duplicate.'] if i<4 else [f'Background {i}.']} for i in range(n)]
    return b''.join(json.dumps(r,ensure_ascii=True,sort_keys=True,separators=(',',':')).encode()+b'\r\n' for r in rows)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def meta(p):
    b=Path(p).read_bytes();return {'bytes':len(b),'sha256':sha(b)}
def ledger(root,held=False):
    return {p.relative_to(root).as_posix():({'bytes':p.stat().st_size,'sha256':None,'scope':'Kernel-exclusive lock content is intentionally unreadable while held on Windows'} if held and p.name=='.writer.lock' else meta(p)) for p in Path(root).rglob('*') if p.is_file()}
def publish(p,v):
    p=Path(p);raw=(json.dumps(v,ensure_ascii=False,sort_keys=True,allow_nan=False)+'\n').encode();tmp=p.with_name('.'+p.name+'.tmp')
    with tmp.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
    tmp.rename(p)
def wait(p,guard=None):
    end=time.monotonic()+30
    while not Path(p).exists():
        if guard:guard()
        if time.monotonic()>end:raise TimeoutError('Owned barrier timeout: '+Path(p).name)
        time.sleep(.005)
    return json.loads(Path(p).read_bytes())
def authorize(root,n):
    if n==9:return
    a=sorted(Path(root).glob('AUTH-*.json'))
    if not a:raise ValueError('Missing external ordinary authorization')
    v=json.loads(a[-1].read_bytes());now=time.time()
    if (v.get('ordinaryUsageAllowed') is not True or type(v.get('usedPercent')) is not int or not 0<=v['usedPercent']<100
        or type(v.get('reference')) is not int or type(v.get('server_resets_at')) is not int
        or abs(v['reference']-v['server_resets_at'])>60 or not 0<=now-v.get('checked_at_epoch',0)<=30 or now>=v['reference']):raise ValueError('No current ordinary authorization')
def verify(memory,result,raw,sid):
    if result['snapshot_id']!=sid:raise ValueError('Source SID differs')
    with memory.store.snapshot(sid) as snap:actual=snap.read_range('corpus.jsonl')
    if actual!=raw:raise ValueError('Whole original source differs')
    records={};offset=0
    for line in raw.splitlines(keepends=True):
        obj=json.loads(line)
        if obj['doc_id']<4:records['doc:'+str(obj['doc_id'])]=(offset,line,obj)
        offset+=len(line)
    if len(result['hits'])!=4 or {h['key'] for h in result['hits']}!=set(records):raise ValueError('Original probe set differs')
    for h in result['hits']:
        offset,line,obj=records[h['key']]
        if h['locator']!={'snapshot_id':sid,'path':'corpus.jsonl','offset':offset,'length':len(line),'sha256':sha(line)}:raise ValueError('Physical locator differs')
        if h['title']!=obj['title'] or h['sentences']!=obj['abstract'] or h['source_bytes_verified'] is not True:raise ValueError('Original text differs')
    return {'whole_source_application_return_B':len(actual),'original_source_SHA':sha(actual)}

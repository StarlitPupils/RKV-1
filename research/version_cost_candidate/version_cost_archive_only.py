"""Private original-byte, no-index archive workpoints. Not formal adopted baselines."""
import hashlib,io,json,os,re,tarfile
from pathlib import Path
import zstandard
PATHS=('README.md','docs/ROADMAP.md');MAX_FILE=512<<10;MAX_BUNDLE=32<<20
def sha(raw):return hashlib.sha256(raw).hexdigest()
def canonical(obj):return json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')
def save(path,raw):
    with Path(path).open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
def decoded(compressed,bound):
    declared=zstandard.frame_content_size(compressed)
    if declared!=zstandard.CONTENTSIZE_UNKNOWN and declared>bound:raise ValueError('Declared decoded size exceeds bound')
    with zstandard.ZstdDecompressor().stream_reader(io.BytesIO(compressed)) as f:
        raw=f.read(bound+1)
        if len(raw)>bound or f.read(1):raise ValueError('Decoded bound exceeded')
    return raw
def compress(raw):return zstandard.ZstdCompressor(level=3,write_content_size=True,write_checksum=True).compress(raw)

class ArchiveOnly:
    @classmethod
    def create(cls,root,kind):
        if kind not in ('full','solid','rkv'):raise ValueError('Unknown workpoint')
        root=Path(root).resolve();root.mkdir(exist_ok=False)
        for name in ('versions','generations','bundles','events'):(root/name).mkdir()
        if kind=='rkv':
            from rkv1.store import Store
            Store.create(root/'cas')
        save(root/'owner.json',canonical({'schema':'original-byte-owned-1','kind':kind}));return cls(root)
    def __init__(self,root):
        self.root=Path(root).resolve();owner=json.loads((self.root/'owner.json').read_bytes())
        if owner.get('schema')!='original-byte-owned-1' or owner.get('kind') not in ('full','solid','rkv'):raise ValueError('Wrong owned root')
        self.kind=owner['kind']
    def _catalog(self):
        if not (self.root/'HEAD').exists():return None
        head=json.loads((self.root/'HEAD').read_bytes());v=head['generation']
        if type(v) is not str or not re.fullmatch(r'v\d{3}',v):raise ValueError('Invalid version')
        raw=(self.root/'generations'/(v+'.json')).read_bytes()
        if sha(raw)!=head['sha256']:raise ValueError('Generation identity differs')
        cat=json.loads(raw);versions=cat['versions']
        if cat['kind']!=self.kind or not 1<=len(versions)<=12 or versions!=[f'v{i:03d}' for i in range(len(versions))] or versions[-1]!=v:raise ValueError('Sequence identity differs')
        return cat
    def _manifest(self,cat,v):
        if v not in cat['versions']:raise ValueError('Unknown logical version')
        raw=(self.root/'versions'/v/'manifest.json').read_bytes()
        if sha(raw)!=cat['manifests'][v]:raise ValueError('Manifest identity differs')
        m=json.loads(raw)
        if set(m['files'])!=set(PATHS):raise ValueError('Required original paths differ')
        return m
    def _solid(self,cat,selected=None):
        digest=cat['bundle_sha256']
        if not re.fullmatch('[0-9a-f]{64}',digest):raise ValueError('Bundle name')
        compressed=(self.root/'bundles'/(digest+'.zst')).read_bytes()
        if sha(compressed)!=digest:raise ValueError('Bundle identity differs')
        raw=decoded(compressed,MAX_BUNDLE);values={};expected={v+'/'+p for v in cat['versions'] for p in PATHS}
        with tarfile.open(fileobj=io.BytesIO(raw),mode='r:') as tar:
            members=tar.getmembers()
            if len(members)!=len(expected) or {m.name for m in members}!=expected or any(not m.isfile() or m.size>MAX_FILE for m in members):raise ValueError('Bundle membership differs')
            if selected is not None and not set(selected)<=expected:raise ValueError('Unknown selected original')
            manifests={}
            for member in members:
                if selected is not None and member.name not in selected:continue
                with tar.extractfile(member) as f:value=f.read(MAX_FILE+1)
                v,p=member.name.split('/',1)
                if v not in manifests:manifests[v]=self._manifest(cat,v)
                truth=manifests[v]['files'][p]
                if len(value)!=truth['bytes'] or sha(value)!=truth['sha256']:raise ValueError('Bundled original differs')
                values[member.name]=value
        return values
    def current(self):
        cat=self._catalog();return cat['versions'][-1] if cat else None
    def restore(self,version=None):
        cat=self._catalog()
        if cat is None:raise ValueError('No committed version')
        v=cat['versions'][-1] if version is None else version;m=self._manifest(cat,v)
        if self.kind=='solid':
            all_values=self._solid(cat,{v+'/'+p for p in PATHS});values={p:all_values[v+'/'+p] for p in PATHS}
        elif self.kind=='rkv':
            from rkv1.store import Store
            with Store(self.root/'cas').snapshot(m['snapshot_id']) as snap:values={p:snap.read_range(p) for p in PATHS}
        else:
            values={}
            for p in PATHS:
                compressed=(self.root/'versions'/v/(p+'.zst')).read_bytes()
                if sha(compressed)!=m['files'][p]['archive_sha256']:raise ValueError('Archive identity differs')
                values[p]=decoded(compressed,MAX_FILE)
        for p,raw in values.items():
            if len(raw)!=m['files'][p]['bytes'] or sha(raw)!=m['files'][p]['sha256']:raise ValueError('Original bytes differ')
        return values
    def read(self,path,version=None):
        if type(path) is not str or path.startswith(('/','\\')) or '\\' in path or any(p in ('..','.','') for p in path.split('/')) or ':' in path:raise ValueError('Unsafe path')
        cat=self._catalog()
        if cat is None:raise ValueError('No committed version')
        v=cat['versions'][-1] if version is None else version;m=self._manifest(cat,v)
        if path not in m['files']:return None
        if self.kind=='solid':return self._solid(cat,{v+'/'+path})[v+'/'+path]
        if self.kind=='rkv':
            from rkv1.store import Store
            with Store(self.root/'cas').snapshot(m['snapshot_id']) as snap:value=snap.read_range(path)
        else:
            compressed=(self.root/'versions'/v/(path+'.zst')).read_bytes()
            if sha(compressed)!=m['files'][path]['archive_sha256']:raise ValueError('Archive identity differs')
            value=decoded(compressed,MAX_FILE)
        if len(value)!=m['files'][path]['bytes'] or sha(value)!=m['files'][path]['sha256']:raise ValueError('Original identity differs')
        return value
    def append(self,version,source):
        if (self.root/'append.lock').exists():raise FileExistsError('Retained/inflight write;no replay')
        source=Path(source).resolve()
        if source.is_relative_to(self.root) or self.root.is_relative_to(source):raise ValueError('Input/store overlap')
        files={p.relative_to(source).as_posix():p for p in source.rglob('*') if p.is_file()}
        if set(files)!=set(PATHS) or any(p.is_symlink() or p.stat().st_size>MAX_FILE for p in files.values()):raise ValueError('Exact bounded original files required')
        values={p:files[p].read_bytes() for p in PATHS}
        if any(len(raw)>MAX_FILE for raw in values.values()):raise ValueError('Source grew')
        previous=self._catalog();versions=previous['versions'] if previous else []
        if version!=f'v{len(versions):03d}' or len(versions)>=12:raise ValueError('Next version required')
        m={'files':{p:{'bytes':len(raw),'sha256':sha(raw)} for p,raw in values.items()}}
        save(self.root/'append.lock',canonical({'version':version,'pid':os.getpid()}));phase='intent';success=False
        try:
            save(self.root/'events'/(version+'.intent.json'),canonical(m));folder=self.root/'versions'/version;folder.mkdir();(folder/'docs').mkdir()
            cat={'kind':self.kind,'versions':versions+[version],'manifests':dict(previous['manifests']) if previous else {}}
            if self.kind=='full':
                for p,raw in values.items():
                    compressed=compress(raw);save(folder/(p+'.zst'),compressed);m['files'][p]['archive_sha256']=sha(compressed)
            elif self.kind=='solid':
                all_values=self._solid(previous) if previous else {};all_values.update({version+'/'+p:raw for p,raw in values.items()});buffer=io.BytesIO()
                with tarfile.open(fileobj=buffer,mode='w',format=tarfile.USTAR_FORMAT) as tar:
                    for name,raw in sorted(all_values.items()):
                        info=tarfile.TarInfo(name);info.size=len(raw);info.mode=0o644;info.mtime=0;tar.addfile(info,io.BytesIO(raw))
                if buffer.tell()>MAX_BUNDLE:raise ValueError('Solid bound')
                compressed=compress(buffer.getvalue());digest=sha(compressed);save(self.root/'bundles'/(digest+'.zst'),compressed);cat['bundle_sha256']=digest
            else:
                from rkv1.store import Store
                store=Store(self.root/'cas');sid=store.add(source,label='')['snapshot_id'];m['snapshot_id']=sid
                with store.snapshot(sid) as snap:
                    if set(snap.files)!=set(PATHS) or any(snap.files[p]['size']!=m['files'][p]['bytes'] or snap.files[p]['sha256']!=m['files'][p]['sha256'] for p in PATHS):raise ValueError('Ingested original identity differs')
            raw=canonical(m);save(folder/'manifest.json',raw);cat['manifests'][version]=sha(raw);raw=canonical(cat);save(self.root/'generations'/(version+'.json'),raw);phase='staged'
            save(self.root/'.HEAD.tmp',canonical({'generation':version,'sha256':sha(raw)}));os.replace(self.root/'.HEAD.tmp',self.root/'HEAD');phase='HEAD_published';removed=[]
            if self.kind=='solid' and previous:
                digest=previous['bundle_sha256'];path=self.root/'bundles'/(digest+'.zst')
                if path.is_symlink() or path.resolve().parent!=(self.root/'bundles').resolve() or sha(path.read_bytes())!=digest:raise ValueError('Unsafe obsolete bundle')
                removed=[{'sha256':digest,'logical_B':path.stat().st_size}];save(self.root/'events'/(version+'.prune.json'),canonical(removed));path.unlink()
            receipt={'version':version,'phase':'stage_completed','deleted_bundles':removed,'external_exit_witness':False};save(self.root/'events'/(version+'.completed.json'),canonical(receipt));success=True
        except BaseException as exc:
            save(self.root/'events'/(version+'.failed.json'),canonical({'phase':phase,'error_type':type(exc).__name__,'returned_normally':False}));raise
        finally:
            if success:(self.root/'append.lock').unlink()
        return receipt

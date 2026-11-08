"""Isolated quota preflight. Synthetic blocking modes are ONLY fresh-owned controls."""
import sys
sys.dont_write_bytecode=True
import os,json,time,hashlib,subprocess,traceback
from pathlib import Path
work=Path(sys.argv[1]).resolve();spec_path=Path(sys.argv[2]).resolve()
def sha(raw):return hashlib.sha256(raw).hexdigest()
def file_sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for part in iter(lambda:f.read(1<<20),b''):h.update(part)
    return h.hexdigest()
def save(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as f:json.dump(obj,f,indent=2);f.flush();os.fsync(f.fileno())
if sys.argv[2]=='owned-pipe-server':
    save(work/'entry.json',{'pid':os.getpid(),'role':'synthetic-pipe-server'});time.sleep(30);raise RuntimeError('Owned pipe server was not stopped')
raw=spec_path.read_bytes();spec=json.loads(raw);success=False
save(work/'entry.json',{'pid':os.getpid(),'spec_sha256':sha(raw),'mode':spec['mode']})
try:
    frozen_raw=Path(spec['freeze_path']).read_bytes();assert sha(frozen_raw)==spec['freeze_sha256'];freeze=json.loads(frozen_raw)
    for path,item in freeze['absolute_files'].items():assert file_sha(path)==item['sha256'],path
    sys.path=list(freeze['path_roots']);sys.pycache_prefix=str(work/'unused-pycache-prefix')
    if spec['mode']=='official':
        import shutil
        cli=Path(shutil.which('codex')).resolve();assert str(cli)==freeze['quota_cli']['path'] and file_sha(cli)==freeze['quota_cli']['sha256']
        os.chdir(Path(spec['quota_script']).resolve().parent.parent)
        import version_cost_quota_guard as guard
        class HiddenSubprocess:
            def __getattr__(self,name):return getattr(subprocess,name)
            def Popen(self,*args,**kwargs):
                kwargs['creationflags']=kwargs.get('creationflags',0)|0x08000000
                si=kwargs.get('startupinfo') or subprocess.STARTUPINFO();si.dwFlags|=subprocess.STARTF_USESHOWWINDOW;si.wShowWindow=0;kwargs['startupinfo']=si
                return subprocess.Popen(*args,**kwargs)
        guard.subprocess=HiddenSubprocess();result=guard.read_official(spec['quota_script'])
        save(work/'result.json',{'pid':os.getpid(),'spec_sha256':sha(raw),'read_record':result,'official_reader_cwd':os.getcwd()});success=True
    elif spec['mode']=='owned-pipe-block':
        childdir=work/'server';childdir.mkdir();child=subprocess.Popen([sys.executable,'-I','-S',str(Path(__file__).resolve()),str(childdir),'owned-pipe-server'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
        save(work/'child.json',{'pid':child.pid});child.stdout.readline();raise RuntimeError('Synthetic pipe unexpectedly returned')
    elif spec['mode']=='owned-partial':
        save(work/'result.json',{'pid':os.getpid(),'spec_sha256':sha(raw),'read_record':{'summary':{'ordinaryUsageAllowed':True,'primary':{'usedPercent':1,'resetsAt':spec['authorized_reference']}}}});time.sleep(30)
    elif spec['mode']=='owned-exit76':os._exit(76)
    else:raise ValueError('Unknown owned preflight mode')
except BaseException as exc:
    save(work/'error.json',{'type':type(exc).__name__,'traceback':traceback.format_exc(),'guard_record':getattr(exc,'record',None)});raise
finally:save(work/'finally.json',{'success':success,'pid':os.getpid(),'spec_sha256':sha(raw)})

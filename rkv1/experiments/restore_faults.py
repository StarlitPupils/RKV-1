"""Test-only exception/forced-process-exit audit; no production failpoint flags."""
import argparse
from contextlib import ExitStack
import json
from pathlib import Path
import subprocess
import sys
import time
from unittest.mock import patch

from .. import persistence
from ..controlled import inventory
from ..core import pack,unpack,assert_tree_equal,valid_path,_file_digest

CASES=("normal-files","normal-close","write-first","flush-first","fsync-first","fsync-last",
       "close-first","publish-before","kill-after-sync","kill-before-publish","kill-after-publish")


def prepare(root,legacy):
    source=root/"source";source.mkdir(parents=True)
    (source/"0-empty").write_bytes(b"")
    (source/"nested").mkdir();(source/"nested/science.csv").write_bytes(b"1.00,2.000,-3e4\r\n"*2000)
    cards=["SIMPLE  =                    T","BITPIX  =                  -32","NAXIS   =                    2",
           "NAXIS1  =                 4000","NAXIS2  =                    1","END"]
    header=b"".join(c.ljust(80).encode() for c in cards).ljust(2880,b" ")
    image=bytes.fromhex("7fc12345 80000000 7f800000 00000001")*1000
    (source/"image.dat").write_bytes(header+image+b"~"*((-len(image))%2880))
    archives=[]
    for version,extra in ((2,{}),(3,{"unit_size":4096,"transform":"csv-columns-v1"}),
                          (4,{"transform":"byte-shuffle-4-v1"}),
                          (5,{"compression":"blosc-zstd-shuffle-4"}),
                          (6,{"layout":"fits-segments-v1","transform":"fits-byte-shuffle-v1"})):
        path=root/f"v{version}.rkv"
        pack(source,path,8192,format_version=version,**extra)
        archives.append((version,source,path))
    old=root/"legacy-source";old.mkdir()
    for name,raw in legacy["files_hex"].items():
        out=old.joinpath(*valid_path(name).parts);out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(bytes.fromhex(raw))
    path=root/"v1.rkv";path.write_bytes(bytes.fromhex(legacy["archive_hex"]))
    return [(1,old,path),*archives]


def injected(archive,source,root,case):
    root.mkdir();target=root/"final";events=[];fired=False;calls=0;fds={}
    real_open,real_sync,real_publish=Path.open,persistence.os.fsync,persistence.publish_directory
    files=len(inventory(source));result=None;error=None
    def failure(point):
        nonlocal fired
        if case==point and not fired:
            fired=True;events.append(["injected",point]);raise OSError("Injected "+point)
    class Output:
        def __init__(self,raw):self.raw=raw;self.name=raw.name;fds[raw.fileno()]=str(Path(self.name).relative_to(root))
        def __enter__(self):return self
        def __exit__(self,*_):self.close()
        def write(self,data):
            events.append(["write",fds[self.raw.fileno()]]);failure("write-first");return self.raw.write(data)
        def flush(self):
            events.append(["flush",fds[self.raw.fileno()]]);failure("flush-first");return self.raw.flush()
        def fileno(self):return self.raw.fileno()
        def close(self):
            name=fds[self.raw.fileno()];self.raw.close();events.append(["close",name]);failure("close-first")
    def opened(path,mode="r",*args,**kwargs):
        raw=real_open(path,mode,*args,**kwargs)
        return Output(raw) if mode=="xb" else raw
    def synced(fd):
        nonlocal calls
        calls+=1;events.append(["fsync",fds[fd]])
        if (case=="fsync-first" and calls==1) or (case=="fsync-last" and calls==files):failure(case)
        return real_sync(fd)
    def published(stage,destination):
        events.append(["publish-attempt"]);failure("publish-before")
        attempts=real_publish(stage,destination);events.append(["published"]);return attempts
    with ExitStack() as stack:
        stack.enter_context(patch.object(Path,"open",opened))
        stack.enter_context(patch.object(persistence.os,"fsync",synced))
        stack.enter_context(patch.object(persistence,"publish_directory",published))
        try:result=unpack(archive,target,sync_policy="close" if case=="normal-close" else "files")
        except OSError as exc:error=str(exc)
    normal=case.startswith("normal-")
    assert (error is None)==normal and target.exists()==normal
    if normal:
        assert_tree_equal(source,target)
        assert result["files_synced"]==calls==(0 if case=="normal-close" else files)
        if case=="normal-files":
            publish=next(i for i,e in enumerate(events) if e[0]=="published")
            for name in {e[1] for e in events if e[0]=="fsync"}:
                positions={kind:next(i for i,e in enumerate(events) if e==[kind,name]) for kind in ("flush","fsync","close")}
                assert positions["flush"]<positions["fsync"]<positions["close"]<publish
    else:assert fired and not list(root.glob(".rkv-extract-*"))
    return {"case":case,"target_present":target.exists(),"bytewise_verified":normal,
            "injected_error_observed":not normal,"fsync_attempts":calls,"events":events,"result":result}


def child(archive,target,ready,point):
    original_finish=persistence.finish_file;original_publish=persistence.publish_directory;count=0
    def checkpoint():
        pending=ready.with_suffix(".pending")
        pending.write_text(json.dumps({"point":point,"files_synced":count}),encoding="utf-8")
        pending.replace(ready)
        while True:time.sleep(1)
    def finish(stream,policy):
        nonlocal count
        value=original_finish(stream,policy);count+=value
        if point=="kill-after-sync" and count==1:checkpoint()
        return value
    def publish(stage,destination):
        if point=="kill-before-publish":checkpoint()
        original_publish(stage,destination)
        if point=="kill-after-publish":checkpoint()
    persistence.finish_file=finish;persistence.publish_directory=publish
    unpack(archive,target,sync_policy="files")
    raise AssertionError("Checkpoint was not reached")


def killed(archive,source,root,case):
    root.mkdir();target=root/"final";ready=root/"checkpoint.json"
    command=[sys.executable,"-m",__name__,"--child",str(archive),str(target),str(ready),case]
    # __name__ is not a usable module name when the parent itself ran as -m.
    command[2]="rkv1.experiments.restore_faults"
    process=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    try:
        deadline=time.monotonic()+15
        while not ready.exists():
            if process.poll() is not None:
                raise AssertionError(process.communicate()[1].decode("utf-8","replace"))
            if time.monotonic()>deadline:raise TimeoutError("Fault checkpoint did not arrive")
            time.sleep(.01)
        signal=json.loads(ready.read_text("utf-8"))
        process.kill();process.communicate(timeout=10)
    finally:
        if process.poll() is None:process.kill();process.communicate(timeout=10)
    committed=case=="kill-after-publish"
    assert signal["files_synced"]==(1 if case=="kill-after-sync" else len(inventory(source)))
    assert target.exists()==committed
    if committed:assert_tree_equal(source,target)
    assert list(root.glob(".rkv-extract-*")),"Forced termination should leave private staging residue"
    return {"case":case,"checkpoint":signal,"exit_code":process.returncode,"target_present":target.exists(),
            "bytewise_verified":committed,"private_staging_left":True,
            "scope":"Forced child process termination, not power failure. Post-publish target may be complete without a success response."}


def campaign(root,legacy,*,repetitions=3):
    root=Path(root).resolve();root.mkdir(parents=True,exist_ok=False)
    records=[]
    for version,source,archive in prepare(root,legacy):
        sha=_file_digest(archive)
        for repetition in range(repetitions):
            for case in CASES:
                out=root/f"v{version}-{repetition}-{case}"
                record=(killed if case.startswith("kill-") else injected)(archive,source,out,case)
                assert _file_digest(archive)==sha
                records.append({"format":version,"repetition":repetition,"archive_sha256":sha,**record})
    return {"records":records,"formats":[1,2,3,4,5,6],"repetitions":repetitions,"cases_per_format":len(CASES),
            "all_expected_outcomes_verified":True,"power_failure_tested":False,"directory_fsync":False,
            "automatic_orphan_recovery":False,"concurrent_untrusted_writer_tested":False}


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--child",nargs=4,required=True);args=p.parse_args()
    child(*[Path(x) for x in args.child[:3]],args.child[3])

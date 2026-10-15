"""Run the frozen cross-domain and text-control byte-shuffle campaign."""
import argparse
import hashlib
import os
from pathlib import Path
import platform
import sys

from rkv1.controlled import implementation_checksums,runtime_footprint
from rkv1.crossdomain_data import fetch
from rkv1.crossdomain_benchmark import crossdomain_benchmark
from rkv1.numeric_data import fetch as numeric,noise
from rkv1.read_benchmark import timestamp
from scripts.run_units import save

DATASETS=("seismic","molecular","python","latex","ecg","noise")


def resource():
    raw=Path("rkv1/numeric.py").read_bytes()
    return {"name":"numeric.py","bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest(),
            "native_bytes":0,"model_bytes":0,"dictionary_bytes":0,
            "basis":"Whole dedicated transform source once, including candidate fallback; common Python/core/codecs/pyc not fully allocated"}


def main():
    p=argparse.ArgumentParser();p.add_argument("--out",type=Path,required=True)
    p.add_argument("--scratch",type=Path,default=Path(".tools/crossdomain-scratch"))
    args=p.parse_args();args.out.mkdir(parents=True,exist_ok=False)
    args.scratch=args.scratch.resolve();args.scratch.mkdir(parents=True,exist_ok=True)
    checks=implementation_checksums();cost=resource()
    save(args.out/"numeric-resource.json",cost)
    save(args.out/"environment.json",{"python":platform.python_version(),"platform":platform.platform(),
        "logical_cpus":os.cpu_count(),"executable":sys.executable,"started_utc":timestamp(),"scratch":str(args.scratch)})
    for name in DATASETS:
        provenance=fetch("data/crossdomain",name) if name not in ("ecg","noise") else numeric("data/numeric",name) if name=="ecg" else noise("data/numeric")
        provenance.setdefault("partition","Previously seen ECG control" if name=="ecg" else "Synthetic fallback control")
        width=2 if name=="ecg" else 4
        save(args.out/f"{name}-provenance.json",provenance)
        save(args.out/f"{name}-crossdomain.json",crossdomain_benchmark(provenance["source"],width,scratch=args.scratch,
             journal=args.out/f"{name}-journal.jsonl"))
    if checks!=implementation_checksums() or cost!=resource():raise ValueError("Measured source changed")
    if "blosc" in sys.modules:raise ValueError("Unexpected Blosc dependency")
    save(args.out/"source-checksums.json",checks);save(args.out/"runtime-footprint.json",runtime_footprint())


if __name__=="__main__":main()

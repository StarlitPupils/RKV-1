"""Frozen FITS routing, new validation records and unchanged fallback controls."""
import argparse
import hashlib
import os
from pathlib import Path
import platform
import sys

from rkv1.controlled import implementation_checksums,runtime_footprint
from rkv1.scientific_data import fetch as development
from rkv1.layout_data import fetch
from rkv1.numeric_data import fetch as numeric,noise
from rkv1.layout_benchmark import layout_benchmark
from rkv1.read_benchmark import timestamp
from scripts.run_units import save


def sources():
    return [{"name":name,"bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest()}
            for name in ("layouts.py","numeric.py") for raw in [Path("rkv1",name).read_bytes()]]


def main():
    p=argparse.ArgumentParser();p.add_argument("--out",type=Path,required=True)
    p.add_argument("--rounds",type=int,default=5);p.add_argument("--queries",type=int,default=32)
    args=p.parse_args();args.out.mkdir(parents=True,exist_ok=False)
    checks=implementation_checksums();dedicated=sources()
    save(args.out/"dedicated-resources.json",{"sources":dedicated,"native_bytes":0,"model_bytes":0,"dictionary_bytes":0,
         "basis":"Whole dedicated source allocation once; no Blosc/RKV Rust. Common Python/core/Zstd and pyc not fully allocated; not complete deployment size."})
    save(args.out/"environment.json",{"python":platform.python_version(),"platform":platform.platform(),
        "logical_cpus":os.cpu_count(),"executable":sys.executable,"started_utc":timestamp()})
    for name,width in (("spitzer32",4),("m13_64",8),("rosat32",4),("ecg",2),("noise",4)):
        provenance=(development("data/scientific",name) if name=="spitzer32" else
                    fetch("data/layout",name) if name in ("m13_64","rosat32") else
                    numeric("data/numeric",name) if name=="ecg" else noise("data/numeric"))
        provenance.setdefault("partition","Development" if name=="spitzer32" else "Unrecognized-format control")
        save(args.out/f"{name}-provenance.json",provenance)
        save(args.out/f"{name}-layout.json",layout_benchmark(provenance["source"],width,rounds=args.rounds,queries=args.queries))
    if checks!=implementation_checksums() or dedicated!=sources():raise ValueError("Measured source changed")
    if "blosc" in sys.modules:raise ValueError("Unexpected professional dependency loaded")
    save(args.out/"source-checksums.json",checks);save(args.out/"runtime-footprint.json",runtime_footprint())


if __name__=="__main__":main()

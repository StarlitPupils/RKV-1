"""Frozen floating FITS, prior int16 and noise controls with C-Blosc baselines."""
import argparse
import os
from pathlib import Path
import platform

from rkv1.controlled import implementation_checksums,runtime_footprint
from rkv1.numeric_data import fetch as fetch_numeric,noise
from rkv1.scientific_data import fetch as fetch_fits
from rkv1.scientific_benchmark import scientific_benchmark
from rkv1.scientific_resources import resources
from rkv1.read_benchmark import timestamp
from scripts.run_units import save


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--data",type=Path,default=Path("data/scientific"))
    parser.add_argument("--numeric-data",type=Path,default=Path("data/numeric"))
    parser.add_argument("--out",type=Path,required=True)
    parser.add_argument("--rounds",type=int,default=5)
    parser.add_argument("--queries",type=int,default=32)
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=False)
    checks=implementation_checksums();before=resources()
    save(args.out/"dependency-provenance.json",before)
    save(args.out/"environment.json",{"python":platform.python_version(),"platform":platform.platform(),
        "logical_cpus":os.cpu_count(),"recorded_utc":timestamp(),"executable":str(Path(os.sys.executable).resolve()),
        "numpy_imported":before["numpy_imported"]})
    for name,width in (("spitzer32",4),("bolocam32",4),("msx64",8),("ecg",2),("noise",4)):
        provenance=(fetch_numeric(args.numeric_data,name) if name=="ecg" else noise(args.numeric_data)
                    if name=="noise" else fetch_fits(args.data,name))
        save(args.out/f"{name}-provenance.json",provenance)
        save(args.out/f"{name}-scientific.json",scientific_benchmark(provenance["source"],width,
            rounds=args.rounds,queries=args.queries))
    if checks!=implementation_checksums() or before!=resources():raise ValueError("Source/dependency changed during scientific campaign")
    save(args.out/"source-checksums.json",checks)
    save(args.out/"runtime-footprint.json",runtime_footprint())


if __name__=="__main__":main()

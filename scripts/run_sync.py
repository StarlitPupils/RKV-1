"""Public original records plus explicit synthetic file-count sync control."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import tempfile

from rkv1.controlled import implementation_checksums,inventory,runtime_footprint
from rkv1.numeric_data import fetch,noise
from rkv1.layout_data import fetch as fits
from rkv1.sync_benchmark import measure
from rkv1.experiments.restore_faults import campaign
from scripts.run_units import save


def fanout(root):
    p=noise("data/numeric");raw=(Path(p["source"])/"seeded-noise.bin").read_bytes()
    expected={f"shards/{i//2048:03d}.bin":raw[i:i+2048] for i in range(0,len(raw),2048)};expected["empty"]=b""
    root=Path(root).resolve()
    if not root.exists():
        root.parent.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".fanout-",dir=root.parent) as temp:
            stage=Path(temp)/"data";stage.mkdir()
            for name,data in expected.items():
                path=stage/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
            if not stage.resolve().is_relative_to(root.parent):raise ValueError("Invalid fanout stage")
            stage.rename(root)
    files=inventory(root)
    assert files==[{"path":n,"bytes":len(b),"sha256":hashlib.sha256(b).hexdigest()} for n,b in sorted(expected.items())]
    return {"source":str(root),"files":files,"scope":"Synthetic file-count control: unchanged deterministic noise cut into 129 consecutive <=2048-byte files plus one empty file, not a scientific corpus"}


def main():
    p=argparse.ArgumentParser();p.add_argument("--out",type=Path,required=True)
    p.add_argument("--scratch",type=Path,default=Path(".tools/sync-scratch"));p.add_argument("--rounds",type=int,default=10)
    args=p.parse_args();args.out.mkdir(parents=True,exist_ok=False);checks=implementation_checksums()
    ecg=fetch("data/numeric","ecg");m13=fits("data/layout","m13_64");many=fanout("data/sync-fanout")
    save(args.out/"input-provenance.json",{"ecg":ecg,"m13":m13,"fanout":many})
    base={"compression":"zstd","chunk_size":1048576,"format_version":4}
    cases=[{"name":"ecg-v4","source":ecg["source"],"pack":{**base,"compression":"zlib","transform":"byte-shuffle-2-v1"}},
           {"name":"m13-v4","source":m13["source"],"pack":{**base,"transform":"byte-shuffle-8-v1"}},
           {"name":"m13-v6","source":m13["source"],"pack":{"chunk_size":65536,"compression":"zstd","format_version":6,"layout":"fits-segments-v1","transform":"fits-byte-shuffle-v1"}},
           {"name":"fanout-v2","source":many["source"],"pack":{"chunk_size":65536,"compression":"zlib","format_version":2}}]
    save(args.out/"restore-sync.json",measure(cases,args.scratch,rounds=args.rounds))
    legacy=json.loads(Path("tests/fixtures/v1.json").read_text("utf-8"))
    with tempfile.TemporaryDirectory(prefix="rkv-fault-",dir=args.scratch.resolve()) as temp:
        save(args.out/"fault-audit.json",campaign(Path(temp)/"cases",legacy,repetitions=3))
    assert checks==implementation_checksums();save(args.out/"source-checksums.json",checks)
    source=Path("rkv1/persistence.py").read_bytes()
    save(args.out/"resource.json",{"persistence_source_bytes":len(source),"persistence_source_sha256":hashlib.sha256(source).hexdigest(),
         "extra_native_bytes":0,"model_bytes":0,"dictionary_bytes":0,"basis":"Whole persistence.py source; archive bytes unchanged. Common Python/core/codecs incomplete, not full deployment size."})
    save(args.out/"environment.json",{"python":platform.python_version(),"platform":platform.platform(),"runtime":runtime_footprint()})


if __name__=="__main__":main()

"""Full recorded dependency identity, separate from common runtime allocation."""
import hashlib
import importlib.metadata
from pathlib import Path
import sys

from .blosc_codec import configured


def resources():
    lib=configured()
    distributions=[]
    for name in ("blosc","numpy"):
        if name=="numpy" and "numpy" not in sys.modules:continue
        dist=importlib.metadata.distribution(name)
        files=[]
        for relative in sorted(dist.files or [],key=str):
            path=dist.locate_file(relative)
            if path.is_file():
                raw=path.read_bytes()
                files.append({"path":str(relative).replace("\\","/"),"bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest()})
        distributions.append({"name":name,"version":dist.version,"installed_bytes":sum(f["bytes"] for f in files),"files":files})
    sources=[]
    for name in ("numeric.py","blosc_codec.py"):
        raw=Path(__file__).with_name(name).read_bytes()
        sources.append({"name":name,"bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest()})
    return {"dependencies":distributions,"total_recorded_dependency_bytes":sum(d["installed_bytes"] for d in distributions),
        "dedicated_sources":sources,"dedicated_source_bytes":sum(s["bytes"] for s in sources),
        "blosc_version":lib.__version__,"c_blosc_version":lib.blosclib_version,"embedded_codec_versions":lib.clib_versions,
        "numpy_imported": "numpy" in sys.modules,"threads":1,"internal_block_bytes":65536,"clevel":3,
        "model_bytes":0,"dictionary_bytes":0,
        "basis":"Entire installed Blosc distribution, including unused embedded codecs and metadata; optional NumPy if imported. Separate dedicated Python source scenario. Not a complete deployment: shared Python/core/Zstd and external linked/OS libraries not fully allocated."}

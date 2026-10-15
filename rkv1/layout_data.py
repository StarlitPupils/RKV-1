"""Pinned new FITS validation records, untouched original file bytes."""
import hashlib
from pathlib import Path
import tempfile
from urllib.request import urlopen

from .controlled import inventory
from .scientific_data import BASE, COMMIT, primary_layout

SPECS={
    "m13_64":("tutorials/FITS-images/stacked_M13_blue.fits",11586240,
              "951a62d97211b90e85fb0379686043a0d090a6973dd14af185d3474b986710f0"),
    "rosat32":("allsky/allsky_rosat.fits",478080,
               "22b77adc0bcb3c344593777b7d998361c0ea9355552bd7deb82f814e709a91b3")}


def fetch(root,dataset):
    root=Path(root).resolve();root.mkdir(parents=True,exist_ok=True)
    relative,size,sha=SPECS[dataset];out=root/dataset;name=Path(relative).name
    if not out.exists():
        with tempfile.TemporaryDirectory(prefix=".layout-",dir=root) as temp:
            stage=Path(temp)/"input";stage.mkdir()
            with urlopen(BASE+relative,timeout=60) as f:raw=f.read((16<<20)+1)
            if len(raw)!=size or hashlib.sha256(raw).hexdigest()!=sha:raise ValueError("FITS validation source pin mismatch")
            (stage/name).write_bytes(raw)
            if not stage.resolve().is_relative_to(root) or not out.resolve().is_relative_to(root):raise ValueError("Invalid input path")
            stage.rename(out)
    files=inventory(out)
    if files!=[{"path":name,"bytes":size,"sha256":sha}]:raise ValueError("FITS validation input changed")
    return {"dataset":dataset,"source":str(out),"files":files,"source_commit":COMMIT,"url":BASE+relative,
            "repository_path":relative,"layout":primary_layout((out/name).read_bytes()),
            "partition":"New record validation; not used to choose routing rules or compression parameters",
            "rights":"Public Astropy example mirror; provider attribution retained in original FITS. No blanket data license assumed; raw file excluded from releases.",
            "limits":"Astronomy examples from the same hosting project; not cross-domain or strict blind evaluation"}

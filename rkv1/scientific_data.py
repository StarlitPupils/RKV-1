"""Pinned complete floating FITS examples; inspect bits, never rewrite values."""
import hashlib
from pathlib import Path
import struct
import tempfile
from urllib.request import urlopen

from .controlled import inventory

COMMIT = "1b964d39b378390b24c58fb5633cef238d22a35a"
BASE = f"https://raw.githubusercontent.com/astropy/astropy-data/{COMMIT}/"
SPECS = {
    "spitzer32": ("photometry/spitzer_example_image.fits", 2113920,
        "4b9cf15419de311fc683a9c378327a0b28bfee29d01e4fdbb9dc5780417f7ebc", -32, (1025,513)),
    "bolocam32": ("galactic_center/gc_bolocam_gps.fits", 1644480,
        "f442e8a6499c461048f8e74fa780dd2098e6e6c9522e8571fffcc8063d0708a9", -32, (640,638)),
    "msx64": ("galactic_center/gc_msx_e.fits", 181440,
        "3687fb3763911825f981e74b6a9b82c0e618f7e592b1e0cb17e2c63164e28cd6", -64, (149,149))}


def primary_layout(raw):
    """Inspect our small uncompressed primary 2D images, not a general FITS parser."""
    if len(raw)%2880 or not raw.startswith(b"SIMPLE  =                    T"):
        raise ValueError("Unsupported FITS primary header")
    keys={};end=None
    for start in range(0,min(len(raw),1<<20),80):
        card=raw[start:start+80];key=card[:8].decode("ascii").strip()
        if key=="END":end=start+80;break
        if key in ("BITPIX","NAXIS","NAXIS1","NAXIS2"):
            if key in keys or card[8:10]!=b"= ":raise ValueError("Duplicate/malformed FITS dimension")
            keys[key]=int(card[10:].split(b"/",1)[0])
    if end is None or set(keys)!={"BITPIX","NAXIS","NAXIS1","NAXIS2"}:
        raise ValueError("Missing FITS dimensions")
    if keys["BITPIX"] not in (-32,-64) or keys["NAXIS"]!=2 or not all(1<=keys[k]<=100000 for k in ("NAXIS1","NAXIS2")):
        raise ValueError("Unsupported floating FITS dimensions")
    offset=(end+2879)//2880*2880;width=-keys["BITPIX"]//8
    size=keys["NAXIS1"]*keys["NAXIS2"]*width
    if offset+(size+2879)//2880*2880!=len(raw):raise ValueError("Unexpected FITS image/extension size")
    mantissa,exponent=(23,8) if width==4 else (52,11)
    mask=((1<<exponent)-1)<<mantissa
    counts={"nan_words":0,"infinite_words":0,"positive_zero_words":0,"negative_zero_words":0}
    for (bits,) in struct.iter_unpack(">I" if width==4 else ">Q",raw[offset:offset+size]):
        if bits&mask==mask:
            counts["nan_words" if bits&((1<<mantissa)-1) else "infinite_words"]+=1
        elif bits==0:counts["positive_zero_words"]+=1
        elif bits==1<<(8*width-1):counts["negative_zero_words"]+=1
    return {"bitpix":keys["BITPIX"],"fits_axes":[keys["NAXIS1"],keys["NAXIS2"]],"byteorder":"big",
            "word_bytes":width,"header_bytes":offset,"image_bytes":size,"image_words":size//width,
            "padding_bytes":len(raw)-offset-size,**counts,
            "scope":"Bit-pattern census of the primary image only; entire original FITS remains the benchmark truth"}


def fetch(root,dataset):
    root=Path(root).resolve();root.mkdir(parents=True,exist_ok=True)
    source,size,sha,bitpix,axes=SPECS[dataset]
    output=root/dataset;name=Path(source).name
    if not output.exists():
        with tempfile.TemporaryDirectory(prefix=".fits-",dir=root) as temp:
            stage=Path(temp)/"source";stage.mkdir()
            with urlopen(BASE+source,timeout=60) as stream:raw=stream.read((8<<20)+1)
            if len(raw)!=size or hashlib.sha256(raw).hexdigest()!=sha:raise ValueError("Pinned FITS SHA/size mismatch")
            (stage/name).write_bytes(raw)
            if not stage.resolve().is_relative_to(root) or not output.resolve().is_relative_to(root):raise ValueError("Invalid FITS stage path")
            stage.rename(output)
    files=inventory(output)
    if files!=[{"path":name,"bytes":size,"sha256":sha}]:raise ValueError("Existing FITS input differs from pin")
    layout=primary_layout((output/name).read_bytes())
    if layout["bitpix"]!=bitpix or tuple(layout["fits_axes"])!=axes:raise ValueError("Pinned FITS layout changed")
    return {"dataset":dataset,"source":str(output),"files":files,"source_commit":COMMIT,
        "url":BASE+source,"repository_path":source,"layout":layout,
        "source_page":"https://www.astropy.org/astropy-data/",
        "rights":"Public Astropy example mirror; provider attribution retained in original FITS header. No blanket repository data license assumed; raw files not redistributed by RKV releases.",
        "scope":"One complete original FITS example file; headers/padding/NaN payloads retained, no float conversion or scaling"}

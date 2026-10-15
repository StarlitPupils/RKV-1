"""Pinned complete distributed examples; never repair or reserialize source bytes."""
import hashlib
from pathlib import Path
import struct
import tempfile
from urllib.request import urlopen

from .controlled import inventory

SPECS = {
    "seismic": {"repo":"obspy/obspy", "commit":"a629e8c021052904b6b8d62699d03f2a3721ae63",
        "path":"obspy/signal/tests/data/CRLZ.HHZ.10.NZ.SAC", "bytes":131704,
        "sha256":"c9011fd76050172e06ec067da99e06b40abad173dcdf2f80e3e343b64639127a",
        "role":"New geophysics example; largest .sac in pinned ObsPy tree, chosen by size before compression",
        "license":"Upstream ObsPy LGPL-3.0 repository; retain original provenance; raw file not redistributed"},
    "molecular": {"repo":"MDAnalysis/mdanalysis", "commit":"51b8271d254ec5ce43e0daf8c33952147f2b2d3c",
        "path":"testsuite/MDAnalysisTests/data/adk_dims.dcd", "bytes":3931724,
        "sha256":"859a5bd9e7de45a0f2401f7971c5ffc296168e7c23f6f65382bde7c1686c19f1",
        "role":"New molecular-dynamics example; canonical adk_dims test trajectory, not a full simulation campaign",
        "license":"Upstream MDAnalysis LGPL-3.0-or-later library distribution with component licenses; fixture grant not separately asserted; raw file not redistributed"},
    "python": {"repo":"scipy/scipy", "commit":"e29dcb65a2040f04819b426a04b60d44a8f69c04",
        "path":"scipy/integrate/_ivp/rk.py", "bytes":22800,
        "sha256":"fa5d6300917f4f949e699b116f59ae147159d5c6147d55d940dc9d3303891056",
        "role":"Non-numeric control: complete SciPy Runge-Kutta Python source; no AST transform or execution",
        "license":"SciPy BSD-3-Clause; original repository license applies"},
    "latex": {"repo":"latex3/latex2e", "commit":"04688cfadaddae62cdaf0530e4ffa7ec5a19cc82",
        "path":"required/amsmath/testmath.tex", "bytes":81184,
        "sha256":"9b311f1835266833ad40130e7a7a6361a950c965d308c02d567361e72ce74aa5",
        "role":"Non-numeric control: complete amsmath example/test source; no token/AST transform or compilation",
        "license":"LPPL-1.3c, as recorded in the original header"}}


def word_census(raw):
    if len(raw)%4:raise ValueError("Unaligned diagnostic float32 payload")
    result={"words":len(raw)//4,"nan_words":0,"infinity_words":0,"positive_zero_words":0,"negative_zero_words":0}
    for (word,) in struct.iter_unpack("<I",raw):
        exponent=word&0x7f800000;fraction=word&0x7fffff
        result["nan_words"]+=int(exponent==0x7f800000 and fraction!=0)
        result["infinity_words"]+=int(exponent==0x7f800000 and fraction==0)
        result["positive_zero_words"]+=int(word==0)
        result["negative_zero_words"]+=int(word==0x80000000)
    return result


def diagnostics(dataset,raw):
    """Untimed provenance only, not an encoder router or semantic decoder."""
    if dataset=="seismic":
        if len(raw)<632:raise ValueError("Short SAC example")
        version=struct.unpack_from("<i",raw,304)[0];npts=struct.unpack_from("<i",raw,316)[0]
        if version!=6 or npts<0 or len(raw)!=632+4*npts:raise ValueError("Unexpected pinned SAC structure")
        return {"format":"SAC v6 little-endian", "header_bytes":632,"stored_samples":npts,
                "payload_float32_census":word_census(raw[632:])}
    if dataset=="molecular":
        records=[];cursor=0
        while cursor<len(raw):
            if cursor+8>len(raw):raise ValueError("Short DCD record")
            n=struct.unpack_from("<I",raw,cursor)[0];end=cursor+4+n
            if end+4>len(raw) or struct.unpack_from("<I",raw,end)[0]!=n:raise ValueError("DCD record markers differ")
            records.append(raw[cursor+4:end]);cursor=end+4
        if len(records)<3 or len(records[0])!=84 or records[0][:4]!=b"CORD" or len(records[2])!=4:
            raise ValueError("Unexpected pinned DCD header")
        atoms=struct.unpack("<I",records[2])[0];axes=records[3:]
        if len(axes)%3 or any(len(r)!=atoms*4 for r in axes):raise ValueError("Unexpected pinned DCD axes")
        return {"format":"Little-endian DCD CORD; three float32 coordinate axes per stored frame",
                "atoms":atoms,"header_declared_frames":struct.unpack_from("<I",records[0],4)[0],
                "stored_complete_frames":len(axes)//3,"record_count":len(records),
                "header_frame_discrepancy_preserved":struct.unpack_from("<I",records[0],4)[0]!=len(axes)//3,
                "payload_float32_census":word_census(b"".join(axes))}
    return {"format":"Original text bytes; no semantic parser, conversion or execution"}


def fetch(root,dataset):
    spec=SPECS[dataset];root=Path(root).resolve();root.mkdir(parents=True,exist_ok=True)
    output=root/dataset;url=f"https://raw.githubusercontent.com/{spec['repo']}/{spec['commit']}/{spec['path']}"
    if not output.exists():
        with tempfile.TemporaryDirectory(prefix=".crossdomain-",dir=root) as temp:
            stage=Path(temp)/"source";stage.mkdir()
            with urlopen(url,timeout=30) as stream:raw=stream.read((8<<20)+1)
            if len(raw)!=spec["bytes"] or hashlib.sha256(raw).hexdigest()!=spec["sha256"]:
                raise ValueError("Pinned cross-domain original differs")
            target=stage/spec["path"];target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
            stage.rename(output)
    files=inventory(output)
    expected=[{k:spec[k] for k in ("path","bytes","sha256")}]
    if files!=expected:raise ValueError("Existing cross-domain input differs from pin")
    return {"dataset":dataset,"source":str(output),"files":files,**spec,"file_url":url,
            "source_page":f"https://github.com/{spec['repo']}/blob/{spec['commit']}/{spec['path']}",
            "diagnostics":diagnostics(dataset,(output/spec["path"]).read_bytes()),"conversion":"None; all original bytes retained",
            "control_word_bytes":4,"partition":"New independent-domain example" if dataset in ("seismic","molecular") else "Code/math text control"}

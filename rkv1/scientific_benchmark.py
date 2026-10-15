"""Same-v5 typed byte controls and fixed single-thread C-Blosc comparisons."""
from .numeric_benchmark import numeric_benchmark


def matrix(width):
    if type(width) is not int or width not in (2,4,8):raise ValueError("Invalid scientific word width")
    rows=[]
    for size in (65536,1048576):
        common={"layout":f"flat-{size//1024}","chunk_size":size,"unit_size":None,
                "deduplicate":True,"format_version":5,"index_cache_bytes":0}
        rows.extend({**common,"compression":codec,"transform":policy}
            for codec in ("zlib","zstd") for policy in ("none",f"byte-shuffle-{width}-v1",f"xor-shuffle-{width}-v1"))
        rows.extend({**common,"compression":f"blosc-zstd-{filter_name}-{width}","transform":"none"}
                    for filter_name in ("none","shuffle","bitshuffle"))
    return rows


def scientific_benchmark(source,width,*,rounds=5,queries=32,warmup_queries=4):
    report=numeric_benchmark(source,configs=matrix(width),rounds=rounds,queries=queries,warmup_queries=warmup_queries)
    report["schema_version"]=11
    report["word_bytes"]=width
    report["protocol"].update({"container":"v5 flat blocks for ALL methods; fields same as v4; defaults unchanged",
        "transforms":f"Explicit {width}-byte grid, per-block reset, literal tail; entire source file including headers/padding",
        "professional":"python-blosc 1.11.4 bytes API, C-Blosc, Zstd, clevel=3, typesize=word_bytes, blocksize=65536, threads=1, releasegil=False; no/shuffle/bitshuffle controls. Not Blosc2, not Blosc NDArray sub-block reads.",
        "startup":"No Blosc preloading in phase workers. First import/setup charged in full encode and first actual-Blosc-frame decode. Range warmups include first-load cost; formal warm ranges do not.",
        "interpretation":"C-Blosc clevel3 and its embedded Zstd version/block splitting differ from direct Zstd3; only its same-profile filter ablations isolate filter choices.",
        "cost":"Entire RKV archive including C-Blosc frames; separate full installed Blosc distribution+adapter source charge once, with optional NumPy if imported. Shared Python/Zstd/core incomplete, not full deployment size."})
    report["limits"]=["single host, warm OS cache; five rounds are descriptive, not significance evidence",
        "three public astronomy examples (two float32, one small float64), one previous int16 ECG record, one synthetic noise control",
        "astronomy examples share a hosting project; not three independent scientific domains",
        "whole FITS byte grids, not semantic channel/row decomposition; special-value proportions disclosed",
        "Blosc1 Zstd profiles only, not all scientific compressors, NDArray operations or Blosc2",
        "ordinary source/codec allocation incomplete; full standalone and already-installed scenarios separate",
        "no inference, cross-machine/cold-cache, Rust numeric kernel or CAS+numeric integration result"]
    return report

"""Existing byte-shuffle controls on new domains, with explicit file sync."""
from .numeric_benchmark import numeric_benchmark


def matrix(width):
    if type(width) is not int or width not in (2,4,8):raise ValueError("Invalid word width")
    return [{"layout":f"flat-{size//1024}","chunk_size":size,"unit_size":None,"compression":codec,
             "transform":policy,"deduplicate":True,"format_version":4,"index_cache_bytes":0,"restore_sync":"files"}
            for size in (65536,1048576) for codec in ("zlib","zstd") for policy in ("none",f"byte-shuffle-{width}-v1")]


def crossdomain_benchmark(source,width,*,scratch,journal,rounds=5,queries=32,warmup_queries=4):
    report=numeric_benchmark(source,configs=matrix(width),rounds=rounds,queries=queries,warmup_queries=warmup_queries,
                             seed=20261017,scratch=scratch,journal=journal)
    report["schema_version"]=14;report["word_bytes"]=width
    report["protocol"].update({"container":"All methods v4 fixed blocks; no format change",
        "transforms":f"Explicit {width}-byte grids over entire original files, including headers and markers; not semantic type routing",
        "persistence":"Both encode and restore request file flush/fsync; restore files explicitly selected; no directory/volume or power-loss guarantee. Windows publication retries included in phase timing.",
        "journal":"Append-only UTF-8 phase/range records flushed/fsynced outside timed workers; failures abort, no whole-job automatic retry, no overwrite of evidence.",
        "scratch":str(scratch),"cost":"Complete archive plus entire numeric.py allocated once; common runtime/core/codecs incomplete; no new native/model/dictionary dependency.",
        "acceptance":"Four same-codec/block working points: allocated bytes<=ordinary; decode/resident/reopen paired median speedup>=1, each >=4/5 faster; encoding separately disclosed. See docs/CROSSDOMAIN.md."})
    report["limits"]=["one SAC geophysics and one DCD molecular example; complete distributed test files, not entire scientific databases",
        "DCD header declares 500 frames but contains 98 complete stored frames; original discrepancy retained",
        "Python/LaTeX are byte-grid negative/guard controls, not code/math semantic encoders or correctness-of-program proofs",
        "manual word widths, not an automatically learned router; no tuning using new compression results",
        "single Windows host, warm OS cache; no cold/cross-machine/inference/Rust-numeric/CAS+numeric claim",
        "historical close-only restores cannot be directly compared with current file-synced timings"]
    return report

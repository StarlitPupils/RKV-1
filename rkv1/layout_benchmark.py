"""Predeclared same-v6 layout/type ablations, without specialist dependencies."""
from .numeric_benchmark import numeric_benchmark
from .layouts import FITS_POLICY


def matrix(width):
    if type(width) is not int or width not in (2,4,8):raise ValueError("Invalid control width")
    methods=(("ordinary","fixed","none"),("global-shuffle","fixed",f"byte-shuffle-{width}-v1"),
             ("typed-fixed","fixed",FITS_POLICY),("segmented-none","fits-segments-v1","none"),
             ("typed-segmented","fits-segments-v1",FITS_POLICY))
    return [{"layout":name+f"-{size//1024}","method":name,"file_layout":layout,"chunk_size":size,
             "transform":transform,"compression":codec,"unit_size":None,"format_version":6,
             "deduplicate":True,"index_cache_bytes":0}
            for size in (65536,1048576) for codec in ("zlib","zstd") for name,layout,transform in methods]


def layout_benchmark(source,width,*,rounds=5,queries=32,warmup_queries=4):
    report=numeric_benchmark(source,configs=matrix(width),rounds=rounds,queries=queries,warmup_queries=warmup_queries)
    report["schema_version"]=12;report["control_word_bytes"]=width
    report["protocol"].update({"container":"All conditions v6 flat blocks; layout fixed or fits-segments-v1",
        "transforms":"Five preregistered methods: fixed none/global shuffle/typed, segmented none/typed; FITS subset whitelist only. Entire headers/data/padding preserved.",
        "selection":"Ordinary codec first; selected byte-shuffle candidate retained only if local payload+label cost shrinks. Full archive and dedicated sources separately allocated.",
        "cost":"Complete archive plus whole layouts.py/numeric.py source allocated once by declared method; common Python/core/Zstd incomplete. No Blosc/RKV Rust/model/dictionary dependency.",
        "offsets":"Segmented readers build unsigned-64 per-file raw-length prefix arrays; logical array bytes reported; fixed readers use arithmetic. RSS includes Python objects, truth and ledger.",
        "acceptance":"See frozen docs/LAYOUT.md: typed-segmented vs BOTH same-codec/chunk ordinary and global-shuffle; nonincreasing allocated bytes, decode/resident-p95/reopen-p95 paired median>=1 and >=4/5 faster, encoding separately disclosed."})
    report["limits"]=["one previously seen development record, two new astronomy validation records; two unrecognized-format controls",
        "new records share hosting/domain; not cross-domain, strict blind validation, or automatic policy trained on independent corpora",
        "FITS whitelist only: single complete 2D primary float32/64 image; unsupported files fall back without semantic transforms",
        "global-shuffle control width manually declared; not inferred for unknown ECG/noise files",
        "single-host warm OS cache, five descriptive rounds; no cold/cross-machine/inference/CAS+layout/numeric Rust result"]
    return report

import argparse
import json
from pathlib import Path
import sys

from . import __version__
from .core import Archive, DEFAULT_CHUNK, assert_tree_equal, pack, unpack, verify
from .numeric import POLICIES as NUMERIC_POLICIES
from .blosc_codec import PROFILES as BLOSC_PROFILES
from .layouts import LAYOUTS, FITS_POLICY
from .persistence import POLICIES as SYNC_POLICIES


def decoder_options(parser):
    parser.add_argument("--decoder-backend", choices=("python", "rust"), default="python")
    parser.add_argument("--native-library", help="Trusted release DLL/SO with adjacent native.json; required for rust")


def main(argv=None):
    # JSON output must have one stable encoding when piped on Windows as well.
    for stream in (sys.stdout,sys.stderr):
        if hasattr(stream,"reconfigure"):stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="RKV-1: reversible scientific evidence storage")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("pack")
    p.add_argument("source")
    p.add_argument("archive")
    p.add_argument("--chunk-size", type=int, default=DEFAULT_CHUNK)
    p.add_argument("--unit-size", type=int, help="RKV v3 independently verified unit size; divides chunk size, minimum 4096")
    p.add_argument("--base", help="Reuse verified compressed chunks from an earlier snapshot")
    p.add_argument("--overwrite", action="store_true")
    p.add_argument("--codec", choices=("raw", "zlib", "zstd", *BLOSC_PROFILES), default="zlib")
    p.add_argument("--no-dedup", action="store_true")
    p.add_argument("--transform", choices=("none", "csv-columns-v1", *NUMERIC_POLICIES, FITS_POLICY), default="none")
    p.add_argument("--layout", choices=LAYOUTS, default="fixed", help="Explicit FITS region boundaries require v6")
    p.add_argument("--format-version", type=int, choices=(2, 3, 4, 5, 6), help="Auto: v2 flat, v3 units, v4 numeric, v5 Blosc, v6 FITS routing/layout")
    p = sub.add_parser("unpack")
    p.add_argument("archive")
    p.add_argument("destination")
    p.add_argument("--sync-policy", choices=SYNC_POLICIES, default="files", help="files: flush/fsync each verified restored file; close: historical close-only behavior. No directory durability guarantee.")
    decoder_options(p)
    for name in ("verify", "inspect"):
        p = sub.add_parser(name)
        p.add_argument("archive")
        if name == "verify":
            decoder_options(p)
    p = sub.add_parser("compare")
    p.add_argument("source")
    p.add_argument("restored")
    p = sub.add_parser("read")
    p.add_argument("archive")
    p.add_argument("path")
    p.add_argument("--offset", type=int, default=0)
    p.add_argument("--length", type=int)
    p.add_argument("--out", required=True)
    decoder_options(p)
    p = sub.add_parser("bench")
    p.add_argument("source")
    p.add_argument("--out", required=True)
    p.add_argument("--repeats", type=int, default=3)
    p.add_argument("--warmups", type=int, default=1)
    p.add_argument("--queries", type=int, default=32)
    p.add_argument("--chunk-size", type=int, default=DEFAULT_CHUNK)
    p = sub.add_parser("bench-controlled")
    p.add_argument("source")
    p.add_argument("--out", required=True)
    p.add_argument("--repeats", type=int, default=5)
    p.add_argument("--warmups", type=int, default=1)
    p.add_argument("--queries", type=int, default=128)
    p.add_argument("--csv-trials", action="store_true")
    p = sub.add_parser("bench-reads")
    p.add_argument("source")
    p.add_argument("--out", required=True)
    p.add_argument("--sessions", type=int, default=2)
    p.add_argument("--rounds", type=int, default=5)
    p.add_argument("--queries", type=int, default=128)
    p.add_argument("--warmup-queries", type=int, default=8)
    p.add_argument("--seed", type=int, default=20261014)
    p = sub.add_parser("fetch")
    p.add_argument("destination")
    p.add_argument("--dataset", choices=("uci", "scifact", "qasper", "wine", "htru2", "superconductivity"), default="uci")
    p = sub.add_parser("store-init")
    p.add_argument("store")
    p.add_argument("--codec", choices=("raw", "zlib", "zstd"), default="zstd")
    p.add_argument("--chunker", choices=("fixed", "gear-v1"), default="fixed")
    p.add_argument("--chunk-size", type=int, default=65536)
    p = sub.add_parser("store-add")
    p.add_argument("store"); p.add_argument("source"); p.add_argument("--label", default="")
    p.add_argument("--chunker-backend", choices=("python", "rust"), default="python")
    p.add_argument("--native-library", help="Trusted Gear ABI 1 DLL/SO with adjacent native.json")
    p.add_argument("--io-backend", choices=("reference", "bounded"), default="reference")
    p.add_argument("--publisher", choices=("link", "rename"), default="link", help="rename is Windows-only, never replaces an existing file")
    p = sub.add_parser("store-stat")
    p.add_argument("store")
    p = sub.add_parser("store-verify")
    p.add_argument("store"); p.add_argument("snapshot")
    p.add_argument("--io-backend", choices=("reference", "bounded"), default="reference")
    p = sub.add_parser("store-unpack")
    p.add_argument("store"); p.add_argument("snapshot"); p.add_argument("destination")
    p.add_argument("--io-backend", choices=("reference", "bounded"), default="reference")
    p = sub.add_parser("store-read")
    p.add_argument("store"); p.add_argument("snapshot"); p.add_argument("path")
    p.add_argument("--offset", type=int, default=0); p.add_argument("--length", type=int)
    p.add_argument("--out", required=True)
    p.add_argument("--io-backend", choices=("reference", "bounded"), default="reference")
    p=sub.add_parser("memory-init")
    p.add_argument("memory");p.add_argument("source");p.add_argument("--codec",choices=("zlib","zstd"),default="zlib")
    p.add_argument("--index-profile",choices=("full-v1","compact-full-v2","compact-delta-v2","compact-base-v3","compact-budget-v3","compact-projection-v4"),default="compact-budget-v3")
    p.add_argument("--chunker",choices=("fixed","gear-v1"),default="fixed");p.add_argument("--chunk-size",type=int,default=65536)
    p.add_argument("--chunker-backend",choices=("python","rust"),default="python");p.add_argument("--native-library")
    p=sub.add_parser("memory-add")
    p.add_argument("memory");p.add_argument("source");p.add_argument("--label",default="evidence")
    p.add_argument("--chunker-backend",choices=("python","rust"),default="python");p.add_argument("--native-library")
    p=sub.add_parser("memory-budget")
    p.add_argument("memory")
    p=sub.add_parser("memory-search")
    p.add_argument("memory");p.add_argument("question");p.add_argument("--top-k",type=int,default=5);p.add_argument("--snapshot")
    p=sub.add_parser("memory-answer")
    p.add_argument("memory");p.add_argument("question");p.add_argument("--top-k",type=int,default=5);p.add_argument("--snapshot")
    p=sub.add_parser("memory-stat")
    p.add_argument("memory")
    p=sub.add_parser("memory-serve")
    p.add_argument("memory");p.add_argument("--port",type=int,default=8765)
    args = parser.parse_args(argv)
    try:
        if args.command == "pack":
            result = pack(args.source, args.archive, args.chunk_size, base=args.base, overwrite=args.overwrite,
                          compression=args.codec, deduplicate=not args.no_dedup, transform=args.transform,
                          unit_size=args.unit_size, format_version=args.format_version, layout=args.layout)
        elif args.command == "unpack":
            result = unpack(args.archive, args.destination, decoder_backend=args.decoder_backend,
                            native_library=args.native_library, sync_policy=args.sync_policy)
        elif args.command == "verify":
            result = verify(args.archive, decoder_backend=args.decoder_backend, native_library=args.native_library)
        elif args.command == "inspect":
            with Archive(args.archive) as reader:
                result = {"manifest_verified": True, "payload_verified": False, "manifest": reader.header}
        elif args.command == "compare":
            assert_tree_equal(args.source, args.restored)
            result = {"bytewise_verified": True}
        elif args.command == "read":
            with Archive(args.archive, decoder_backend=args.decoder_backend, native_library=args.native_library) as reader:
                raw = reader.read_range(args.path, args.offset, args.length)
                segmented = reader.header["version"] == 3
            with Path(args.out).open("xb") as stream:
                stream.write(raw)
            result = {"bytes": len(raw), "touched_units_verified" if segmented else "touched_chunks_verified": True}
        elif args.command == "bench":
            from .benchmark import benchmark
            result = benchmark(args.source, repeats=args.repeats, warmups=args.warmups, queries=args.queries, chunk_size=args.chunk_size)
            path = Path(args.out)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", "utf-8")
            result = {"report": str(path), "methods": len(result["results"])}
        elif args.command == "bench-controlled":
            from .controlled import controlled_benchmark
            result = controlled_benchmark(args.source, repeats=args.repeats, warmups=args.warmups,
                                          queries=args.queries, csv_trials=args.csv_trials)
            path = Path(args.out)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", "utf-8")
            result = {"report": str(path), "configurations": len(result["results"])}
        elif args.command == "bench-reads":
            from .read_benchmark import read_benchmark
            path = Path(args.out)
            # Reject before doing work; released records must never be overwritten.
            if path.exists():
                raise ValueError("Reading report already exists; choose a new output path")
            result = read_benchmark(args.source, sessions=args.sessions, rounds=args.rounds,
                                    queries=args.queries, warmup_queries=args.warmup_queries, seed=args.seed)
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("x", encoding="utf-8") as stream:
                json.dump(result, stream, ensure_ascii=False, indent=2)
                stream.write("\n")
            result = {"report": str(path), "configurations": len(result["results"])}
        elif args.command.startswith("memory-"):
            from .memory import Memory
            if args.command=="memory-init":
                result=Memory.create(args.memory,compression=args.codec,index_profile=args.index_profile,chunker=args.chunker,chunk_size=args.chunk_size).add(args.source,chunker_backend=args.chunker_backend,native_library=args.native_library)
            elif args.command=="memory-add":result=Memory(args.memory).add(args.source,label=args.label,chunker_backend=args.chunker_backend,native_library=args.native_library)
            elif args.command=="memory-budget":result=Memory(args.memory).enable_replay_budget()
            elif args.command=="memory-search":result=Memory(args.memory).search(args.question,top_k=args.top_k,snapshot=args.snapshot)
            elif args.command=="memory-answer":
                from .memory_model import answer
                result=answer(Memory(args.memory),args.question,top_k=args.top_k,snapshot=args.snapshot)
            elif args.command=="memory-serve":
                from .memory_server import serve
                serve(args.memory,args.port);return
            else:result=Memory(args.memory).stats()
        elif args.command.startswith("store-"):
            from .store import Store, unpack as store_unpack, verify as store_verify
            if args.command == "store-init":
                store = Store.create(args.store, compression=args.codec, chunker=args.chunker, chunk_size=args.chunk_size)
                result = {"config": store.config, "config_sha256": store.config_sha256}
            elif args.command == "store-add":
                result = Store(args.store, io_backend=args.io_backend, publisher=args.publisher).add(args.source, label=args.label,
                            chunker_backend=args.chunker_backend, native_library=args.native_library)
            elif args.command == "store-stat":
                result = Store(args.store).stats()
            elif args.command == "store-verify":
                result = store_verify(args.store, args.snapshot, io_backend=args.io_backend)
            elif args.command == "store-unpack":
                result = store_unpack(args.store, args.snapshot, args.destination, io_backend=args.io_backend)
            else:
                raw = Store(args.store, io_backend=args.io_backend).snapshot(args.snapshot).read_range(args.path, args.offset, args.length)
                with Path(args.out).open("xb") as stream:
                    stream.write(raw)
                result = {"bytes": len(raw), "touched_objects_verified": True}
        else:
            from .datasets import fetch_public
            result = fetch_public(args.destination, args.dataset)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except (ValueError, OSError, KeyError) as exc:
        parser.exit(2, f"ERROR: {exc}\n")

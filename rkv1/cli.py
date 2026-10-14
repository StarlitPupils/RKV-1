import argparse
import json
from pathlib import Path

from . import __version__
from .core import Archive, DEFAULT_CHUNK, assert_tree_equal, pack, unpack, verify


def main(argv=None):
    parser = argparse.ArgumentParser(description="RKV-1: reversible scientific evidence storage")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("pack")
    p.add_argument("source")
    p.add_argument("archive")
    p.add_argument("--chunk-size", type=int, default=DEFAULT_CHUNK)
    p.add_argument("--base", help="Reuse verified compressed chunks from an earlier snapshot")
    p.add_argument("--overwrite", action="store_true")
    p = sub.add_parser("unpack")
    p.add_argument("archive")
    p.add_argument("destination")
    for name in ("verify", "inspect"):
        p = sub.add_parser(name)
        p.add_argument("archive")
    p = sub.add_parser("compare")
    p.add_argument("source")
    p.add_argument("restored")
    p = sub.add_parser("read")
    p.add_argument("archive")
    p.add_argument("path")
    p.add_argument("--offset", type=int, default=0)
    p.add_argument("--length", type=int)
    p.add_argument("--out", required=True)
    p = sub.add_parser("bench")
    p.add_argument("source")
    p.add_argument("--out", required=True)
    p.add_argument("--repeats", type=int, default=3)
    p.add_argument("--warmups", type=int, default=1)
    p.add_argument("--queries", type=int, default=32)
    p.add_argument("--chunk-size", type=int, default=DEFAULT_CHUNK)
    p = sub.add_parser("fetch")
    p.add_argument("destination")
    p.add_argument("--dataset", choices=("uci", "scifact"), default="uci")
    args = parser.parse_args(argv)
    try:
        if args.command == "pack":
            result = pack(args.source, args.archive, args.chunk_size, base=args.base, overwrite=args.overwrite)
        elif args.command == "unpack":
            result = unpack(args.archive, args.destination)
        elif args.command == "verify":
            result = verify(args.archive)
        elif args.command == "inspect":
            with Archive(args.archive) as reader:
                result = {"manifest_verified": True, "payload_verified": False, "manifest": reader.header}
        elif args.command == "compare":
            assert_tree_equal(args.source, args.restored)
            result = {"bytewise_verified": True}
        elif args.command == "read":
            with Archive(args.archive) as reader:
                raw = reader.read_range(args.path, args.offset, args.length)
            with Path(args.out).open("xb") as stream:
                stream.write(raw)
            result = {"bytes": len(raw), "touched_chunks_verified": True}
        elif args.command == "bench":
            from .benchmark import benchmark
            result = benchmark(args.source, repeats=args.repeats, warmups=args.warmups, queries=args.queries, chunk_size=args.chunk_size)
            path = Path(args.out)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", "utf-8")
            result = {"report": str(path), "methods": len(result["results"])}
        else:
            from .datasets import fetch_public
            result = fetch_public(args.destination, args.dataset)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except (ValueError, OSError, KeyError) as exc:
        parser.exit(2, f"ERROR: {exc}\n")

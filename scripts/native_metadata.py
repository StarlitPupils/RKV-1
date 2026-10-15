"""Create build provenance for CI integration tests; release packaging records the same fields."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import subprocess


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("library", type=Path)
    args = parser.parse_args()
    library = args.library.resolve()
    info = {"abi": 1, "library": library.name, "sha256": hashlib.sha256(library.read_bytes()).hexdigest(),
            "bytes": library.stat().st_size, "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
            "tag": "CI-candidate", "platform": platform.platform(),
            "rustc": subprocess.check_output(["rustc", "--version"], text=True).strip(),
            "features": ["csv-columns-v1", "gear-v1"], "gear_abi": 1,
            "scope": "CSV inverse and Gear boundary scan; not a complete archive/CAS implementation"}
    library.with_name("native.json").write_text(json.dumps(info, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

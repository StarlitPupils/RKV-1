"""Small, pinned public datasets. Data files are never silently normalized."""
import hashlib
import io
import json
from pathlib import Path
import tarfile
from urllib.request import Request, urlopen

UCI = {
    "iris.csv": ("https://archive.ics.uci.edu/ml/machine-learning-databases/iris/iris.data", "6f608b71a7317216319b4d27b4d9bc84e6abd734eda7872b71a458569e2656c0"),
    "winequality-red.csv": ("https://archive.ics.uci.edu/ml/machine-learning-databases/wine-quality/winequality-red.csv", "4a402cf041b025d4566d954c3b9ba8635a3a8a01e039005d97d6a710278cf05e"),
}
SCIFACT_URL = "https://scifact.s3-us-west-2.amazonaws.com/release/latest/data.tar.gz"
SCIFACT_ARCHIVE_SHA256 = "11c621288d41ac144d29b13b0f8503b3820b7d6e8b1f6ff24dff335c196d76be"
SCIFACT = {
    "corpus.jsonl": "b8d6c89624cb2ed74dee8938effc4f5d8bd2086887880af8110d64be4ceade62",
    "claims_train.jsonl": "f4c8fa82d8bd0653a9cc8d61a6ea48c25eacea64e90af5dbf390ebb1b74372f0",
    "claims_dev.jsonl": "86f0435d08fdb65d1aa41d1472684f57e6e71930626497bdf4d7a9ec1a632217",
    "claims_test.jsonl": "558930d75215c73f84a28fe538307d6d397c9de1ec7239514cf45f80d75d2ca3",
}


def _check(raw, expected):
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError("Dataset SHA-256 mismatch; upstream may have changed. Review before changing the pin.")
    return raw


def _download(url, expected):
    with urlopen(Request(url, headers={"User-Agent": "RKV1/0.1.0"}), timeout=60) as response:
        raw = response.read((32 << 20) + 1)
    if len(raw) > 32 << 20:
        raise ValueError("Download exceeds size limit")
    return _check(raw, expected)


def fetch_public(destination, dataset="uci"):
    destination = Path(destination)
    if destination.is_symlink():
        raise ValueError("Dataset destination must not be a symlink")
    destination.mkdir(parents=True, exist_ok=True)
    expected = {name: sha for name, (_, sha) in UCI.items()} if dataset == "uci" else SCIFACT if dataset == "scifact" else None
    if expected is None:
        raise ValueError("Unknown dataset")
    content = {}
    for name, sha in expected.items():
        path = destination / name
        if path.exists() or path.is_symlink():
            if path.is_symlink():
                raise ValueError("Dataset file must not be a symlink")
            content[name] = _check(path.read_bytes(), sha)
    if dataset == "uci":
        for name, (url, sha) in UCI.items():
            if name not in content:
                content[name] = _download(url, sha)
    elif len(content) != len(expected):
        raw = _download(SCIFACT_URL, SCIFACT_ARCHIVE_SHA256)
        with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as tar:
            for name, sha in expected.items():
                member = tar.getmember(f"data/{name}")
                if not member.isfile() or member.size > 16 << 20:
                    raise ValueError("Invalid SciFact member")
                with tar.extractfile(member) as stream:
                    content[name] = _check(stream.read((16 << 20) + 1), sha)
    # Validate all downloads before creating any new dataset files.
    for name, raw in content.items():
        target = destination / name
        if not target.exists():
            with target.open("xb") as stream:
                stream.write(raw)
    sources = [{"filename": name, "bytes": len(content[name]), "sha256": sha,
                "url": UCI[name][0] if dataset == "uci" else SCIFACT_URL,
                "license": "CC BY 4.0" if dataset == "uci" or name.startswith("claims_") else "ODC-By 1.0"}
               for name, sha in expected.items()]
    # Outside the raw corpus: provenance metadata must not contaminate its size.
    sidecar = destination.parent / f"{destination.name}.sources.json"
    sidecar.write_text(json.dumps({"dataset": dataset, "files": sources}, indent=2) + "\n", "utf-8")
    return {"dataset": dataset, "sources": str(sidecar), "files": sources}

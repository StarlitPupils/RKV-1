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
WINE = {
    "winequality-red.csv": UCI["winequality-red.csv"],
    "winequality-white.csv": ("https://archive.ics.uci.edu/ml/machine-learning-databases/wine-quality/winequality-white.csv", "76c3f809815c17c07212622f776311faeb31e87610d52c26d87d6e361b169836"),
}
QASPER_URL = "https://qasper-dataset.s3-us-west-2.amazonaws.com/qasper-train-dev-v0.3.tgz"
QASPER_ARCHIVE_SHA256 = "a28fdf966db827bcee3d873107d6b6669864fb7ca8fbf73a192f5e39191bdb5a"
QASPER = {
    "qasper-train-v0.3.json": "9458bfe76074a8fa8d1685af02bcc73537aa6d338ad20591dfaff1946bc88bf4",
    "qasper-dev-v0.3.json": "2ae7ee62a65b1c4225791c70de80c2aad4e8998cf1fd4f09a53103db4f21af93",
}


def _check(raw, expected):
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError("Dataset SHA-256 mismatch; upstream may have changed. Review before changing the pin.")
    return raw


def _download(url, expected):
    from . import __version__
    with urlopen(Request(url, headers={"User-Agent": f"RKV1/{__version__}"}), timeout=60) as response:
        raw = response.read((32 << 20) + 1)
    if len(raw) > 32 << 20:
        raise ValueError("Download exceeds size limit")
    return _check(raw, expected)


def fetch_public(destination, dataset="uci"):
    destination = Path(destination)
    if destination.is_symlink():
        raise ValueError("Dataset destination must not be a symlink")
    destination.mkdir(parents=True, exist_ok=True)
    direct = UCI if dataset == "uci" else WINE if dataset == "wine" else None
    expected = {name: sha for name, (_, sha) in direct.items()} if direct else SCIFACT if dataset == "scifact" else QASPER if dataset == "qasper" else None
    if expected is None:
        raise ValueError("Unknown dataset")
    content = {}
    for name, sha in expected.items():
        path = destination / name
        if path.exists() or path.is_symlink():
            if path.is_symlink():
                raise ValueError("Dataset file must not be a symlink")
            content[name] = _check(path.read_bytes(), sha)
    if direct:
        for name, (url, sha) in direct.items():
            if name not in content:
                content[name] = _download(url, sha)
    elif len(content) != len(expected):
        url, sha = (SCIFACT_URL, SCIFACT_ARCHIVE_SHA256) if dataset == "scifact" else (QASPER_URL, QASPER_ARCHIVE_SHA256)
        raw = _download(url, sha)
        with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as tar:
            for name, sha in expected.items():
                member = tar.getmember(f"data/{name}" if dataset == "scifact" else name)
                if not member.isfile() or member.size > 64 << 20:
                    raise ValueError("Invalid scientific dataset member")
                with tar.extractfile(member) as stream:
                    content[name] = _check(stream.read((64 << 20) + 1), sha)
    # Validate all downloads before creating any new dataset files.
    for name, raw in content.items():
        target = destination / name
        if not target.exists():
            with target.open("xb") as stream:
                stream.write(raw)
    sources = [{"filename": name, "bytes": len(content[name]), "sha256": sha,
                "url": direct[name][0] if direct else SCIFACT_URL if dataset == "scifact" else QASPER_URL,
                "license": "ODC-By 1.0" if dataset == "scifact" and name == "corpus.jsonl" else "CC BY 4.0"}
               for name, sha in expected.items()]
    # Outside the raw corpus: provenance metadata must not contaminate its size.
    sidecar = destination.parent / f"{destination.name}.sources.json"
    sidecar.write_text(json.dumps({"dataset": dataset, "files": sources}, indent=2) + "\n", "utf-8")
    return {"dataset": dataset, "sources": str(sidecar), "files": sources}

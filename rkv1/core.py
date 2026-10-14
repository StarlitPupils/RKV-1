"""RKV1 draft 0.1: self-contained, content-addressed directory archives.

Only regular-file relative paths and bytes are preserved. No lossy transforms.
The SHA-256 digest of the manifest detects accidental metadata damage, not forgery.
"""
from __future__ import annotations

from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import struct
import tempfile
import unicodedata
import zlib

MAGIC = b"RKV1\r\n\x1a\n"
VERSION = 1
DEFAULT_CHUNK = 1 << 20
MAX_CHUNK = 8 << 20
MAX_HEADER = 64 << 20
MAX_OUTPUT = 2 << 30
MAX_FILES = 100_000
MAX_BLOCKS = 500_000
PREFIX_SIZE = 48  # magic + u64 manifest length + SHA-256(manifest)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def valid_hash(value):
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def valid_path(value):
    """Require paths that cannot alias or escape on Windows or POSIX."""
    if not isinstance(value, str) or not value or len(value) > 4096:
        raise ValueError("Invalid relative path")
    reserved = {"CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$"}
    reserved.update(f"{prefix}{n}" for prefix in ("COM", "LPT") for n in "123456789¹²³")
    for part in value.split("/"):
        if (part in ("", ".", "..") or part[-1:] in (" ", ".")
                or any(ord(c) < 32 or ord(c) == 127 or c in '\\:<>"|?*' for c in part)
                or part.split(".")[0].upper() in reserved):
            raise ValueError(f"Unsafe archive path: {value!r}")
    try:
        value.encode("utf-8")
    except UnicodeError as exc:
        raise ValueError("Path is not valid Unicode") from exc
    return PurePosixPath(value)


def _path_key(value):
    return unicodedata.normalize("NFC", value).casefold()


def _check_paths(paths):
    seen = set()
    for path in paths:
        valid_path(path)
        key = _path_key(path)
        if key in seen:
            raise ValueError("Duplicate or non-portable path collision")
        seen.add(key)
    for path in seen:
        if any(parent.as_posix() in seen for parent in PurePosixPath(path).parents if parent.as_posix() != "."):
            raise ValueError("File/directory path collision")


def _regular_kind(path):
    st = path.lstat()
    if stat.S_ISLNK(st.st_mode) or getattr(st, "st_file_attributes", 0) & 0x400:
        raise ValueError(f"Symlinks and reparse points unsupported: {path}")
    return st.st_mode


def files_in(root):
    root = Path(root)
    if not stat.S_ISDIR(_regular_kind(root)):
        raise ValueError("Source must be a real directory")
    entries = []
    # Walk explicitly so a junction is rejected before entering it.
    pending = [root]
    while pending:
        directory = pending.pop()
        for path in directory.iterdir():
            mode = _regular_kind(path)
            if stat.S_ISDIR(mode):
                pending.append(path)
            elif stat.S_ISREG(mode):
                entries.append((path, path.relative_to(root).as_posix()))
                if len(entries) > MAX_FILES:
                    raise ValueError("Too many files")
            else:
                raise ValueError(f"Special file unsupported: {path}")
    entries.sort(key=lambda item: item[1])
    _check_paths(rel for _, rel in entries)
    yield from entries


def _json_bytes(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("Duplicate JSON key")
        value[key] = item
    return value


def validate_manifest(header, payload_size):
    if not isinstance(header, dict) or set(header) != {"version", "chunk_size", "files", "blocks"}:
        raise ValueError("Invalid manifest schema")
    if type(header["version"]) is not int or header["version"] != VERSION:
        raise ValueError("Unsupported format version")
    chunk_size = header["chunk_size"]
    if type(chunk_size) is not int or not 1 <= chunk_size <= MAX_CHUNK:
        raise ValueError("Invalid chunk size")
    files, blocks = header["files"], header["blocks"]
    if not isinstance(files, list) or not isinstance(blocks, dict):
        raise ValueError("Invalid manifest collections")
    if len(files) > MAX_FILES or len(blocks) > MAX_BLOCKS:
        raise ValueError("Manifest exceeds prototype limits")
    ranges = []
    for key, meta in blocks.items():
        if not valid_hash(key) or not isinstance(meta, dict) or set(meta) != {"offset", "stored_size", "raw_size", "codec"}:
            raise ValueError("Invalid block metadata")
        if any(type(meta[f]) is not int for f in ("offset", "stored_size", "raw_size")):
            raise ValueError("Invalid block number")
        offset, stored, raw, codec = (meta[f] for f in ("offset", "stored_size", "raw_size", "codec"))
        if (offset < 0 or not 1 <= raw <= chunk_size or not 1 <= stored <= raw
                or codec not in ("raw", "zlib") or (codec == "raw" and stored != raw)
                or (codec == "zlib" and stored >= raw) or offset + stored > payload_size):
            raise ValueError("Invalid block bounds or codec")
        ranges.append((offset, offset + stored))
    cursor = 0
    for start, end in sorted(ranges):
        if start != cursor:
            raise ValueError("Overlapping or missing block payload")
        cursor = end
    if cursor != payload_size:
        raise ValueError("Unexpected trailing payload")
    total, referenced, paths = 0, set(), []
    for entry in files:
        if not isinstance(entry, dict) or set(entry) != {"path", "size", "sha256", "chunks"}:
            raise ValueError("Invalid file entry")
        valid_path(entry["path"])
        paths.append(entry["path"])
        if (type(entry["size"]) is not int or not 0 <= entry["size"] <= MAX_OUTPUT
                or not valid_hash(entry["sha256"]) or not isinstance(entry["chunks"], list)):
            raise ValueError("Invalid file metadata")
        expected_count = (entry["size"] + chunk_size - 1) // chunk_size
        if len(entry["chunks"]) != expected_count:
            raise ValueError("Non-canonical chunk count")
        size = 0
        for i, key in enumerate(entry["chunks"]):
            if not isinstance(key, str) or key not in blocks:
                raise ValueError("Missing referenced chunk")
            expected = min(chunk_size, entry["size"] - i * chunk_size)
            if blocks[key]["raw_size"] != expected:
                raise ValueError("Non-canonical chunk length")
            size += blocks[key]["raw_size"]
            referenced.add(key)
        if size != entry["size"]:
            raise ValueError("File length mismatch")
        total += size
        if total > MAX_OUTPUT:
            raise ValueError("Archive exceeds 2 GiB output limit")
    _check_paths(paths)
    if referenced != set(blocks):
        raise ValueError("Unreferenced blocks")


def read_manifest(stream):
    if stream.read(8) != MAGIC:
        raise ValueError("Invalid RKV1 magic")
    length_bytes = stream.read(8)
    if len(length_bytes) != 8:
        raise ValueError("Truncated manifest length")
    length, = struct.unpack("<Q", length_bytes)
    if not 2 <= length <= MAX_HEADER:
        raise ValueError("Manifest size exceeds limits")
    checksum, encoded = stream.read(32), stream.read(length)
    if len(encoded) != length or hashlib.sha256(encoded).digest() != checksum:
        raise ValueError("Manifest SHA-256 mismatch or truncation")
    try:
        header = json.loads(encoded.decode("utf-8"), object_pairs_hook=_unique_object)
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise ValueError("Invalid JSON manifest") from exc
    body_start = stream.tell()
    stream.seek(0, os.SEEK_END)
    validate_manifest(header, stream.tell() - body_start)
    return header, body_start


def decode_block(stream, body_start, key, meta):
    stream.seek(body_start + meta["offset"])
    stored = stream.read(meta["stored_size"])
    if len(stored) != meta["stored_size"]:
        raise ValueError("Truncated block")
    if meta["codec"] == "raw":
        raw = stored
    else:
        try:
            decoder = zlib.decompressobj()
            raw = decoder.decompress(stored, meta["raw_size"] + 1)
        except zlib.error as exc:
            raise ValueError("Invalid compressed block") from exc
        if not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:
            raise ValueError("Malformed compressed block")
    if len(raw) != meta["raw_size"] or digest(raw) != key:
        raise ValueError("Block SHA-256 mismatch or length mismatch")
    return raw


class Archive:
    """Single-threaded reader. Range reads verify touched chunks, not other files."""
    def __init__(self, path):
        self.stream = Path(path).open("rb")
        try:
            self.header, self.body_start = read_manifest(self.stream)
            self.files = {entry["path"]: entry for entry in self.header["files"]}
        except BaseException:
            self.stream.close()
            raise

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def close(self):
        self.stream.close()

    def block(self, key):
        return decode_block(self.stream, self.body_start, key, self.header["blocks"][key])

    def read_range(self, path, offset=0, length=None):
        entry = self.files[path]
        if length is None:
            length = entry["size"] - offset
        if type(offset) is not int or type(length) is not int or offset < 0 or length < 0 or offset + length > entry["size"]:
            raise ValueError("Invalid byte range")
        if length > 64 << 20:
            raise ValueError("Use streaming unpack for reads larger than 64 MiB")
        chunk_size = self.header["chunk_size"]
        result = bytearray()
        for i in range(offset // chunk_size, (offset + length + chunk_size - 1) // chunk_size):
            if not length:
                break
            raw = self.block(entry["chunks"][i])
            start, end = max(0, offset - i * chunk_size), min(len(raw), offset + length - i * chunk_size)
            result.extend(raw[start:end])
        data = bytes(result)
        if offset == 0 and length == entry["size"] and digest(data) != entry["sha256"]:
            raise ValueError("File SHA-256 mismatch")
        return data

    def process(self, output_dir=None):
        for entry in self.header["files"]:
            file_hash = hashlib.sha256()
            with ExitStack() as stack:
                output = None
                if output_dir is not None:
                    target = Path(output_dir).joinpath(*valid_path(entry["path"]).parts)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    output = stack.enter_context(target.open("xb"))
                for key in entry["chunks"]:
                    raw = self.block(key)
                    file_hash.update(raw)
                    if output is not None:
                        output.write(raw)
            if file_hash.hexdigest() != entry["sha256"]:
                raise ValueError(f"File SHA-256 mismatch: {entry['path']}")
        return {"verified_files": len(self.files), "unique_chunks": len(self.header["blocks"]),
                "raw_bytes": sum(e["size"] for e in self.header["files"])}


def pack(source, archive, chunk_size=DEFAULT_CHUNK, *, base=None, overwrite=False):
    source, archive = Path(source), Path(archive)
    if type(chunk_size) is not int or not 1 <= chunk_size <= MAX_CHUNK:
        raise ValueError("Invalid chunk size")
    if archive.resolve().is_relative_to(source.resolve()):
        raise ValueError("Archive must be outside source directory")
    if archive.exists() and not overwrite:
        raise FileExistsError(archive)
    if base is not None and Path(base).resolve() == archive.resolve():
        raise ValueError("Base and new archive must differ")
    entries, blocks, total_raw, reused = [], {}, 0, 0
    with ExitStack() as stack:
        previous = stack.enter_context(Archive(base)) if base else None
        if previous and previous.header["chunk_size"] != chunk_size:
            raise ValueError("Incremental base chunk size must match")
        spool = stack.enter_context(tempfile.TemporaryFile())
        for path, rel in files_in(source):
            file_hash, references, size = hashlib.sha256(), [], 0
            with path.open("rb") as stream:
                while raw := stream.read(chunk_size):
                    total_raw += len(raw)
                    if total_raw > MAX_OUTPUT:
                        raise ValueError("Prototype 2 GiB output limit")
                    size += len(raw)
                    file_hash.update(raw)
                    key = digest(raw)
                    references.append(key)
                    if key in blocks:
                        continue
                    if len(blocks) >= MAX_BLOCKS:
                        raise ValueError("Too many unique blocks")
                    if previous and key in previous.header["blocks"]:
                        if previous.block(key) != raw:
                            raise ValueError("Base block mismatch")
                        old = previous.header["blocks"][key]
                        previous.stream.seek(previous.body_start + old["offset"])
                        payload, codec = previous.stream.read(old["stored_size"]), old["codec"]
                        reused += 1
                    else:
                        compressed = zlib.compress(raw, level=6)
                        codec, payload = ("zlib", compressed) if len(compressed) < len(raw) else ("raw", raw)
                    blocks[key] = {"offset": spool.tell(), "stored_size": len(payload), "raw_size": len(raw), "codec": codec}
                    spool.write(payload)
            entries.append({"path": rel, "size": size, "sha256": file_hash.hexdigest(), "chunks": references})
        header = {"version": VERSION, "chunk_size": chunk_size, "files": entries, "blocks": blocks}
        validate_manifest(header, spool.tell())
        encoded = _json_bytes(header)
        if len(encoded) > MAX_HEADER:
            raise ValueError("Manifest too large")
        archive.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=".rkv1-", dir=archive.parent)
        try:
            with os.fdopen(fd, "wb") as output:
                output.write(MAGIC + struct.pack("<Q", len(encoded)) + hashlib.sha256(encoded).digest() + encoded)
                spool.seek(0)
                shutil.copyfileobj(spool, output)
                output.flush()
                os.fsync(output.fileno())
            if overwrite:
                os.replace(temporary, archive)
            else:
                # Atomic publish without replacing another process's output.
                os.link(temporary, archive)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
    return {"files": len(entries), "raw_bytes": total_raw, "chunk_references": sum(len(e["chunks"]) for e in entries),
            "unique_chunks": len(blocks), "reused_chunks": reused, "new_chunks": len(blocks) - reused,
            "unique_raw_bytes": sum(b["raw_size"] for b in blocks.values()),
            "payload_bytes": sum(b["stored_size"] for b in blocks.values()),
            "metadata_bytes": PREFIX_SIZE + len(encoded), "stored_bytes": archive.stat().st_size}


def verify(archive):
    with Archive(archive) as reader:
        return reader.process()


def unpack(archive, destination):
    destination = Path(destination)
    if destination.exists() or destination.is_symlink():
        raise FileExistsError("Destination must not already exist")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".rkv-extract-", dir=destination.parent) as temporary:
        stage = Path(temporary) / "data"
        stage.mkdir()
        with Archive(archive) as reader:
            result = reader.process(stage)
        # Check again just before publish; extraction parents must be trusted.
        if destination.exists() or destination.is_symlink():
            raise FileExistsError(destination)
        stage.rename(destination)
    return result


def same_bytes(first, second):
    with Path(first).open("rb") as a, Path(second).open("rb") as b:
        while True:
            left, right = a.read(1 << 20), b.read(1 << 20)
            if left != right:
                return False
            if not left:
                return True


def assert_tree_equal(first, second):
    left, right = dict((rel, p) for p, rel in files_in(first)), dict((rel, p) for p, rel in files_in(second))
    if left.keys() != right.keys():
        raise ValueError("File lists differ")
    for rel in left:
        if not same_bytes(left[rel], right[rel]):
            raise ValueError(f"Bytewise mismatch: {rel}")

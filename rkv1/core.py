"""RKV1 draft 0.2: self-contained, content-addressed directory archives.

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

from .codecs import compressor, decompress
from .transforms import csv_columns_decode, csv_columns_encode

MAGIC = b"RKV1\r\n\x1a\n"
VERSION = 2
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


def block_hash(key):
    return key.split("@", 1)[0]


def valid_block_id(key, version, deduplicate):
    if not isinstance(key, str):
        return False
    if version == 1 or deduplicate:
        return valid_hash(key)
    parts = key.split("@")
    return (len(parts) == 2 and valid_hash(parts[0]) and len(parts[1]) == 8
            and all(c in "0123456789abcdef" for c in parts[1]))


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
    if not isinstance(header, dict):
        raise ValueError("Invalid manifest schema")
    version = header.get("version")
    if type(version) is not int or version not in (1, VERSION):
        raise ValueError("Unsupported format version")
    fields = {"version", "chunk_size", "files", "blocks"}
    if version == 2:
        fields.update(("compression", "deduplicate", "transform"))
    if set(header) != fields:
        raise ValueError("Invalid manifest schema")
    deduplicate = header.get("deduplicate", True)
    if version == 2 and (type(deduplicate) is not bool or header["compression"] not in ("raw", "zlib", "zstd")
                         or header["transform"] not in ("none", "csv-columns-v1")):
        raise ValueError("Invalid archive encoding policy")
    chunk_size = header["chunk_size"]
    if type(chunk_size) is not int or not 1 <= chunk_size <= MAX_CHUNK:
        raise ValueError("Invalid chunk size")
    files, blocks = header["files"], header["blocks"]
    if not isinstance(files, list) or not isinstance(blocks, dict):
        raise ValueError("Invalid manifest collections")
    if len(files) > MAX_FILES or len(blocks) > MAX_BLOCKS:
        raise ValueError("Manifest exceeds prototype limits")
    ranges = []
    suffixes = set()
    for key, meta in blocks.items():
        block_fields = {"offset", "stored_size", "raw_size", "codec"}
        if version == 2:
            block_fields.update(("coded_size", "transform"))
        if not valid_block_id(key, version, deduplicate) or not isinstance(meta, dict) or set(meta) != block_fields:
            raise ValueError("Invalid block metadata")
        if any(type(meta[f]) is not int for f in ("offset", "stored_size", "raw_size")):
            raise ValueError("Invalid block number")
        offset, stored, raw, codec = (meta[f] for f in ("offset", "stored_size", "raw_size", "codec"))
        allowed_codecs = ("raw", "zlib") if version == 1 else ("raw", "zlib", "zstd")
        if (offset < 0 or not 1 <= raw <= chunk_size or not 1 <= stored <= raw
                or codec not in allowed_codecs or (codec == "raw" and stored != raw)
                or (codec != "raw" and stored >= raw) or offset + stored > payload_size):
            raise ValueError("Invalid block bounds or codec")
        if version == 2:
            coded, transform = meta["coded_size"], meta["transform"]
            if (type(coded) is not int or not 1 <= coded <= 2 * raw + 256
                    or transform not in ("none", "csv-columns-v1")
                    or (transform == "none" and coded != raw)
                    or (transform != "none" and (codec == "raw" or header["transform"] != transform))
                    or (codec != "raw" and codec != header["compression"])):
                raise ValueError("Invalid block transform or encoding policy")
            if not deduplicate:
                suffix = int(key.split("@")[1], 16)
                if suffix in suffixes:
                    raise ValueError("Duplicate block occurrence index")
                suffixes.add(suffix)
        ranges.append((offset, offset + stored))
    if version == 2 and not deduplicate and suffixes != set(range(len(blocks))):
        raise ValueError("Non-canonical block occurrence indices")
    cursor = 0
    for start, end in sorted(ranges):
        if start != cursor:
            raise ValueError("Overlapping or missing block payload")
        cursor = end
    if cursor != payload_size:
        raise ValueError("Unexpected trailing payload")
    total, referenced, paths, reference_count = 0, set(), [], 0
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
            reference_count += 1
        if size != entry["size"]:
            raise ValueError("File length mismatch")
        total += size
        if total > MAX_OUTPUT:
            raise ValueError("Archive exceeds 2 GiB output limit")
    _check_paths(paths)
    if referenced != set(blocks):
        raise ValueError("Unreferenced blocks")
    if version == 2 and not deduplicate and reference_count != len(blocks):
        raise ValueError("Repeated references in no-dedup archive")


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
    raw = decompress(stored, meta["codec"], meta.get("coded_size", meta["raw_size"]))
    if meta.get("transform", "none") == "csv-columns-v1":
        raw = csv_columns_decode(raw, meta["raw_size"])
    if len(raw) != meta["raw_size"] or digest(raw) != block_hash(key):
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


def pack(source, archive, chunk_size=DEFAULT_CHUNK, *, base=None, overwrite=False,
         compression="zlib", deduplicate=True, transform="none"):
    source, archive = Path(source), Path(archive)
    if type(chunk_size) is not int or not 1 <= chunk_size <= MAX_CHUNK:
        raise ValueError("Invalid chunk size")
    if type(deduplicate) is not bool or transform not in ("none", "csv-columns-v1"):
        raise ValueError("Invalid encoding policy")
    if compression == "raw" and transform != "none":
        raise ValueError("Transforms require a compression profile")
    compress = compressor(compression)
    if archive.resolve().is_relative_to(source.resolve()):
        raise ValueError("Archive must be outside source directory")
    if archive.exists() and not overwrite:
        raise FileExistsError(archive)
    if base is not None and Path(base).resolve() == archive.resolve():
        raise ValueError("Base and new archive must differ")
    entries, blocks, total_raw, reused, transformed, attempts = [], {}, 0, 0, 0, 0
    with ExitStack() as stack:
        previous = stack.enter_context(Archive(base)) if base else None
        if previous and previous.header["chunk_size"] != chunk_size:
            raise ValueError("Incremental base chunk size must match")
        if previous and (previous.header.get("compression", "zlib") != compression
                         or previous.header.get("transform", "none") != transform):
            raise ValueError("Incremental base compression and transform policy must match")
        previous_ids = {block_hash(key): key for key in previous.header["blocks"]} if previous else {}
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
                    raw_hash = digest(raw)
                    key = raw_hash if deduplicate else f"{raw_hash}@{len(blocks):08x}"
                    references.append(key)
                    if key in blocks:
                        continue
                    if len(blocks) >= MAX_BLOCKS:
                        raise ValueError("Too many unique blocks")
                    if previous and raw_hash in previous_ids:
                        previous_key = previous_ids[raw_hash]
                        if previous.block(previous_key) != raw:
                            raise ValueError("Base block mismatch")
                        old = previous.header["blocks"][previous_key]
                        previous.stream.seek(previous.body_start + old["offset"])
                        payload, codec = previous.stream.read(old["stored_size"]), old["codec"]
                        coded_size, chosen_transform = old.get("coded_size", len(raw)), old.get("transform", "none")
                        reused += 1
                    else:
                        compressed = compress(raw)
                        codec, payload = ("zlib", compressed) if len(compressed) < len(raw) else ("raw", raw)
                        if codec != "raw":
                            codec = compression
                        coded_size, chosen_transform = len(raw), "none"
                        if transform == "csv-columns-v1":
                            attempts += 1
                            candidate = csv_columns_encode(raw)
                            if candidate is not None:
                                candidate_payload = compress(candidate)
                                # Include the longer transform label and coded-size field
                                # in local selection. Full archive size is also benchmarked.
                                extra = len(transform) - len("none") + len(str(len(candidate))) - len(str(len(raw)))
                                if len(candidate_payload) + extra < len(payload):
                                    payload, codec, coded_size, chosen_transform = candidate_payload, compression, len(candidate), transform
                    if chosen_transform != "none":
                        transformed += 1
                    blocks[key] = {"offset": spool.tell(), "stored_size": len(payload), "raw_size": len(raw), "codec": codec,
                                   "coded_size": coded_size, "transform": chosen_transform}
                    spool.write(payload)
            entries.append({"path": rel, "size": size, "sha256": file_hash.hexdigest(), "chunks": references})
        header = {"version": VERSION, "chunk_size": chunk_size, "files": entries, "blocks": blocks,
                  "compression": compression, "deduplicate": deduplicate, "transform": transform}
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
            "metadata_bytes": PREFIX_SIZE + len(encoded), "stored_bytes": archive.stat().st_size,
            "compression": compression, "deduplicate": deduplicate, "transform": transform,
            "transformed_chunks": transformed, "transform_attempts": attempts,
            "archive_sha256": _file_digest(archive)}


def _file_digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        while raw := stream.read(1 << 20):
            h.update(raw)
    return h.hexdigest()


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

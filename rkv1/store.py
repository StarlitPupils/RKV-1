"""Immutable shared CAS objects and atomically published exact snapshots.

Logical file bytes are fully counted. Filesystem directories/MFT/journal costs
are separate and not inferred from file sizes. Caller-selected parents and
stores must be trusted; internal links/reparse points are rejected.
"""
from bisect import bisect_right
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import struct
import tempfile

from .chunking import chunks, profile
from .codecs import compressor, decompress
from .core import (MAX_BLOCKS, MAX_FILES, MAX_HEADER, MAX_OUTPUT, _check_paths, _json_bytes,
                   _regular_kind, digest, files_in, valid_hash)

CONFIG_MAGIC = b"RKVCAS1\n"
SNAPSHOT_MAGIC = b"RKVSNP1\n"
OBJECT_MAGIC = b"RKVOBJ1\n"
OBJECT = struct.Struct("<8sBBHII32s32s")  # 84 bytes, including both raw/stored digests
CODECS = ("raw", "zlib", "zstd")


def _directory(path):
    if not stat.S_ISDIR(_regular_kind(path)):
        raise ValueError("CAS directory required")


def _publish(path, data):
    """No replacement: flush object before publishing its final immutable name."""
    fd, temporary = tempfile.mkstemp(prefix=".pending-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)
    finally:
        os.unlink(temporary)


def _record(magic, value):
    raw = _json_bytes(value)
    if len(raw) > MAX_HEADER:
        raise ValueError("CAS record too large")
    return magic + struct.pack("<Q", len(raw)) + hashlib.sha256(raw).digest() + raw


def _load_record(path, magic, limit=MAX_HEADER):
    if not stat.S_ISREG(_regular_kind(path)):
        raise ValueError("Regular CAS record required")
    with path.open("rb") as stream:
        prefix = stream.read(48)
        if len(prefix) != 48 or prefix[:8] != magic:
            raise ValueError("Invalid CAS record prefix")
        size = struct.unpack_from("<Q", prefix, 8)[0]
        if not 2 <= size <= limit or path.stat().st_size != 48 + size:
            raise ValueError("Invalid CAS record size")
        raw = stream.read(size)
    if hashlib.sha256(raw).digest() != prefix[16:]:
        raise ValueError("CAS record SHA-256 mismatch")
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate CAS JSON key")
            result[key] = value
        return result
    try:
        value = json.loads(raw, object_pairs_hook=unique)
    except (UnicodeError, RecursionError) as exc:
        raise ValueError("Invalid CAS JSON") from exc
    if _json_bytes(value) != raw:
        raise ValueError("Noncanonical CAS record")
    return value, digest(raw)


class Store:
    def __init__(self, root):
        self.root = Path(root)
        for path in (self.root, self.root / "objects", self.root / "snapshots"):
            _directory(path)
        self.config, self.config_sha256 = _load_record(self.root / "config.rkvc", CONFIG_MAGIC, 65536)
        c = self.config
        if (type(c) is not dict or set(c) != {"version", "compression", "chunker"}
                or type(c["version"]) is not int or c["version"] != 1 or c["compression"] not in CODECS
                or type(c["chunker"]) is not dict
                or c["chunker"] != profile(c["chunker"].get("mode"), c["chunker"].get("size"))):
            raise ValueError("Invalid CAS configuration")

    @classmethod
    def create(cls, root, *, compression="zstd", chunker="fixed", chunk_size=65536):
        if compression not in CODECS:
            raise ValueError("Unknown CAS compression")
        settings = profile(chunker, chunk_size)
        compressor(compression)  # dependency validation before creating any directories
        root = Path(root)
        root.mkdir(parents=True, exist_ok=False)
        (root / "objects").mkdir(); (root / "snapshots").mkdir()
        _publish(root / "config.rkvc", _record(CONFIG_MAGIC, {"version": 1, "compression": compression, "chunker": settings}))
        return cls(root)

    def object_path(self, key, create=False):
        if not valid_hash(key):
            raise ValueError("Invalid CAS object ID")
        shard = self.root / "objects" / key[:2]
        if create:
            shard.mkdir(exist_ok=True)
        _directory(shard)
        return shard / key[2:]

    def block(self, key, expected_size):
        path = self.object_path(key)
        if not stat.S_ISREG(_regular_kind(path)):
            raise ValueError("Regular CAS object required")
        with path.open("rb") as stream:
            header = stream.read(OBJECT.size)
            if len(header) != OBJECT.size:
                raise ValueError("Truncated CAS object")
            magic, codec, flags, reserved, raw_size, stored_size, raw_sha, stored_sha = OBJECT.unpack(header)
            maximum = self.config["chunker"].get("max_size", self.config["chunker"]["size"])
            if (magic != OBJECT_MAGIC or codec >= len(CODECS) or flags != 0 or reserved != 0
                    or type(expected_size) is not int or raw_size != expected_size or not 1 <= raw_size <= maximum
                    or not 1 <= stored_size <= raw_size or raw_sha.hex() != key
                    or path.stat().st_size != OBJECT.size + stored_size):
                raise ValueError("Invalid CAS object bounds or ID")
            name = CODECS[codec]
            if ((name == "raw" and stored_size != raw_size)
                    or (name != "raw" and (stored_size >= raw_size or name != self.config["compression"]))):
                raise ValueError("Invalid CAS codec policy")
            payload = stream.read(stored_size)
        if hashlib.sha256(payload).digest() != stored_sha:
            raise ValueError("CAS stored SHA-256 mismatch")
        raw = decompress(payload, name, raw_size)
        if digest(raw) != key:
            raise ValueError("CAS raw SHA-256 mismatch")
        return raw

    def add(self, source, *, label=""):
        if type(label) is not str or len(label) > 256:
            raise ValueError("Invalid snapshot label")
        source_path, store_path = Path(source).resolve(), self.root.resolve()
        if source_path.is_relative_to(store_path) or store_path.is_relative_to(source_path):
            raise ValueError("Source and CAS store must not overlap")
        compress = compressor(self.config["compression"])
        entries, checked, sizes = [], set(), []
        total = new = reused = new_bytes = new_raw = reused_raw = 0
        for path, relative in files_in(source):
            references, h, file_size = [], hashlib.sha256(), 0
            with path.open("rb") as stream:
                for raw in chunks(stream, self.config["chunker"]):
                    total += len(raw); file_size += len(raw); h.update(raw); sizes.append(len(raw))
                    if total > MAX_OUTPUT or len(sizes) > MAX_BLOCKS:
                        raise ValueError("CAS snapshot prototype limits exceeded")
                    key = digest(raw)
                    references.append({"id": key, "size": len(raw)})
                    if key in checked:
                        reused += 1; reused_raw += len(raw)
                        continue
                    target = self.object_path(key, create=True)
                    if target.exists() or target.is_symlink():
                        if self.block(key, len(raw)) != raw:
                            raise ValueError("Existing CAS object differs from source")
                        reused += 1; reused_raw += len(raw)
                    else:
                        encoded = compress(raw)
                        codec, payload = ((self.config["compression"], encoded) if len(encoded) < len(raw) else ("raw", raw))
                        data = OBJECT.pack(OBJECT_MAGIC, CODECS.index(codec), 0, 0, len(raw), len(payload),
                                           bytes.fromhex(key), hashlib.sha256(payload).digest()) + payload
                        try:
                            _publish(target, data)
                            new += 1; new_raw += len(raw); new_bytes += len(data)
                        except FileExistsError:
                            # Concurrent writers may race to add exactly the same object.
                            if self.block(key, len(raw)) != raw:
                                raise ValueError("Concurrent CAS object mismatch")
                            reused += 1; reused_raw += len(raw)
                    checked.add(key)
            entries.append({"path": relative, "size": file_size, "sha256": h.hexdigest(), "chunks": references})
        header = {"version": 1, "config_sha256": self.config_sha256, "label": label, "files": entries}
        raw = _json_bytes(header); snapshot_id = digest(raw)
        encoded = _record(SNAPSHOT_MAGIC, header)
        target = self.root / "snapshots" / (snapshot_id + ".rkvs")
        published = True
        try:
            _publish(target, encoded)
        except FileExistsError:
            _, actual = _load_record(target, SNAPSHOT_MAGIC)
            if actual != snapshot_id:
                raise ValueError("Existing snapshot ID mismatch")
            published = False
        return {"snapshot_id": snapshot_id, "files": len(entries), "raw_bytes": total,
                "chunk_references": len(sizes), "unique_snapshot_objects": len(checked),
                "new_objects": new, "reused_references": reused, "new_raw_bytes": new_raw, "reused_raw_bytes": reused_raw,
                "new_object_bytes": new_bytes, "new_snapshot_bytes": len(encoded) if published else 0,
                "new_written_bytes": new_bytes + (len(encoded) if published else 0),
                "snapshot_bytes": len(encoded), "snapshot_published": published,
                "chunk_sizes": sizes, "bytewise_source_hashed": True}

    def snapshot(self, snapshot_id):
        return Snapshot(self, snapshot_id)

    def stats(self):
        items = list(files_in(self.root))
        sizes = {rel: path.stat().st_size for path, rel in items}
        unexpected = [rel for rel in sizes if not (rel == "config.rkvc" or rel.startswith("objects/") or rel.startswith("snapshots/"))]
        if unexpected:
            raise ValueError("Unexpected files in CAS root")
        # Pending writes are not silently omitted from accounting. No concurrent
        # writer is supported during this audit; callers inspect a quiescent store.
        allocated = [_allocated(path) for path, _ in items]
        return {"logical_file_bytes": sum(sizes.values()), "files": len(sizes),
                "object_bytes": sum(n for p, n in sizes.items() if p.startswith("objects/")),
                "object_count": sum(p.startswith("objects/") for p in sizes),
                "snapshot_bytes": sum(n for p, n in sizes.items() if p.startswith("snapshots/")),
                "snapshot_count": sum(p.startswith("snapshots/") for p in sizes), "config_bytes": sizes["config.rkvc"],
                "allocated_file_data_bytes": sum(allocated) if all(n is not None for n in allocated) else None,
                "filesystem_directory_metadata_journal_unmeasured": True}


class Snapshot:
    def __init__(self, store, snapshot_id):
        if not valid_hash(snapshot_id):
            raise ValueError("Invalid snapshot ID")
        self.store, self.snapshot_id = store, snapshot_id
        self.header, actual = _load_record(store.root / "snapshots" / (snapshot_id + ".rkvs"), SNAPSHOT_MAGIC)
        h = self.header
        if (actual != snapshot_id or type(h) is not dict or set(h) != {"version", "config_sha256", "label", "files"}
                or type(h["version"]) is not int or h["version"] != 1 or h["config_sha256"] != store.config_sha256
                or type(h["label"]) is not str or len(h["label"]) > 256
                or type(h["files"]) is not list or len(h["files"]) > MAX_FILES):
            raise ValueError("Invalid snapshot manifest")
        self.files, self.offsets = {}, {}
        total = count = 0
        known = {}
        maximum = store.config["chunker"].get("max_size", store.config["chunker"]["size"])
        for entry in h["files"]:
            if (type(entry) is not dict or set(entry) != {"path", "size", "sha256", "chunks"}
                    or type(entry["size"]) is not int or not 0 <= entry["size"] <= MAX_OUTPUT
                    or not valid_hash(entry["sha256"]) or type(entry["chunks"]) is not list):
                raise ValueError("Invalid snapshot file")
            offsets = [0]
            for position, reference in enumerate(entry["chunks"]):
                if (type(reference) is not dict or set(reference) != {"id", "size"} or not valid_hash(reference["id"])
                        or type(reference["size"]) is not int or not 1 <= reference["size"] <= maximum):
                    raise ValueError("Invalid snapshot object reference")
                minimum = (store.config["chunker"].get("min_size", maximum)
                           if position + 1 < len(entry["chunks"]) else 1)
                if reference["size"] < minimum:
                    raise ValueError("Invalid non-final chunk size")
                if known.setdefault(reference["id"], reference["size"]) != reference["size"]:
                    raise ValueError("Conflicting snapshot object lengths")
                offsets.append(offsets[-1] + reference["size"])
            total += entry["size"]; count += len(entry["chunks"])
            if offsets[-1] != entry["size"] or total > MAX_OUTPUT or count > MAX_BLOCKS:
                raise ValueError("Snapshot size or reference limit mismatch")
            # Validate before a path is used as a dictionary key.
            _check_paths([entry["path"]])
            self.files[entry["path"]] = entry
            self.offsets[entry["path"]] = offsets
        _check_paths(entry["path"] for entry in h["files"])

    def close(self):
        pass  # File handles are per object; no decoded-data cache.

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def read_range(self, path, offset=0, length=None):
        entry = self.files[path]
        if length is None:
            length = entry["size"] - offset
        if (type(offset) is not int or type(length) is not int or offset < 0 or length < 0
                or offset + length > entry["size"] or length > 64 << 20):
            raise ValueError("Invalid CAS byte range")
        result = bytearray()
        if length:
            starts = self.offsets[path]
            i = bisect_right(starts, offset) - 1
            while i < len(entry["chunks"]) and starts[i] < offset + length:
                ref = entry["chunks"][i]
                raw = self.store.block(ref["id"], ref["size"])
                result.extend(raw[max(0, offset - starts[i]): min(len(raw), offset + length - starts[i])])
                i += 1
        data = bytes(result)
        if offset == 0 and length == entry["size"] and digest(data) != entry["sha256"]:
            raise ValueError("CAS file SHA-256 mismatch")
        return data

    def process(self, destination=None):
        for entry in self.header["files"]:
            h = hashlib.sha256()
            with _output(destination, entry["path"]) as stream:
                for ref in entry["chunks"]:
                    raw = self.store.block(ref["id"], ref["size"]); h.update(raw)
                    if stream is not None:
                        stream.write(raw)
            if h.hexdigest() != entry["sha256"]:
                raise ValueError("CAS file SHA-256 mismatch")
        return {"snapshot_id": self.snapshot_id, "files": len(self.files), "raw_bytes": sum(e["size"] for e in self.files.values()), "verified": True}


@contextmanager
def _output(destination, path):
    if destination is None:
        yield None
    else:
        target = Path(destination) / path
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            yield stream


def verify(root, snapshot_id):
    return Store(root).snapshot(snapshot_id).process()


def unpack(root, snapshot_id, destination):
    destination = Path(destination)
    if destination.resolve().is_relative_to(Path(root).resolve()):
        raise ValueError("Destination must be outside the CAS store")
    if destination.exists() or destination.is_symlink():
        raise FileExistsError("Destination must not already exist")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".rkv-cas-extract-", dir=destination.parent) as temp:
        stage = Path(temp) / "data"; stage.mkdir()
        result = Store(root).snapshot(snapshot_id).process(stage)
        if destination.exists() or destination.is_symlink():
            raise FileExistsError(destination)
        stage.rename(destination)
    return result


def _allocated(path):
    """Allocated data extents, not all filesystem overhead; null when unavailable."""
    if os.name != "nt":
        blocks = getattr(path.stat(), "st_blocks", None)
        return blocks * 512 if blocks is not None else None
    import ctypes
    from ctypes import wintypes
    class Standard(ctypes.Structure):
        _fields_ = [("allocation", ctypes.c_longlong), ("eof", ctypes.c_longlong),
                    ("links", wintypes.DWORD), ("pending", ctypes.c_ubyte), ("directory", ctypes.c_ubyte)]
    dll = ctypes.WinDLL("kernel32", use_last_error=True)
    create = dll.CreateFileW
    create.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    create.restype = wintypes.HANDLE
    get = dll.GetFileInformationByHandleEx
    get.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]; get.restype = wintypes.BOOL
    close = dll.CloseHandle; close.argtypes = [wintypes.HANDLE]; close.restype = wintypes.BOOL
    handle = create(str(path.resolve()), 0x80, 7, None, 3, 0, None)
    if handle == ctypes.c_void_p(-1).value:
        return None
    try:
        data = Standard()
        return data.allocation if get(handle, 1, ctypes.byref(data), ctypes.sizeof(data)) else None
    finally:
        close(handle)

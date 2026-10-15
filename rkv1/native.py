"""Explicit, provenance-checked optional CSV inverse and Gear scan kernels."""
import ctypes
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re


class NativeCSV:
    def __init__(self, library):
        path = Path(library).resolve(strict=True)
        metadata = path.with_name("native.json")
        if not path.is_file() or not metadata.is_file() or metadata.stat().st_size > 65536:
            raise ValueError("Native library requires adjacent release native.json")
        metadata_bytes = metadata.read_bytes()
        info = json.loads(metadata_bytes)
        if (type(info) is not dict or info.get("abi") != 1 or info.get("library") != path.name
                or type(info.get("bytes")) is not int or not 0 < info["bytes"] <= 64 << 20
                or path.stat().st_size != info["bytes"]
                or type(info.get("source_commit")) is not str or type(info.get("sha256")) is not str
                or not re.fullmatch(r"[0-9a-f]{40}", info["source_commit"])
                or not re.fullmatch(r"[0-9a-f]{64}", info["sha256"])):
            raise ValueError("Invalid native release provenance")
        if hashlib.sha256(path.read_bytes()).hexdigest() != info["sha256"]:
            raise ValueError("Native library SHA-256 mismatch")
        # This executes a caller-selected trusted library; a digest checks identity,
        # not publisher trust. Releases supply its source commit and digest.
        self.library = ctypes.CDLL(str(path))
        abi = self.library.rkv1_csv_abi_version
        abi.argtypes, abi.restype = [], ctypes.c_uint32
        if abi() != 1:
            raise ValueError("Unsupported native CSV ABI")
        self.function = self.library.rkv1_csv_decode
        self.function.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_size_t,
                                  ctypes.c_void_p, ctypes.c_size_t]
        self.function.restype = ctypes.c_ssize_t
        self.provenance = {**info, "metadata_bytes": len(metadata_bytes),
                           "metadata_sha256": hashlib.sha256(metadata_bytes).hexdigest()}

    def decode(self, coded, expected_size):
        if (type(coded) is not bytes or type(expected_size) is not int
                or not 1 <= expected_size <= 8 << 20 or not 28 <= len(coded) <= 2 * expected_size + 256):
            raise ValueError("Invalid native CSV input bounds")
        output = ctypes.create_string_buffer(expected_size)
        source = ctypes.c_char_p(coded)  # owned bytes remain alive for the entire call
        result = self.function(source, len(coded), expected_size, output, expected_size)
        if result != expected_size:
            raise ValueError(f"Native CSV inverse rejected input (status {result})")
        return output.raw


@lru_cache(maxsize=4)
def load_native(library):
    """Check/hash/load once per process; libraries must stay immutable while used."""
    return NativeCSV(library)


def select_decoder(backend, library):
    if backend == "python" and library is None:
        return None
    if backend == "rust" and library is not None:
        return load_native(str(Path(library).resolve())).decode
    raise ValueError("Use decoder_backend='python', or 'rust' with native_library")


class NativeGear(NativeCSV):
    """Gear ABI 1 is additive; the existing CSV ABI remains unchanged."""
    def __init__(self, library):
        super().__init__(library)
        features = self.provenance.get("features")
        if (type(self.provenance.get("gear_abi")) is not int or self.provenance["gear_abi"] != 1
                or type(features) is not list or any(type(f) is not str for f in features)
                or "gear-v1" not in features):
            raise ValueError("Native metadata does not declare Gear ABI 1")
        try:
            abi = self.library.rkv1_gear_abi_version
            abi.argtypes, abi.restype = [], ctypes.c_uint32
            if abi() != 1:
                raise ValueError("Unsupported native Gear ABI")
            self.scan_function = self.library.rkv1_gear_scan
        except AttributeError as exc:
            raise ValueError("Native library lacks Gear ABI") from exc
        self.scan_function.argtypes = [ctypes.c_void_p, ctypes.c_size_t,
            ctypes.POINTER(ctypes.c_uint64), ctypes.c_size_t,
            ctypes.POINTER(ctypes.c_uint64), ctypes.POINTER(ctypes.c_size_t),
            ctypes.POINTER(ctypes.c_size_t), ctypes.c_size_t]
        self.scan_function.restype = ctypes.c_ssize_t
        from .chunking import GEAR
        self.table = (ctypes.c_uint64 * 256)(*GEAR)

    def scan(self, data, scale, rolling=0, count=0):
        from .chunking import profile, MASK64, MAX_SIZE
        settings = profile("gear-v1", scale)
        if (type(data) is not bytes or len(data) > MAX_SIZE
                or type(rolling) is not int or not 0 <= rolling <= MASK64
                or type(count) is not int or not 0 <= count < settings["max_size"]
                or (count == 0 and rolling != 0)):
            raise ValueError("Invalid native Gear buffer/state")
        capacity = len(data) // settings["min_size"] + 1
        cuts = (ctypes.c_size_t * capacity)()
        h, n = ctypes.c_uint64(rolling), ctypes.c_size_t(count)
        result = self.scan_function(ctypes.c_char_p(data), len(data), self.table, scale,
                                   ctypes.byref(h), ctypes.byref(n), cuts, capacity)
        if not 0 <= result <= capacity or not 0 <= n.value < settings["max_size"]:
            raise ValueError(f"Native Gear scan rejected input (status {result})")
        positions = list(cuts[:result])
        if any(not 0 < b <= len(data) or b <= a for a, b in zip([0] + positions, positions)):
            raise ValueError("Invalid native Gear boundaries")
        return positions, h.value, n.value


@lru_cache(maxsize=4)
def load_native_gear(library):
    return NativeGear(library)


def select_scanner(backend, library, mode):
    if backend == "python" and library is None:
        return None
    if backend == "rust" and library is not None and mode == "gear-v1":
        return load_native_gear(str(Path(library).resolve())).scan
    raise ValueError("Use chunker_backend='python', or 'rust' with Gear profile and native_library")

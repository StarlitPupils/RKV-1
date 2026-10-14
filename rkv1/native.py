"""Explicit, provenance-checked optional CSV inverse kernel (ABI 1)."""
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

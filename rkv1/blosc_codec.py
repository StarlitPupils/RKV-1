"""Pinned C-Blosc byte API profiles; preflight bounds before native decoding."""
from functools import lru_cache
import os
import struct

PROFILES = {f"blosc-zstd-{name}-{width}": (flag, width)
            for name, flag in (("none", 0), ("shuffle", 1), ("bitshuffle", 4)) for width in (2, 4, 8)}
HEADER = struct.Struct("<BBBBIII")
MAX_RAW = 8 << 20
ENVIRONMENT = ("BLOSC_CLEVEL", "BLOSC_SHUFFLE", "BLOSC_TYPESIZE", "BLOSC_COMPRESSOR",
               "BLOSC_NTHREADS", "BLOSC_BLOCKSIZE", "BLOSC_SPLITMODE", "BLOSC_NOLOCK")


@lru_cache(maxsize=1)
def module():
    try:
        import blosc
    except ImportError as exc:
        raise ValueError('Blosc profiles need pip install "rkv1[scientific]"') from exc
    if blosc.__version__ != "1.11.4":
        raise ValueError("Blosc profiles require the pinned python-blosc 1.11.4")
    return blosc


def configured():
    if any(os.environ.get(key) for key in ENVIRONMENT):
        raise ValueError("BLOSC environment overrides conflict with the fixed profile")
    lib = module()
    lib.set_nthreads(1)
    lib.set_blocksize(65536)
    lib.set_releasegil(False)
    return lib


def compressor(profile):
    flag, width = PROFILES[profile]
    configured()  # Charge first import/setup inside the encoding phase.
    def compress(raw):
        lib = configured()
        return lib.compress(raw, typesize=width, clevel=3,
                            shuffle=lib.BITSHUFFLE if flag==4 else flag, cname="zstd")
    return compress


def preflight(stored, expected_size, profile):
    if type(expected_size) is not int or not 1 <= expected_size <= MAX_RAW or len(stored) < HEADER.size:
        raise ValueError("Invalid Blosc frame bounds")
    flag, width = PROFILES[profile]
    version, codec_version, flags, typesize, nbytes, blocksize, cbytes = HEADER.unpack_from(stored)
    if (version != 2 or codec_version != 1 or typesize != width or nbytes != expected_size
            or cbytes != len(stored) or not HEADER.size < cbytes < nbytes
            or not 1 <= blocksize <= min(65536, nbytes)
            or flags & ~0x97 or flags & 0xE0 != 0x80 or flags & 0x05 != flag or flags & 0x02):
        raise ValueError("Blosc frame size, codec, filter or typesize mismatch")


def decompress(stored, expected_size, profile):
    preflight(stored, expected_size, profile)
    lib = configured()
    if not lib.cbuffer_validate(stored):
        raise ValueError("Invalid Blosc frame structure")
    try:
        raw = lib.decompress(stored)
    except Exception as exc:
        raise ValueError("Invalid Blosc compressed block") from exc
    if len(raw) != expected_size:
        raise ValueError("Blosc decoded length mismatch")
    return raw

"""Fixed lossless codec profiles with bounded, single-frame decoding."""
import zlib
from .blosc_codec import PROFILES as BLOSC_PROFILES


def zstd_module():
    try:
        import zstandard
    except ImportError as exc:
        raise ValueError('Zstd needs the optional dependency: pip install "rkv1[bench]"') from exc
    return zstandard


def compressor(name):
    if not isinstance(name,str):raise ValueError("Unsupported compression profile")
    if name in BLOSC_PROFILES:
        from .blosc_codec import compressor as blosc_compressor
        return blosc_compressor(name)
    if name == "raw":
        return lambda raw: raw
    if name == "zlib":
        return lambda raw: zlib.compress(raw, 6)
    if name == "zstd":
        return zstd_module().ZstdCompressor(level=3, write_content_size=True, write_checksum=True).compress
    raise ValueError("Unsupported compression profile")


def decompress(stored, name, expected_size):
    if not isinstance(name,str):raise ValueError("Unsupported block codec")
    if name in BLOSC_PROFILES:
        from .blosc_codec import decompress as blosc_decompress
        raw = blosc_decompress(stored, expected_size, name)
    elif name == "raw":
        raw = stored
    elif name == "zlib":
        try:
            decoder = zlib.decompressobj()
            raw = decoder.decompress(stored, expected_size + 1)
        except zlib.error as exc:
            raise ValueError("Invalid compressed block") from exc
        if not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:
            raise ValueError("Malformed compressed block")
    elif name == "zstd":
        zstd = zstd_module()
        try:
            frame = zstd.get_frame_parameters(stored)
            if frame.content_size != expected_size or frame.window_size > expected_size or frame.dict_id != 0:
                raise ValueError("Zstd frame size, window or dictionary mismatch")
            raw = zstd.ZstdDecompressor().decompress(stored, max_output_size=expected_size,
                                                   read_across_frames=False, allow_extra_data=False)
        except zstd.ZstdError as exc:
            raise ValueError("Invalid Zstd frame") from exc
    else:
        raise ValueError("Unsupported block codec")
    if len(raw) != expected_size:
        raise ValueError("Decoded block length mismatch")
    return raw

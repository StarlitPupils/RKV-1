"""RKV v3: independently coded/hash-checked units and an authenticated index."""
import hashlib
import struct

from .codecs import decompress
from .transforms import csv_columns_decode, csv_columns_encode

ENTRY = struct.Struct("<IIIBBH32s")  # raw/stored/coded, codec, transform, reserved, raw SHA-256
MIN_UNIT = 4096
CODECS = ("raw", "zlib", "zstd")
TRANSFORMS = ("none", "csv-columns-v1")


def encode_units(raw, unit_size, compression, transform, compress):
    entries, payloads = [], []
    transformed = attempts = 0
    for start in range(0, len(raw), unit_size):
        unit = raw[start:start + unit_size]
        encoded = compress(unit)
        codec, payload = (compression, encoded) if len(encoded) < len(unit) else ("raw", unit)
        coded_size, chosen = len(unit), "none"
        if transform == "csv-columns-v1":
            attempts += 1
            candidate = csv_columns_encode(unit)
            if candidate is not None:
                candidate_payload = compress(candidate)
                # Every index entry has the same size for either transform.
                if len(candidate_payload) < len(payload):
                    codec, payload, coded_size, chosen = compression, candidate_payload, len(candidate), transform
                    transformed += 1
        entries.append(ENTRY.pack(len(unit), len(payload), coded_size, CODECS.index(codec),
                                  TRANSFORMS.index(chosen), 0, hashlib.sha256(unit).digest()))
        payloads.append(payload)
    index = b"".join(entries)
    return (index + b"".join(payloads),
            {"codec": "units-v1", "unit_count": len(entries), "index_size": len(index),
             "index_sha256": hashlib.sha256(index).hexdigest()}, transformed, attempts)


def validate_index(index, meta, unit_size, compression, transform):
    if len(index) != meta["index_size"] or hashlib.sha256(index).hexdigest() != meta["index_sha256"]:
        raise ValueError("Unit index SHA-256 mismatch or truncation")
    offsets = []
    cursor = meta["index_size"]
    for i in range(meta["unit_count"]):
        raw, stored, coded, codec_id, transform_id, reserved, _ = ENTRY.unpack_from(index, i * ENTRY.size)
        expected = min(unit_size, meta["raw_size"] - i * unit_size)
        if (raw != expected or not 1 <= stored <= raw or not 1 <= coded <= 2 * raw + 256
                or codec_id >= len(CODECS) or transform_id >= len(TRANSFORMS) or reserved != 0):
            raise ValueError("Invalid unit entry bounds or flags")
        codec, chosen = CODECS[codec_id], TRANSFORMS[transform_id]
        if ((codec == "raw" and (stored != raw or coded != raw or chosen != "none"))
                or (codec != "raw" and (stored >= raw or codec != compression))
                or (chosen == "none" and coded != raw)
                or (chosen != "none" and (codec == "raw" or chosen != transform))):
            raise ValueError("Invalid unit encoding policy")
        offsets.append(cursor)
        cursor += stored
    if cursor != meta["stored_size"]:
        raise ValueError("Unit payload size mismatch")
    return tuple(offsets)


def decode_unit(stream, body_start, meta, index, offsets, position):
    raw_size, stored_size, coded_size, codec, transform, _, checksum = ENTRY.unpack_from(index, position * ENTRY.size)
    stream.seek(body_start + meta["offset"] + offsets[position])
    stored = stream.read(stored_size)
    if len(stored) != stored_size:
        raise ValueError("Truncated unit")
    raw = decompress(stored, CODECS[codec], coded_size)
    if transform:
        raw = csv_columns_decode(raw, raw_size)
    if len(raw) != raw_size or hashlib.sha256(raw).digest() != checksum:
        raise ValueError("Unit SHA-256 mismatch or size mismatch")
    return raw

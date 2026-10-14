"""Streaming fixed boundaries and a frozen, simple Gear CDC profile.

gear-v1 is our single-mask profile, not a FastCDC reproduction. The parameter
is a mask scale; observed mean size depends on content and is measured.
"""
import hashlib

MAX_SIZE = 8 << 20
SEED = b"RKV1-GEAR-V1\0"
GEAR = tuple(int.from_bytes(hashlib.sha256(SEED + bytes([b])).digest()[:8], "little") for b in range(256))
MASK64 = (1 << 64) - 1


def profile(mode="fixed", size=65536):
    if type(size) is not int or not 4096 <= size <= MAX_SIZE:
        raise ValueError("Chunk scale must be 4096..8388608 bytes")
    if mode == "fixed":
        return {"mode": mode, "size": size}
    if mode == "gear-v1" and size <= 2 << 20 and size & (size - 1) == 0:
        return {"mode": mode, "size": size, "min_size": size // 4, "max_size": size * 4,
                "table_sha256": hashlib.sha256(b"".join(v.to_bytes(8, "little") for v in GEAR)).hexdigest()}
    raise ValueError("Unsupported chunker or Gear scale (power of two, at most 2 MiB)")


def chunks(stream, settings, *, read_size=1 << 20):
    if settings != profile(settings.get("mode"), settings.get("size")):
        raise ValueError("Invalid or unknown chunker profile")
    if type(read_size) is not int or not 1 <= read_size <= MAX_SIZE:
        raise ValueError("Invalid input buffer size")
    if settings["mode"] == "fixed":
        # Buffered files fill reads, but generic streams may return short reads.
        buffer = bytearray()
        while data := stream.read(read_size):
            buffer.extend(data)
            size = settings["size"]
            while len(buffer) >= size:
                yield bytes(buffer[:size])
                del buffer[:size]
        if buffer:
            yield bytes(buffer)
        return
    minimum, maximum, mask = settings["min_size"], settings["max_size"], settings["size"] - 1
    buffer, rolling = bytearray(), 0
    for_data = iter(lambda: stream.read(read_size), b"")
    for data in for_data:
        for byte in data:
            buffer.append(byte)
            rolling = ((rolling << 1) + GEAR[byte]) & MASK64
            if len(buffer) >= maximum or (len(buffer) >= minimum and rolling & mask == 0):
                yield bytes(buffer)
                buffer.clear()
                rolling = 0
    if buffer:
        yield bytes(buffer)

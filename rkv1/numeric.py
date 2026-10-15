"""Exact byte-lane transforms; never parse or round a numeric value.

Each block starts a new word/predictor grid. Incomplete words remain literal.
XOR uses the preceding word in this byte stream, not the previous channel sample.
"""
from itertools import accumulate
from operator import xor

POLICIES = {f"{name}-{width}-v1": (name, width)
            for name in ("byte-shuffle", "xor-shuffle") for width in (2, 4, 8)}


def encode(raw, policy):
    name, width = POLICIES[policy]
    end = len(raw) // width * width
    if end < 2 * width:
        return None
    body = raw[:end]
    if name == "xor-shuffle":
        body = body[:width] + bytes(a ^ b for a, b in zip(body[width:], body[:-width]))
    return b"".join(body[lane::width] for lane in range(width)) + raw[end:]


def decode(coded, expected_size, policy):
    if type(expected_size) is not int or expected_size < 0 or len(coded) != expected_size:
        raise ValueError("Invalid numeric transform length")
    name, width = POLICIES[policy]
    end = expected_size // width * width
    if end < 2 * width:
        raise ValueError("Invalid numeric transform word count")
    count = end // width
    result = bytearray(coded)
    for lane in range(width):
        column = coded[lane * count:(lane + 1) * count]
        if name == "xor-shuffle":
            column = bytes(accumulate(column, xor))
        result[lane:end:width] = column
    return bytes(result)

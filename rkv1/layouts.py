"""Encoding-only FITS routing; no numeric interpretation or rewritten headers."""
from dataclasses import dataclass

LAYOUTS = ("fixed", "fits-segments-v1")
FITS_POLICY = "fits-byte-shuffle-v1"
HEADER_LIMIT = 1 << 20


@dataclass(frozen=True)
class FitsImage:
    start: int
    end: int
    width: int


def fits_image(stream, size):
    """Recognize only one complete 2D float primary HDU; otherwise return None.

    Scan at most 1MiB, restore stream position, never parse float values. This is
    a routing whitelist, not a general FITS validator or an authenticity check.
    """
    original = stream.tell()
    try:
        if size < 2880 or size % 2880:
            return None
        stream.seek(0)
        keys = {}
        for offset in range(0, min(size, HEADER_LIMIT)//2880*2880, 2880):
            block = stream.read(2880)
            if len(block) != 2880 or (offset == 0 and not block.startswith(b"SIMPLE  =                    T")):
                return None
            for i in range(0, 2880, 80):
                card = block[i:i+80]
                card.decode("ascii")
                key = card[:8].decode("ascii").strip()
                if key == "END":
                    if card[8:].strip():
                        return None
                    if (not all(k in keys for k in ("BITPIX", "NAXIS", "NAXIS1", "NAXIS2"))
                            or keys["BITPIX"] not in (-32, -64) or keys["NAXIS"] != 2
                            or not all(1 <= keys[k] <= 100000 for k in ("NAXIS1", "NAXIS2"))
                            or keys.get("PCOUNT", 0) != 0 or keys.get("GCOUNT", 1) != 1
                            or keys.get("GROUPS", "F") != "F"):
                        return None
                    start = offset+2880
                    width = -keys["BITPIX"]//8
                    end = start+keys["NAXIS1"]*keys["NAXIS2"]*width
                    return FitsImage(start, end, width) if (end+2879)//2880*2880 == size else None
                if key in ("BITPIX", "NAXIS", "NAXIS1", "NAXIS2", "PCOUNT", "GCOUNT", "GROUPS"):
                    if key in keys or card[8:10] != b"= ":
                        return None
                    value = card[10:].split(b"/", 1)[0].strip()
                    keys[key] = value.decode("ascii") if key == "GROUPS" else int(value)
        return None
    except (ValueError, UnicodeError):
        return None
    finally:
        stream.seek(original)


def chunks(stream, size, chunk_size, layout, policy):
    """Yield (original bytes, actual transform candidate) without omitting bytes."""
    image = fits_image(stream, size) if layout != "fixed" or policy == FITS_POLICY else None
    ends = (image.start, image.end, size) if image and layout == "fits-segments-v1" else (size,)
    position = 0
    for end in ends:
        while position < end:
            raw = stream.read(min(chunk_size, end-position))
            if not raw:
                raise ValueError("Source truncated during layout encoding")
            selected = policy
            if policy == FITS_POLICY:
                selected = (f"byte-shuffle-{image.width}-v1" if image and
                            image.start <= position and position+len(raw) <= image.end else "none")
            yield raw, selected
            position += len(raw)
    if stream.read(1):
        raise ValueError("Source grew during layout encoding")

"""Reversible byte transforms; no floating-point parsing or text normalization."""
import re
import struct

CSV_MAGIC = b"RKVCSV1\n"
CSV_HEADER = struct.Struct("<BBHIIII")
MAX_ROWS = 65536
MAX_COLUMNS = 256
MAX_CELLS = 262144
NUMBER = re.compile(rb"[ \t]*[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?[ \t]*\Z")


def csv_columns_encode(raw):
    """Transpose complete numeric rows inside one chunk; preserve boundary bytes.

    The first line and incomplete last line remain literal. Quoted headers are
    therefore preserved. Quoted data, ragged rows and unsupported cells return
    None, so callers can use an ordinary lossless codec.
    """
    first, last = raw.find(b"\n"), raw.rfind(b"\n")
    if first < 0 or last <= first:
        return None
    prefix, suffix = raw[:first + 1], raw[last + 1:]
    lines = raw[first + 1:last].split(b"\n")
    if not 2 <= len(lines) <= MAX_ROWS:
        return None
    delimiter = b";" if b";" in lines[0] else b"," if b"," in lines[0] else None
    if delimiter is None:
        return None
    rows, endings = [], bytearray()
    columns = None
    for line in lines:
        crlf = line.endswith(b"\r")
        cells = (line[:-1] if crlf else line).split(delimiter)
        if columns is None:
            columns = len(cells)
            if not 2 <= columns <= MAX_COLUMNS or len(lines) * columns > MAX_CELLS:
                return None
        if len(cells) != columns or any(not NUMBER.fullmatch(cell) for cell in cells):
            return None
        rows.append(cells)
        endings.append(int(crlf))
    values = b"\n".join(rows[r][c] for c in range(columns) for r in range(len(rows)))
    return (CSV_MAGIC + CSV_HEADER.pack(delimiter[0], 0, columns, len(rows), len(prefix), len(suffix), len(raw))
            + prefix + suffix + bytes(endings) + values)


def csv_columns_decode(coded, expected_size):
    if len(coded) < len(CSV_MAGIC) + CSV_HEADER.size or coded[:8] != CSV_MAGIC:
        raise ValueError("Invalid CSV transform header")
    delim, flags, columns, rows, prefix_size, suffix_size, original_size = CSV_HEADER.unpack_from(coded, 8)
    if (delim not in (ord(","), ord(";")) or flags != 0 or original_size != expected_size
            or not 2 <= columns <= MAX_COLUMNS or not 2 <= rows <= MAX_ROWS or rows * columns > MAX_CELLS):
        raise ValueError("Invalid CSV transform dimensions")
    start = 8 + CSV_HEADER.size
    values_start = start + prefix_size + suffix_size + rows
    if values_start > len(coded) or prefix_size + suffix_size > expected_size:
        raise ValueError("Invalid CSV transform bounds")
    prefix = coded[start:start + prefix_size]
    suffix = coded[start + prefix_size:start + prefix_size + suffix_size]
    endings = coded[start + prefix_size + suffix_size:values_start]
    if any(value not in (0, 1) for value in endings):
        raise ValueError("Invalid CSV newline map")
    # Cap splitting before constructing Python objects for malformed payloads.
    cells = coded[values_start:].split(b"\n", rows * columns)
    if len(cells) != rows * columns or any(not NUMBER.fullmatch(cell) for cell in cells):
        raise ValueError("Invalid CSV transform cells")
    # Check the complete reconstructed size before allocating the output.
    calculated = prefix_size + suffix_size + sum(map(len, cells)) + rows * columns + sum(endings)
    if calculated != expected_size:
        raise ValueError("CSV transform output length mismatch")
    delimiter = bytes([delim])
    result = bytearray(prefix)
    for r in range(rows):
        result.extend(delimiter.join(cells[c * rows + r] for c in range(columns)))
        result.extend(b"\r\n" if endings[r] else b"\n")
    result.extend(suffix)
    return bytes(result)

"""Compare a candidate C ABI CSV decoder to exact Python output; no timing claim."""
import argparse
import ctypes
import random

from rkv1.transforms import csv_columns_decode, csv_columns_encode


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("library")
    args = parser.parse_args()
    library = ctypes.CDLL(args.library)
    library.rkv1_csv_abi_version.restype = ctypes.c_uint32
    assert library.rkv1_csv_abi_version() == 1
    decoder = library.rkv1_csv_decode
    decoder.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_size_t]
    decoder.restype = ctypes.c_ssize_t
    rng = random.Random(20261014)
    values = [b"+001", b"-0", b"1.", b".5", b"1.e+00", b" -2.1E-9\t", b"001e-02"]
    for columns in (2, 9, 82, 256):
        for delimiter in (b",", b";"):
            raw = b'"opaque header"\r\n'
            for row in range(50):
                raw += delimiter.join(rng.choice(values) for _ in range(columns)) + (b"\r\n" if row % 2 else b"\n")
            raw += b"opaque\0tail"
            coded = csv_columns_encode(raw)
            assert coded is not None
            output = ctypes.create_string_buffer(len(raw))
            source = ctypes.c_char_p(coded)
            assert decoder(source, len(coded), len(raw), output, len(output)) == len(raw)
            assert output.raw == csv_columns_decode(coded, len(raw)) == raw
            bad = bytearray(coded); bad[9] = 1
            assert decoder(ctypes.c_char_p(bytes(bad)), len(bad), len(raw), output, len(output)) < 0
    print("native ABI + exact Python differential checks passed (8 numeric/mixed-newline tables)")


if __name__ == "__main__":
    main()

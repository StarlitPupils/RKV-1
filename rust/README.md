# Rust format boundary and CSV candidate

`cargo test --manifest-path rust/Cargo.toml`

The crate tests the 48-byte format prefix and range-to-chunk arithmetic, unchanged
for manifest versions 1/2/3. csv.rs adds an exact CSV-COLUMNS-V1 inverse transform
and C ABI candidate following the v0.4 lexical/reconstruction profiles. It never
converts floating-point values or normalizes literals/newlines. Dimensions,
numeric grammar, newline map and exact output length remain checked.

It is not a complete archive decoder or hash verifier. Python owns codecs,
index/unit/parent/file SHA-256 and restoration. v0.5 measurements use Python only;
no local Rust speedup is claimed. Windows/Linux CI tests the Rust functions and
compares the shared library's output against eight Python-generated tables.

`cargo build --release --manifest-path rust/Cargo.toml` creates cdylib and rlib.
`rkv1_csv_abi_version()` returns 1. The C ABI `rkv1_csv_decode(input, input_len,
expected_size, output, output_capacity)` returns restored length or -1/-2/-3.
The caller must supply valid live pointers and sufficient buffers; dimensions
do not validate pointers. Panics that unwind are contained, not arbitrary faults
or allocator aborts. See [Rust linkage](https://doc.rust-lang.org/reference/linkage.html)
and [catch_unwind](https://doc.rust-lang.org/std/panic/fn.catch_unwind.html).

Release native ZIPs contain the library and native.json with source commit,
platform, ABI, compiler and binary SHA-256. These are platform/build candidates,
not universal portable binaries. The next milestone must measure Python/native
using identical archives, include binary deployment cost, and preserve hashes.

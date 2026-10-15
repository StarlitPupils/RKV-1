# Rust format boundary, exact CSV kernel and streaming Gear scanner

`cargo test --manifest-path rust/Cargo.toml`

The crate tests the 48-byte format prefix and range-to-chunk arithmetic, unchanged
for manifest versions 1/2/3. csv.rs adds an exact CSV-COLUMNS-V1 inverse transform
and C ABI candidate following the v0.4 lexical/reconstruction profiles. It never
converts floating-point values or normalizes literals/newlines. Dimensions,
numeric grammar, newline map and exact output length remain checked.

It is not a complete archive decoder or hash verifier. Python owns codecs,
index/unit/parent/file SHA-256 and restoration. v0.5 measurements used Python only.
v0.6 uses a frozen v0.5 Windows release binary with the same csv.rs source for
matched local CPU measurements, including FFI/copies and binary deployment cost.
See [NATIVE.md](../docs/NATIVE.md) and [results](../results/v0.6.0/SUMMARY.md).
Windows/Linux CI tests functions, Python differential cases, malformed payloads,
v1/v2/v3 archives, integrity and the matched benchmark protocol. Linux correctness
CI is not a cross-machine timing result.

`cargo build --release --manifest-path rust/Cargo.toml` creates cdylib and rlib.
`rkv1_csv_abi_version()` returns 1. The C ABI `rkv1_csv_decode(input, input_len,
expected_size, output, output_capacity)` returns restored length or -1/-2/-3.
The caller must supply valid live pointers and sufficient buffers; dimensions
do not validate pointers. Panics that unwind are contained, not arbitrary faults
or allocator aborts. See [Rust linkage](https://doc.rust-lang.org/reference/linkage.html)
and [catch_unwind](https://doc.rust-lang.org/std/panic/fn.catch_unwind.html).

Release native ZIPs contain the library and native.json with source commit,
platform, ABI, compiler and binary SHA-256. These are platform/build candidates,
not universal portable binaries. Readers select a trusted release library explicitly;
the optional Python wrapper checks the adjacent metadata and caches the loaded
library per process. A checksum establishes identity, not publisher trust.

v0.8 adds gear.rs after profiling the frozen v0.7 Python Gear loop. The scanner
implements the same u64 recurrence, minimum/maximum bounds and single mask;
Python supplies the validated 256-element table. It returns buffer-relative cut
positions and carries rolling/pending-byte state across short reads. It does not
compress, hash, publish objects or restore snapshots. CSV ABI 1 is unchanged;
Gear has a separate ABI 1 export and requires gear_abi/features provenance.
See [the frozen local experiment](../results/v0.8.0/SUMMARY.md). CI differential
checks cover profiles, buffers, zero/random data, final residuals, complete CAS
trees, existing-object corruption and matched campaign workers. Python remains
the default; there is no automatic native selection.

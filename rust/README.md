# Rust core boundary

`cargo test --manifest-path rust/Cargo.toml`

This initial crate tests the 48-byte format prefix and range-to-chunk arithmetic.
It is scaffolding, not a complete archive decoder, checksum verifier, or Python
extension. The Python reference is authoritative for v0.2.0. The 48-byte prefix
is unchanged for manifest versions 1 and 2. Migrate measured hot
paths only after E0 profiling; keep bytewise differential tests against Python.

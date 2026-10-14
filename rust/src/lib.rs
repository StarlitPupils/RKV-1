//! Format boundary scaffold. This is NOT a full decoder or integrity verifier.
//! Python remains the reference implementation until profiling justifies migration.

pub const MAGIC: &[u8; 8] = b"RKV1\r\n\x1a\n";
pub const PREFIX_SIZE: usize = 48;
pub const MAX_HEADER: u64 = 64 << 20;

#[derive(Debug, PartialEq, Eq)]
pub struct Prefix {
    pub manifest_len: u64,
    pub manifest_sha256: [u8; 32],
}

/// Read fixed-size framing only. The caller must hash and validate the manifest.
pub fn parse_prefix(bytes: &[u8]) -> Result<Prefix, &'static str> {
    if bytes.len() != PREFIX_SIZE {
        return Err("prefix must be exactly 48 bytes");
    }
    if &bytes[..8] != MAGIC {
        return Err("invalid magic");
    }
    let manifest_len = u64::from_le_bytes(bytes[8..16].try_into().unwrap());
    if !(2..=MAX_HEADER).contains(&manifest_len) {
        return Err("manifest length exceeds limits");
    }
    Ok(Prefix {
        manifest_len,
        manifest_sha256: bytes[16..48].try_into().unwrap(),
    })
}

/// Enumerate the logical chunks touched by a validated byte range.
pub fn chunk_span(offset: u64, length: u64, size: u64, chunk: u64) -> Result<std::ops::Range<u64>, &'static str> {
    if chunk == 0 || chunk > 8 << 20 {
        return Err("invalid chunk size");
    }
    let end = offset.checked_add(length).ok_or("range overflow")?;
    if end > size {
        return Err("range outside file");
    }
    let start_chunk = offset / chunk;
    if length == 0 {
        return Ok(start_chunk..start_chunk);
    }
    Ok(start_chunk..((end - 1) / chunk + 1))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn prefix_layout() {
        let mut bytes = [0; PREFIX_SIZE];
        bytes[..8].copy_from_slice(MAGIC);
        bytes[8..16].copy_from_slice(&128_u64.to_le_bytes());
        assert_eq!(parse_prefix(&bytes).unwrap().manifest_len, 128);
        bytes[0] ^= 1;
        assert!(parse_prefix(&bytes).is_err());
    }

    #[test]
    fn truncated_and_oversize_prefix() {
        assert!(parse_prefix(&[0; 47]).is_err());
        let mut bytes = [0; PREFIX_SIZE];
        bytes[..8].copy_from_slice(MAGIC);
        bytes[8..16].copy_from_slice(&(MAX_HEADER + 1).to_le_bytes());
        assert!(parse_prefix(&bytes).is_err());
    }

    #[test]
    fn range_boundaries_and_overflow() {
        assert_eq!(chunk_span(511, 2, 1024, 512).unwrap(), 0..2);
        assert_eq!(chunk_span(1024, 0, 1024, 512).unwrap(), 2..2);
        assert!(chunk_span(1024, 1, 1024, 512).is_err());
        assert!(chunk_span(u64::MAX, 1, u64::MAX, 512).is_err());
        assert!(chunk_span(0, 0, 0, 0).is_err());
    }
}

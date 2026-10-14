//! Exact CSV-COLUMNS-V1 inverse transform. No floating-point conversion.

pub const MAX_RAW: usize = 8 << 20;

fn number(bytes: &[u8]) -> bool {
    let mut i = 0;
    while i < bytes.len() && matches!(bytes[i], b' ' | b'\t') { i += 1; }
    if i < bytes.len() && matches!(bytes[i], b'+' | b'-') { i += 1; }
    let start = i;
    while i < bytes.len() && bytes[i].is_ascii_digit() { i += 1; }
    let integer = i - start;
    let mut fractional = 0;
    if i < bytes.len() && bytes[i] == b'.' {
        i += 1;
        let start = i;
        while i < bytes.len() && bytes[i].is_ascii_digit() { i += 1; }
        fractional = i - start;
    }
    if integer == 0 && fractional == 0 { return false; }
    if i < bytes.len() && matches!(bytes[i], b'e' | b'E') {
        i += 1;
        if i < bytes.len() && matches!(bytes[i], b'+' | b'-') { i += 1; }
        let start = i;
        while i < bytes.len() && bytes[i].is_ascii_digit() { i += 1; }
        if i == start { return false; }
    }
    while i < bytes.len() && matches!(bytes[i], b' ' | b'\t') { i += 1; }
    i == bytes.len()
}

fn u32_at(bytes: &[u8], position: usize) -> usize {
    u32::from_le_bytes(bytes[position..position + 4].try_into().unwrap()) as usize
}

pub fn decode(coded: &[u8], expected: usize) -> Result<Vec<u8>, &'static str> {
    if expected == 0 || expected > MAX_RAW || coded.len() > 2 * expected + 256
        || coded.len() < 28 || &coded[..8] != b"RKVCSV1\n" {
        return Err("invalid CSV header/size");
    }
    let delimiter = coded[8];
    let columns = u16::from_le_bytes(coded[10..12].try_into().unwrap()) as usize;
    let rows = u32_at(coded, 12);
    let prefix = u32_at(coded, 16);
    let suffix = u32_at(coded, 20);
    if !matches!(delimiter, b',' | b';') || coded[9] != 0
        || !(2..=256).contains(&columns) || !(2..=65536).contains(&rows)
        || rows * columns > 262144 || u32_at(coded, 24) != expected
        || prefix + suffix > expected {
        return Err("invalid CSV dimensions/flags");
    }
    let endings_start = 28 + prefix + suffix;
    let values_start = endings_start + rows;
    if values_start > coded.len() { return Err("invalid CSV bounds"); }
    let endings = &coded[endings_start..values_start];
    if endings.iter().any(|e| *e > 1) { return Err("invalid newline map"); }
    let cell_count = rows * columns;
    let mut cells = Vec::with_capacity(cell_count);
    let mut cell_bytes = 0;
    for cell in coded[values_start..].split(|b| *b == b'\n') {
        if cells.len() == cell_count || !number(cell) { return Err("invalid numeric cells"); }
        cell_bytes += cell.len();
        cells.push(cell);
    }
    if cells.len() != cell_count
        || prefix + suffix + cell_bytes + cell_count + endings.iter().map(|e| *e as usize).sum::<usize>() != expected {
        return Err("CSV output length mismatch");
    }
    let mut output = Vec::with_capacity(expected);
    output.extend_from_slice(&coded[28..28 + prefix]);
    for (row, ending) in endings.iter().enumerate() {
        for column in 0..columns {
            if column != 0 { output.push(delimiter); }
            output.extend_from_slice(cells[column * rows + row]);
        }
        if *ending != 0 { output.push(b'\r'); }
        output.push(b'\n');
    }
    output.extend_from_slice(&coded[28 + prefix..28 + prefix + suffix]);
    Ok(output)
}

#[no_mangle]
pub extern "C" fn rkv1_csv_abi_version() -> u32 { 1 }

/// Copy exact restored bytes into caller-owned output. Returns size or negative error.
///
/// # Safety
/// Non-null input/output pointers must refer to readable input_len and writable
/// output_capacity bytes for the call's duration. Bounds do not validate pointers.
#[no_mangle]
pub unsafe extern "C" fn rkv1_csv_decode(input: *const u8, input_len: usize, expected: usize,
                                        output: *mut u8, output_capacity: usize) -> isize {
    if input.is_null() || output.is_null() || expected == 0 || expected > MAX_RAW
        || output_capacity < expected || input_len > 2 * expected + 256 { return -1; }
    let restored = std::panic::catch_unwind(|| {
        decode(std::slice::from_raw_parts(input, input_len), expected)
    });
    match restored {
        Ok(Ok(bytes)) => {
            std::ptr::copy_nonoverlapping(bytes.as_ptr(), output, bytes.len());
            bytes.len() as isize
        },
        Ok(Err(_)) => -2,
        Err(_) => -3,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn fixture() -> (Vec<u8>, Vec<u8>) {
        let raw = b"header\n+01.00; -0.0 ;1e-09\n002;3.1400;9E+2\r\ntail".to_vec();
        let mut coded = b"RKVCSV1\n".to_vec();
        coded.extend_from_slice(&[b';', 0]);
        coded.extend_from_slice(&3_u16.to_le_bytes());
        for value in [2_u32, 7, 4, raw.len() as u32] { coded.extend_from_slice(&value.to_le_bytes()); }
        coded.extend_from_slice(b"header\ntail\0\x01+01.00\n002\n -0.0 \n3.1400\n1e-09\n9E+2");
        (coded, raw)
    }

    #[test]
    fn exact_literal_numbers() {
        for value in ["+001", "-0", "1.", ".5", "1.e+00", "  -2.1E-9\t", "001e-02"] {
            assert!(number(value.as_bytes()), "{}", value);
        }
        for value in ["", " ", ".", "1e", "e3", "1 2", "1 e2", "NaN", "Inf", "1,2", "--1", "1\n"] {
            assert!(!number(value.as_bytes()), "{}", value);
        }
    }

    #[test]
    fn exact_mixed_endings_and_boundaries() {
        let (coded, raw) = fixture();
        assert_eq!(decode(&coded, raw.len()).unwrap(), raw);
        let mut corrupt = coded.clone(); corrupt[9] = 1;
        assert!(decode(&corrupt, raw.len()).is_err());
        assert!(decode(&coded[..27], raw.len()).is_err());
        assert!(decode(&coded, raw.len() + 1).is_err());
    }

    #[test]
    fn ffi_bounds_and_exact_copy() {
        let (coded, raw) = fixture();
        let mut output = vec![0; raw.len()];
        unsafe {
            assert_eq!(rkv1_csv_decode(coded.as_ptr(), coded.len(), raw.len(), output.as_mut_ptr(), output.len()), raw.len() as isize);
            assert_eq!(output, raw);
            assert_eq!(rkv1_csv_decode(std::ptr::null(), 0, raw.len(), output.as_mut_ptr(), output.len()), -1);
            assert_eq!(rkv1_csv_decode(coded.as_ptr(), coded.len(), raw.len(), output.as_mut_ptr(), 1), -1);
        }
    }
}

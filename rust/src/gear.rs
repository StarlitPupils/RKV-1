//! Streaming boundary scan for the frozen Python gear-v1 recurrence.
//! Tables are supplied by the validated Python profile; no payload or hash policy changes.

pub const MAX_INPUT: usize = 8 << 20;

pub fn scan(input: &[u8], table: &[u64; 256], scale: usize, mut rolling: u64,
            mut count: usize) -> Result<(Vec<usize>, u64, usize), &'static str> {
    if !(4096..=2 << 20).contains(&scale) || !scale.is_power_of_two()
        || input.len() > MAX_INPUT || count >= scale * 4 || (count == 0 && rolling != 0) {
        return Err("invalid Gear input/state/scale");
    }
    let minimum = scale / 4;
    let maximum = scale * 4;
    let mask = (scale - 1) as u64;
    let mut cuts = Vec::with_capacity(input.len() / minimum + 1);
    for (i, byte) in input.iter().enumerate() {
        rolling = rolling.wrapping_shl(1).wrapping_add(table[*byte as usize]);
        count += 1;
        if count >= maximum || (count >= minimum && rolling & mask == 0) {
            cuts.push(i + 1);
            rolling = 0;
            count = 0;
        }
    }
    Ok((cuts, rolling, count))
}

#[no_mangle]
pub extern "C" fn rkv1_gear_abi_version() -> u32 { 1 }

/// Return cut count or negative status. Updates state only on success.
///
/// # Safety
/// Pointers must be aligned, non-overlapping, and valid for their declared lengths;
/// table points to 256 u64s, rolling/count to one writable value each, and cuts to
/// capacity writable usize values. Inputs must remain alive for this call.
#[no_mangle]
pub unsafe extern "C" fn rkv1_gear_scan(input: *const u8, input_len: usize,
        table: *const u64, scale: usize, rolling: *mut u64, count: *mut usize,
        cuts: *mut usize, capacity: usize) -> isize {
    if input.is_null() || table.is_null() || rolling.is_null() || count.is_null()
        || cuts.is_null() || input_len > MAX_INPUT { return -1; }
    let result = std::panic::catch_unwind(|| {
        scan(std::slice::from_raw_parts(input, input_len), &*(table as *const [u64; 256]),
             scale, *rolling, *count)
    });
    match result {
        Ok(Ok((positions, next_rolling, next_count))) => {
            if positions.len() > capacity { return -2; }
            std::ptr::copy_nonoverlapping(positions.as_ptr(), cuts, positions.len());
            *rolling = next_rolling;
            *count = next_count;
            positions.len() as isize
        },
        Ok(Err(_)) => -3,
        Err(_) => -4,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn streaming_states_match_single_buffer() {
        let table = std::array::from_fn(|i| (i as u64).wrapping_mul(0x9e3779b97f4a7c15));
        let input: Vec<u8> = (0..100000).map(|i| ((i * 73 + i / 113) % 256) as u8).collect();
        for scale in [4096, 65536, 2 << 20] {
            let (expected, h, n) = scan(&input, &table, scale, 0, 0).unwrap();
            for buffer in [1, 17, 4096, 8192] {
                let (mut rolling, mut count, mut offset) = (0, 0, 0);
                let mut positions = Vec::new();
                for data in input.chunks(buffer) {
                    let (cuts, next_h, next_n) = scan(data, &table, scale, rolling, count).unwrap();
                    positions.extend(cuts.iter().map(|p| p + offset));
                    rolling = next_h; count = next_n; offset += data.len();
                }
                assert_eq!((positions, rolling, count), (expected.clone(), h, n));
            }
        }
    }

    #[test]
    fn ffi_capacity_and_error_leave_state_unchanged() {
        let input = vec![0_u8; 20000];
        let table = [0_u64; 256];
        let (mut rolling, mut count, mut cuts) = (0, 0, [0_usize; 32]);
        unsafe {
            assert_eq!(rkv1_gear_scan(input.as_ptr(), input.len(), table.as_ptr(), 4096,
                       &mut rolling, &mut count, cuts.as_mut_ptr(), 0), -2);
            assert_eq!((rolling, count), (0, 0));
            let result = rkv1_gear_scan(input.as_ptr(), input.len(), table.as_ptr(), 4096,
                       &mut rolling, &mut count, cuts.as_mut_ptr(), cuts.len());
            assert_eq!(result, 19);
            assert_eq!(cuts[0], 1024);
            assert_eq!(count, 544);
            assert!(rkv1_gear_scan(input.as_ptr(), input.len(), table.as_ptr(), 5000,
                       &mut rolling, &mut count, cuts.as_mut_ptr(), cuts.len()) < 0);
            assert_eq!(count, 544);
        }
        assert!(scan(&input, &table, 4096, 1, 0).is_err());
        assert!(scan(&input, &table, 4096, 0, 16384).is_err());
    }
}

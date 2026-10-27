#![cfg_attr(not(test), no_std)]

#[cfg(not(test))]
#[panic_handler]
fn panic(_: &core::panic::PanicInfo) -> ! { loop { core::hint::spin_loop(); } }

#[no_mangle]
pub extern "C" fn rkv_postings_abi() -> u32 { 1 }

/// Decode exactly count canonical unsigned u64 varints; no allocation.
/// Caller owns valid, non-overlapping buffers with the supplied bounds.
/// Return 0 success, 1 invalid pointer/bound/count, 2 truncated,
/// 3 overflow, 4 noncanonical; output must be ignored on any error.
/// consumed is set to zero on failure after its pointer is validated.
#[no_mangle]
pub unsafe extern "C" fn rkv_postings_decode(
    src: *const u8, src_len: usize, count: usize,
    out: *mut u64, out_cap: usize, consumed: *mut usize,
) -> u32 {
    if consumed.is_null() || (consumed as usize) % core::mem::align_of::<usize>() != 0 { return 1; }
    unsafe { *consumed = 0; }
    if src_len > 65 * 1024 * 1024 || count > 2_000_000 || out_cap < count ||
       (src_len > 0 && src.is_null()) || (count > 0 && out.is_null()) ||
       (!out.is_null() && (out as usize) % core::mem::align_of::<u64>() != 0) { return 1; }
    let mut at = 0usize;
    for j in 0..count {
        let mut value = 0u64;
        let mut complete = false;
        for n in 0..10usize {
            if at >= src_len { return 2; }
            let byte = unsafe { *src.add(at) }; at += 1;
            if n == 9 && byte > 1 { return 3; }
            value |= ((byte & 127) as u64) << (7 * n);
            if byte & 128 == 0 {
                if n > 0 && byte == 0 { return 4; }
                complete = true; break;
            }
        }
        if !complete { return 3; }
        unsafe { *out.add(j) = value; }
    }
    unsafe { *consumed = at; } 0
}

#[cfg(test)]
mod tests {
    use super::*;
    fn decode(raw: &[u8], count: usize) -> (u32, [u64; 8], usize) {
        let mut out = [999u64;8]; let mut used = 999usize;
        let code = unsafe { rkv_postings_decode(raw.as_ptr(),raw.len(),count,out.as_mut_ptr(),8,&mut used) };
        (code,out,used)
    }
    #[test]
    fn canonical_goldens_and_no_extra_read_or_write() {
        let (code,out,used)=decode(&[0,1,127,128,1,255,127,9],5);
        assert_eq!(code,0); assert_eq!(&out[..5],&[0,1,127,128,16383]);
        assert_eq!(&out[5..],&[999,999,999]); assert_eq!(used,7);
        let (code,out,used)=decode(&[255,255,255,255,255,255,255,255,255,1],1);
        assert_eq!(code,0);assert_eq!(out[0],u64::MAX);assert_eq!(used,10);
    }
    #[test]
    fn rejects_nonminimal_truncated_and_overflow() {
        for raw in [&[128,0][..],&[129,0][..],&[255,255,0][..]] {let (code,_,used)=decode(raw,1);assert_eq!(code,4);assert_eq!(used,0);}
        assert_eq!(decode(&[],1).0,2);assert_eq!(decode(&[128],1).0,2);
        assert_eq!(decode(&[255;10],1).0,3);
        assert_eq!(decode(&[255,255,255,255,255,255,255,255,255,2],1).0,3);
    }
    #[test]
    fn output_capacity_bounds_and_zero_values() {
        let mut out=[777u64;2];let mut used=9usize;
        let code=unsafe {rkv_postings_decode([1,2].as_ptr(),2,2,out.as_mut_ptr(),1,&mut used)};
        assert_eq!(code,1);assert_eq!(out,[777,777]);assert_eq!(used,0);
        let code=unsafe {rkv_postings_decode(core::ptr::null(),0,0,core::ptr::null_mut(),0,&mut used)};
        assert_eq!(code,0);assert_eq!(used,0);
    }
    #[test]
    fn invalid_nulls_counts_and_alignment() {
        let mut out=[0u64;1];let mut used=0usize;
        assert_eq!(unsafe {rkv_postings_decode(core::ptr::null(),1,1,out.as_mut_ptr(),1,&mut used)},1);
        assert_eq!(unsafe {rkv_postings_decode([1].as_ptr(),1,1,core::ptr::null_mut(),1,&mut used)},1);
        assert_eq!(unsafe {rkv_postings_decode([1].as_ptr(),1,1,out.as_mut_ptr(),1,core::ptr::null_mut())},1);
        assert_eq!(unsafe {rkv_postings_decode([1].as_ptr(),1,2_000_001,out.as_mut_ptr(),1,&mut used)},1);
        assert_eq!(unsafe {rkv_postings_decode([1].as_ptr(),1,1,(out.as_mut_ptr() as *mut u8).add(1) as *mut u64,1,&mut used)},1);
    }
}

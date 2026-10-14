"""CPU-only end-to-end benchmarks, isolated per method; no model-quality claims."""
from __future__ import annotations

import ctypes
import hashlib
import importlib.metadata
import io
import json
import lzma
import math
import os
from pathlib import Path
import platform
import random
import shutil
import statistics
import subprocess
import sys
import tarfile
import tempfile
import time
import zlib

from .core import Archive, DEFAULT_CHUNK, assert_tree_equal, files_in, pack, unpack, valid_path

MAX_BENCH = 64 << 20


def canonical_tar(source):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w", format=tarfile.PAX_FORMAT) as tar:
        for path, rel in files_in(source):
            info = tarfile.TarInfo(rel)
            info.size, info.mode, info.mtime, info.uid, info.gid = path.stat().st_size, 0o644, 0, 0, 0
            with path.open("rb") as stream:
                tar.addfile(info, stream)
    return buffer.getvalue()


def restore_tar(raw, destination):
    """Only called on this benchmark's own verified baseline stream."""
    destination.mkdir()
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as tar:
        for member in tar:
            if not member.isfile():
                raise ValueError("Unexpected non-regular TAR member")
            target = destination.joinpath(*valid_path(member.name).parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            with tar.extractfile(member) as src, target.open("xb") as out:
                shutil.copyfileobj(src, out)


def codec(name):
    if name == "tar-raw":
        return (lambda b: b), (lambda b: b)
    if name == "tar-zlib-6":
        return lambda b: zlib.compress(b, 6), zlib.decompress
    if name == "tar-lzma-6":
        return lambda b: lzma.compress(b, preset=6), lzma.decompress
    if name == "tar-zstd-3":
        import zstandard
        return zstandard.ZstdCompressor(level=3).compress, zstandard.ZstdDecompressor().decompress
    if name == "tar-brotli-5":
        import brotli
        return lambda b: brotli.compress(b, quality=5), brotli.decompress
    raise ValueError(f"Unknown baseline: {name}")


def peak_rss():
    if os.name == "nt":
        from ctypes import wintypes
        class Counters(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [
                (name, ctypes.c_size_t) for name in ("PeakWorkingSetSize", "WorkingSetSize", "QuotaPeakPagedPoolUsage",
                "QuotaPagedPoolUsage", "QuotaPeakNonPagedPoolUsage", "QuotaNonPagedPoolUsage", "PagefileUsage", "PeakPagefileUsage")]
        counters = Counters()
        counters.cb = ctypes.sizeof(counters)
        kernel, psapi = ctypes.WinDLL("kernel32"), ctypes.WinDLL("psapi")
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
        if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
            raise OSError("Cannot measure process memory")
        return counters.PeakWorkingSetSize
    import resource
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return value if sys.platform == "darwin" else value * 1024


def summary(values):
    if not values:
        return None
    ordered = sorted(values)
    return {"samples": values, "median": statistics.median(values), "min": min(values), "max": max(values),
            "stdev": statistics.stdev(values) if len(values) > 1 else 0.0,
            "p95": ordered[max(0, math.ceil(len(ordered) * 0.95) - 1)]}


def _worker(source, method, repeats, warmups, queries, seed, chunk_size):
    source = Path(source)
    files = list(files_in(source))
    raw_bytes = sum(p.stat().st_size for p, _ in files)
    if raw_bytes > MAX_BENCH:
        raise ValueError("Benchmark limited to 64 MiB raw files")
    is_rkv = method == "rkv1-zlib-dedup"
    if not is_rkv:
        compress, decompress = codec(method)
    enc_times, dec_times, enc_cpu, dec_cpu = [], [], [], []
    unique_sizes, details = set(), {}
    with tempfile.TemporaryDirectory(prefix="rkv-bench-") as temp:
        work = Path(temp)
        archive = work / "dataset.bin"
        for i in range(warmups + repeats):
            restored = work / f"restored-{i}"
            start, cpu = time.perf_counter(), time.process_time()
            if is_rkv:
                details = pack(source, archive, chunk_size, overwrite=True)
            else:
                original = canonical_tar(source)
                archive.write_bytes(compress(original))
            e_cpu, e = time.process_time() - cpu, time.perf_counter() - start
            size = archive.stat().st_size
            start, cpu = time.perf_counter(), time.process_time()
            if is_rkv:
                unpack(archive, restored)
            else:
                decoded = decompress(archive.read_bytes())
                if decoded != original:
                    raise ValueError("Baseline byte stream mismatch")
                restore_tar(decoded, restored)
            d_cpu, d = time.process_time() - cpu, time.perf_counter() - start
            assert_tree_equal(source, restored)
            shutil.rmtree(restored)
            if i >= warmups:
                enc_times.append(e)
                dec_times.append(d)
                enc_cpu.append(e_cpu)
                dec_cpu.append(d_cpu)
                unique_sizes.add(size)
        if len(unique_sizes) != 1:
            raise ValueError("Non-deterministic compressed size")
        # Repeated requests reuse an open RKV reader; TAR streams are decoded anew.
        # Source reads for expected bytes are OUTSIDE the timed interval.
        rng = random.Random(seed)
        candidates = [(p, rel) for p, rel in files if p.stat().st_size]
        random_times = []
        reader = Archive(archive) if is_rkv else None
        try:
            for _ in range(queries if candidates else 0):
                path, rel = rng.choice(candidates)
                length = min(4096, path.stat().st_size)
                offset = rng.randrange(path.stat().st_size - length + 1)
                with path.open("rb") as expected_file:
                    expected_file.seek(offset)
                    expected = expected_file.read(length)
                start = time.perf_counter()
                if is_rkv:
                    actual = reader.read_range(rel, offset, length)
                else:
                    with tarfile.open(fileobj=io.BytesIO(decompress(archive.read_bytes())), mode="r:") as tar:
                        with tar.extractfile(rel) as member:
                            member.seek(offset)
                            actual = member.read(length)
                random_times.append(time.perf_counter() - start)
                if actual != expected:
                    raise ValueError("Random range mismatch")
        finally:
            if reader:
                reader.close()
    size = unique_sizes.pop()
    return {"method": method, "stored_bytes": size, "total_bits": size * 8,
            "raw_file_bytes": raw_bytes, "compression_ratio": raw_bytes / size if size else None,
            "encode_s": summary(enc_times), "decode_s": summary(dec_times),
            "encode_cpu_s": summary(enc_cpu), "decode_cpu_s": summary(dec_cpu),
            "encode_mib_s": raw_bytes / (1 << 20) / statistics.median(enc_times),
            "decode_mib_s": raw_bytes / (1 << 20) / statistics.median(dec_times),
            "random_read_s": summary(random_times), "random_read_verified": True,
            "bytewise_verified": True, "exact_recovery_rate": 1.0,
            "worker_peak_rss_bytes": peak_rss(), "storage_breakdown": details or None,
            "external_model_bytes": 0, "external_dictionary_bytes": 0, "semantic_index_bytes": 0}


def benchmark(source, *, repeats=3, warmups=1, queries=32, seed=20261014, chunk_size=DEFAULT_CHUNK):
    if not 1 <= repeats <= 100 or not 0 <= warmups <= 10 or not 0 <= queries <= 10000:
        raise ValueError("Invalid benchmark repetitions")
    source = Path(source).resolve()
    inputs = list(files_in(source))
    if sum(p.stat().st_size for p, _ in inputs) > MAX_BENCH:
        raise ValueError("Benchmark limited to 64 MiB")
    files = []
    for path, rel in inputs:
        h = hashlib.sha256()
        with path.open("rb") as stream:
            while data := stream.read(1 << 20):
                h.update(data)
        files.append({"path": rel, "bytes": path.stat().st_size, "sha256": h.hexdigest()})
    methods = ["tar-raw", "tar-zlib-6", "tar-lzma-6"]
    missing, versions = [], {"zlib": zlib.ZLIB_RUNTIME_VERSION}
    for package, method in [("zstandard", "tar-zstd-3"), ("Brotli", "tar-brotli-5")]:
        try:
            versions[package] = importlib.metadata.version(package)
            methods.append(method)
        except importlib.metadata.PackageNotFoundError:
            missing.append(package)
    methods.append("rkv1-zlib-dedup")
    rows = []
    for method in methods:
        print(f"Benchmarking {source.name}: {method}", file=sys.stderr, flush=True)
        cmd = [sys.executable, "-m", "rkv1.benchmark", str(source), method, str(repeats), str(warmups), str(queries), str(seed), str(chunk_size)]
        result = subprocess.run(cmd, check=True, capture_output=True, text=True, encoding="utf-8")
        rows.append(json.loads(result.stdout))
    from . import __version__
    return {"schema_version": 1, "rkv1_version": __version__, "dataset": source.name,
            "environment": {"python": platform.python_version(), "platform": platform.platform(),
                            "processor": platform.processor(), "logical_cpus": os.cpu_count(), "codec_versions": versions},
            "configuration": {"repeats": repeats, "warmups": warmups, "queries": queries, "seed": seed, "chunk_size": chunk_size,
                              "timing": "end-to-end pack/write and read/restore; source comparison outside timed interval",
                              "random_read": "warm OS cache; RKV open manifest cached, touched chunks verified; TAR decoded for each request",
                              "memory": "isolated worker lifetime peak RSS, including interpreter, source, buffers and warmups"},
            "files": files, "missing_optional_packages": missing, "results": rows,
            "inference_quality": None, "limits": ["single machine, warm cache, no energy measurement", "different archive layouts, engineering comparison", "no neural model or scientific inference evaluated", "software/runtime footprint shared and not included in archive size"]}


def incremental_experiment(source, chunk_size=DEFAULT_CHUNK):
    """Append one controlled record; compare recompression with verified block reuse."""
    with tempfile.TemporaryDirectory(prefix="rkv-incremental-") as temp:
        root = Path(temp)
        snapshot = root / "input"
        snapshot.mkdir()
        for path, rel in files_in(source):
            target = snapshot.joinpath(*valid_path(rel).parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
        pack(snapshot, root / "base.rkv", chunk_size)
        files = list(files_in(snapshot))
        target = files[0][0] if files else snapshot / "new.txt"
        with target.open("ab") as stream:
            stream.write(b'\nRKV1-controlled-incremental-probe\n')
        rows = []
        for mode in ("full", "reuse"):
            archive = root / f"{mode}.rkv"
            start = time.perf_counter()
            stats = pack(snapshot, archive, chunk_size, base=root / "base.rkv" if mode == "reuse" else None)
            elapsed = time.perf_counter() - start
            restored = root / f"restored-{mode}"
            unpack(archive, restored)
            assert_tree_equal(snapshot, restored)
            rows.append({"mode": mode, "encode_s": elapsed, "bytewise_verified": True, **stats})
        return {"change": "append 35-byte probe to first sorted file", "runs": rows,
                "limitation": "single trial; both modes read/hash all input and write a complete independent snapshot; reused blocks are verified before copying"}


if __name__ == "__main__":
    source, method, *numbers = sys.argv[1:]
    print(json.dumps(_worker(source, method, *map(int, numbers))))

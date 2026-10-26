"""Aggregate-only diagnostic of EXISTING frames; no scientific re-encoding."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import platform
import sys
import time

from rkv1 import arithmetic
from rkv1.benchmark import peak_rss
from rkv1.neural_frame import HEADER, _restore
from rkv1.neural_small import Predictor as NeuralPredictor
from rkv1.unigram_frame import Predictor as UnigramPredictor
from scripts.neural_inputs import load

ROOT = Path(__file__).resolve().parents[1]
MODEL_SHA = {
    'neural': 'f4848728bc05e305208cdc50f4ec10b80fee167736deecf334b03e0ebfc03813',
    'unigram': '35437268b5c5feccff134e024e45c0161b3c07b54b601b19ccb0db9ff2280672',
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def information(raw, predict):
    # Independent of arithmetic encoder interval updates and emitted bits.
    context = [256] * 4
    terms = []
    start = time.perf_counter()
    for symbol in raw:
        cdf = predict(context)
        if (len(cdf) != 257 or cdf[0] != 0 or cdf[-1] != 32768
                or any(type(n) is not int for n in cdf)
                or any(a >= b for a, b in zip(cdf, cdf[1:]))):
            raise ValueError('Invalid CDF in information audit')
        terms.append(-math.log2((cdf[symbol + 1] - cdf[symbol]) / 32768))
        context = context[1:] + [symbol]
    total = math.fsum(terms)
    return total, time.perf_counter() - start


def controls():
    uniform = tuple(range(0, 32769, 128))
    skew = (0,) + tuple(32513 + n for n in range(256))
    rows = []
    for name, raw, cdf in (
        ('empty_uniform', b'', uniform),
        ('all_bytes_uniform', bytes(range(256)) * 4, uniform),
        ('fixed_skew', b'\0' * 512 + bytes(range(256)), skew),
    ):
        predict = lambda context, values=cdf: values
        ideal, wall = information(raw, predict)
        payload, bits = arithmetic.encode(raw, predict)
        exact = arithmetic.decode(payload, bits, len(raw), predict) == raw
        golden = bits == 8 * len(raw) + 2 if name != 'fixed_skew' else None
        rows.append(dict(id=name, raw_bytes=len(raw), information_bits=ideal,
                         logical_bits=bits, excess_bits=bits-ideal,
                         padding_bits=8*len(payload)-bits, exact=exact,
                         uniform_golden_pass=golden, information_wall_s=wall,
                         engineering_gate_pass=-1 <= bits-ideal <= 4))
    return rows


def audit(inputs, workers):
    start = time.perf_counter()
    cpu = time.process_time()
    jobs = {meta['id']: (meta, raw) for meta, raw in load(inputs, 'test')}
    expected = json.loads((ROOT/'results/v0.37.0/source-checksums.json').read_text('utf-8'))
    files = sorted((ROOT/'rkv1').rglob('*.py')) + [ROOT/'rkv1/memory_demo.html']
    actual = {p.relative_to(ROOT/'rkv1').as_posix(): sha(p.read_bytes()) for p in files}
    if actual != expected:
        raise ValueError('Runtime differs from frozen v0.37, including recursive module set')
    rows = []
    for round_number in (1, 2, 3):
        record = ROOT/f'results/v0.37.0/round-{round_number}.json'
        trials = json.loads(record.read_text('utf-8'))['trials']
        for trial in trials:
            method = trial['method']
            if method not in MODEL_SHA:
                continue
            meta, raw = jobs[trial['id']]
            path = Path(workers)/f'round-{round_number}'/f"{trial['order']:02d}-{method}"/'frame.rkvnn'
            frame = path.read_bytes()
            if sha(frame) != trial['pack']['frame_sha256']:
                raise ValueError('Original frame SHA mismatch')
            magic, version, code, n, mn, pn, bits, rs, ms, ps = HEADER.unpack_from(frame)
            model = _restore(1, frame[HEADER.size:HEADER.size+mn], 6944 if method == 'neural' else 520)
            payload = frame[HEADER.size+mn:]
            if not (magic == (b'RKVNN001' if method == 'neural' else b'RKVUNI01')
                    and version == 1 and code == (0 if method == 'neural' else 4)
                    and n == len(raw) == 8192 and rs.hex() == sha(raw)
                    and ms.hex() == sha(model) == MODEL_SHA[method]
                    and ps.hex() == sha(payload) and pn == len(payload) == (bits+7)//8
                    and bits == trial['pack']['info']['payload_bits']
                    and len(frame) == HEADER.size+mn+pn):
                raise ValueError('Original frame field/model/payload mismatch')
            previous = next((x for x in rows if x['id'] == meta['id'] and x['method'] == method), None)
            if previous:
                if previous['frame_sha256'] != sha(frame):
                    raise ValueError('Original repeated frame differs')
                continue
            predictor = (NeuralPredictor if method == 'neural' else UnigramPredictor)(model)
            ideal, wall = information(raw, predictor.cdf)
            rows.append(dict(**meta, method=method, frame_sha256=sha(frame),
                             model_sha256=sha(model), model_raw_bytes=len(model),
                             model_zlib_bytes=mn, header_bytes=HEADER.size, payload_bytes=pn,
                             logical_bits=bits, information_bits=ideal, excess_bits=bits-ideal,
                             padding_bits=8*pn-bits, information_wall_s=wall,
                             engineering_gate_pass=-1 <= bits-ideal <= 4))
    if len(rows) != 8:
        raise ValueError('Expected eight unique conditions')
    synthetic = controls()
    return dict(schema='rkv-cdf-information-audit-1', status='diagnostic_only_not_release',
                conditions=rows, original_frames_verified=24, unique_conditions=8,
                new_scientific_encodes=0, synthetic_controls=synthetic,
                runtime_sha256=actual, runtime_source_bytes=sum(p.stat().st_size for p in files),
                diagnostic_source_sha256=sha(Path(__file__).read_bytes()),
                diagnostic_source_bytes=Path(__file__).stat().st_size,
                threshold_bits=[-1, 4], all_engineering_gates_pass=all(
                    x['engineering_gate_pass'] for x in rows+synthetic),
                diagnostic_wall_s=time.perf_counter()-start,
                diagnostic_cpu_s=time.process_time()-cpu, peak_rss_bytes=peak_rss(),
                python=platform.python_version(), numpy_imported='numpy' in sys.modules,
                remote_model_calls=0, cold_cache=None, cross_machine=None)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', required=True)
    parser.add_argument('--workers', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    target = Path(args.output)
    # Refuse to overwrite diagnostics, including a negative result.
    with target.open('x', encoding='utf-8', newline='\n') as stream:
        result = audit(args.inputs, args.workers)
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


if __name__ == '__main__':
    main()

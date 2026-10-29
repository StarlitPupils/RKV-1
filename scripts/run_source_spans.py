"""Fixed owned Store source-span case; no model, gold, ranking or HTTP."""
import copy
import json
from pathlib import Path
import time
from rkv1.store import Store
from rkv1.benchmark import peak_rss
from scripts.sentence_spans import digest
from scripts.store_sentence_spans import make_witness, recover_witness
from scripts.source_span_fixture import encode, fixture


def write(path, value):
    with Path(path).open('xb') as stream:
        stream.write(encode(value) + b'\n')


def run_case(out, count, mode):
    out = Path(out)
    out.mkdir(exist_ok=False)
    started, cpu, success = time.perf_counter(), time.process_time(), False
    try:
        source, records = fixture(count, mode)
        src = out/'source'
        src.mkdir()
        (src/'corpus.jsonl').write_bytes(source)
        t, c = time.perf_counter(), time.process_time()
        store = Store.create(out/'store', compression='zlib', chunk_size=65536, io_backend='bounded')
        sid = store.add(src)['snapshot_id']
        build = {'wall_s': time.perf_counter()-t, 'CPU_s': time.process_time()-c}
        t, c = time.perf_counter(), time.process_time()
        rows, cursor = [], 0
        for raw, field in records:
            binding = {'snapshot_id': sid, 'path': 'corpus.jsonl', 'source_sha256': digest(source),
                       'record_offset': cursor, 'record_length': len(raw), 'record_sha256': digest(raw), 'field': field}
            witness = make_witness(store.root, binding, [0, 2])
            tokens = recover_witness(store.root, witness, expected_binding=binding)
            packet = {'witness': witness, 'original_token_hex': [v.hex() for v in tokens]}
            # Hex transport is explicit and charged. No API prompt or wire equality claim.
            rows.append({'binding': binding, 'witness': witness, 'token_sha256s': [digest(v) for v in tokens],
                         'selected_token_B': sum(map(len, tokens)),
                         'decoded_utf8_B': sum(len(json.loads(v).encode('utf-8')) for v in tokens),
                         'witness_serialized_B': len(encode(witness)), 'packet_serialized_B': len(encode(packet)),
                         'packet_sha256': digest(encode(packet)), 'application_record_return_B': 2*len(raw)})
            cursor += len(raw)
        phase = {'wall_s': time.perf_counter()-t, 'CPU_s': time.process_time()-c}
        # Six fixed identity/position/accounting controls; no candidate parameter changes.
        original = rows[0]
        controls = []
        for kind in ('external_source', 'external_record', 'token_digest', 'duplicate_index', 'record_count', 'new_SID'):
            witness, expected = copy.deepcopy(original['witness']), dict(original['binding'])
            if kind == 'external_source':
                expected['source_sha256'] = '0'*64
            elif kind == 'external_record':
                expected['record_sha256'] = '0'*64
            elif kind == 'token_digest':
                witness['sentences'][0]['token_sha256'] = '0'*64
            elif kind == 'duplicate_index':
                witness['sentences'][1] = copy.deepcopy(witness['sentences'][0])
            elif kind == 'record_count':
                witness['application_record_return_B'] += 1
            else:
                (src/'corpus.jsonl').write_bytes(source + b'{"abstract":["new HEAD only"]}\n')
                new_sid = store.add(src)['snapshot_id']
                assert new_sid != sid
                witness['binding']['snapshot_id'] = new_sid
            refused = False
            try:
                recover_witness(store.root, witness, expected_binding=expected)
            except ValueError:
                refused = True
            controls.append({'kind': kind, 'refused': refused})
            assert refused, kind
        # Old source SID still recovers after HEAD changes.
        assert recover_witness(store.root, original['witness'], expected_binding=original['binding'])
        result = {'count': count, 'mode': mode, 'snapshot_id': sid, 'source_sha256': digest(source),
                  'source_B': len(source), 'rows': rows, 'controls': controls, 'old_SID_after_HEAD_change': True,
                  'source_build': build, 'candidate_build_and_recovery': phase, 'new_model_API_calls': 0,
                  'CAS_decode_B': None, 'OS_physical_IO_B': None, 'input_whole_source_generated_in_worker': True}
        write(out/'case.json', result)
        success = True
        return result
    finally:
        write(out/'case-finally.json', {'success': success, 'full_wall_s': time.perf_counter()-started,
                                      'full_CPU_s': time.process_time()-cpu, 'peak_RSS_B': peak_rss()})


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('out')
    parser.add_argument('count', type=int)
    parser.add_argument('mode')
    args = parser.parse_args()
    run_case(args.out, args.count, args.mode)

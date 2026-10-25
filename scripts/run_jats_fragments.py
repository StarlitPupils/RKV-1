"""Exact fragment audit and explicitly counterfactual adjacent replay plans."""
import argparse
from collections import Counter
import json
import os
from pathlib import Path
import platform
import random
import shutil
import subprocess
import sys
import time
from types import SimpleNamespace

from rkv1.benchmark import peak_rss
from rkv1.controlled import implementation_checksums
from rkv1.core import digest, files_in
from rkv1.jats_fragments import fragments, verify
from rkv1.memory import _json
from rkv1.memory_jats import parse
from rkv1.memory_budget import DEFAULT_BUDGET, evaluate, range_work
from rkv1.memory_index import differences
from rkv1.memory_projection import fingerprint
from rkv1.native import load_native_gear
from rkv1.store import Store
from scripts.run_memory_history import clean_env, inventory
from scripts.run_paper_revisions import inputs, schedule
from scripts.run_units import save

ROOT = Path(__file__).resolve().parents[1]
MODES = ('whole', 'position', 'xml-id')
SEED = 20261025


def units(raw, mode):
    if mode != 'whole': return fragments(raw, mode=mode)
    key, title, paragraphs = parse(raw)
    return [{'key': key, 'parent_key': key, 'parent_sha256': digest(raw), 'role': 'whole', 'selector': 'whole',
             'offset': 0, 'length': len(raw), 'sha256': digest(raw), 'text': '\n'.join([title, *paragraphs])}]


def worker(args):
    sources = {v['path']: (ROOT/'data/elife-revisions'/v['path']).read_bytes() for p in inputs()['papers'] for v in p['versions']}
    names = list(sources); random.Random(SEED+args.round).shuffle(names)
    samples = []
    for name in names:
        start = time.perf_counter(); cpu = time.process_time()
        rows = units(sources[name], args.mode)
        wall = time.perf_counter()-start; cpu = time.process_time()-cpu
        samples.append({'path': name, 'units': len(rows), 'wall_s': wall, 'cpu_s': cpu, 'descriptor_sha256': digest(_json(rows))})
    save(args.result, {'mode': args.mode, 'round': args.round, 'samples': samples, 'peak_rss_bytes': peak_rss()})


def current_rows(state, versions, mode):
    result = {}
    for pid, version in state:
        name = versions[pid, version]['path']; raw = (ROOT/'data/elife-revisions'/name).read_bytes()
        for f in units(raw, mode):
            assert f['key'] not in result
            meta = [f['key'], name, f['offset'], f['length'], f['sha256'], 'jats-fragment-preflight-'+mode]
            if mode == 'whole':
                _, title, paragraphs = parse(raw)
                result[f['key']] = (meta, title, paragraphs)
            else:
                result[f['key']] = (meta, '', [f['text']])
    return result


def plan(store, before_sid, sid, before, current, projection):
    prior = {k: r[0] for k, r in before.items()}
    removed, changed, moves = differences(prior, current)
    rebound = []; upserted = []
    for meta in changed:
        key = meta[0]
        if projection and key in before and fingerprint(*before[key][1:]) == fingerprint(*current[key][1:]): rebound.append(meta)
        else: upserted.append(meta)
    lower = evaluate(SimpleNamespace(store=store), before_sid, sid, prior, removed, upserted, DEFAULT_BUDGET)
    reads = [(before_sid, prior[k]) for k in removed]
    for meta in upserted:
        old = prior.get(meta[0])
        if old and old[4] == meta[4]: continue
        if old: reads.append((before_sid, old))
        reads.append((sid, meta))
    # An audit verifier currently checks even text-equal rebindings against its
    # entire new parent. Excluding these reads would invent a trusted fast path.
    parent_reads = [*reads, *((sid, meta) for meta in rebound)]
    with store.snapshot(before_sid) as old, store.snapshot(sid) as new:
        snaps = {before_sid: old, sid: new}
        def measured(items, full):
            total = cas = 0
            for which, meta in items:
                charged = list(meta)
                if full:
                    charged[2] = 0; charged[3] = snaps[which].files[meta[1]]['size']
                total += charged[3]; cas += range_work(snaps[which], charged)
            return {'record_reads': len(items), 'record_bytes': total, 'cas_bytes': cas}
        lower_work = measured(reads, False); actual_work = measured(parent_reads, True)
    def reason(work):
        if len(removed)+len(upserted) > max(1, len(prior)//4): return 'legacy-change-limit'
        if len(moves) > 256: return 'relocation-limit'
        if len(rebound) > 4096: return 'rebinding-limit'
        for field, limit, why in [('changes', DEFAULT_BUDGET['max_changes'], 'changes'),
                                  ('record_bytes', DEFAULT_BUDGET['max_record_bytes'], 'record-bytes'),
                                  ('cas_bytes', DEFAULT_BUDGET['max_cas_bytes'], 'cas-bytes')]:
            value = len(removed)+len(upserted) if field == 'changes' else work[field]
            if value > limit: return 'budget-'+why
        return None
    low_reason = reason(lower_work); actual_reason = reason(actual_work)
    if lower['reason'] is None: assert all(lower[k] == lower_work[k] for k in lower_work)
    return {'removed': len(removed), 'upserted': len(upserted), 'rebound': len(rebound), 'relocation_ranges': len(moves),
            'prior_records': len(prior), 'current_records': len(current),
            'range_only_lower_bound': {**lower_work, 'reason': low_reason, 'admissible': low_reason is None},
            'current_full_parent_verifier': {**actual_work, 'reason': actual_reason, 'admissible': actual_reason is None}}


def main(args, *, modes=MODES, fragment_modes=('position','xml-id'),
         worker_module='scripts.run_jats_fragments', label_prefix='v024-fragments'):
    manifest = inputs(); args.out.mkdir(); args.work.mkdir()
    checks = implementation_checksums(); save(args.out/'source-checksums.json', checks)
    source_paths = sorted(Path('rkv1').rglob('*.py'))+[Path('rkv1/memory_demo.html')]
    resources = {p.as_posix(): {'bytes': p.stat().st_size, 'sha256': digest(p.read_bytes())} for p in source_paths}
    save(args.out/'source-resource.json', {'files': resources, 'total_bytes': sum(v['bytes'] for v in resources.values())})
    library = args.native_library.resolve(); load_native_gear(str(library)); meta = library.with_name('native.json')
    native = {'bytes': library.stat().st_size, 'sha256': digest(library.read_bytes()), 'metadata_bytes': meta.stat().st_size,
              'metadata_sha256': digest(meta.read_bytes()), 'metadata': json.loads(meta.read_text('utf-8'))}
    save(args.out/'native-resource.json', native)
    save(args.out/'environment.json', {'python': platform.python_version(), 'platform': platform.platform(), 'logical_cpus': os.cpu_count(),
        'seed': SEED, 'parser_rounds': 3, 'new_independent_papers': 0, 'reused_papers': 6, 'real_transitions': 12,
        'generation_calls': 0, 'new_scientific_QA': 0, 'cold_cache': None, 'cross_machine': None,
        'scope': 'Identity audit and adjacent-state necessary-condition planning only; not an integrated Memory benchmark'})
    audit = []; verified = 0
    for paper in manifest['papers']:
        for v in paper['versions']:
            raw = (ROOT/'data/elife-revisions'/v['path']).read_bytes()
            for mode in fragment_modes:
                fs = fragments(raw, mode=mode)
                for f in fs:
                    original = verify(raw, f, mode=mode)
                    assert digest(original) == f['sha256']; verified += 1
                audit.append({'path': v['path'], 'sha256': digest(raw), 'mode': mode, 'units': len(fs),
                    'roles': dict(Counter(f['role'] for f in fs)), 'id_key_count': sum(f['selector'].startswith('id:') for f in fs),
                    'descriptor_sha256': digest(_json(fs)), 'descriptor_bytes': len(_json(fs)),
                    'locator_metadata_json_bytes': len(_json([{k: x for k, x in f.items() if k != 'text'} for f in fs])),
                    'text_utf8_bytes': sum(len(f['text'].encode()) for f in fs), 'covered_original_bytes': sum(f['length'] for f in fs),
                    'parent_and_every_range_verified': True, 'lexical_projection_matches_whole': True})
    save(args.out/'identity-audit.json', {'inputs': manifest, 'files': audit, 'verified_ranges_including_two_key_policies': verified})
    parser_trials = []
    for r in range(3):
        order = list(modes); random.Random(SEED+r).shuffle(order)
        for mode in order:
            result = args.work/f'parse-{r}-{mode}.json'; start = time.perf_counter()
            subprocess.run([sys.executable, '-m', worker_module, '--worker', '--mode', mode, '--round', str(r), '--result', str(result)], check=True, env=clean_env())
            trial = json.loads(result.read_text('utf-8')); trial['process_wall_including_startup_s'] = time.perf_counter()-start
            parser_trials.append(trial)
    save(args.out/'parser-trials.json', {'trials': parser_trials})
    versions = {(p['id'], v['version']): v for p in manifest['papers'] for v in p['versions']}
    plans = []; cas_stats = []
    for case in ('fixed', 'gear'):
        source = args.work/(case+'-source'); source.mkdir()
        store = Store.create(args.work/(case+'-cas'), compression='zlib', chunker='fixed' if case=='fixed' else 'gear-v1')
        history = []; previous_sid = None; previous = None
        for n, state in enumerate(schedule()):
            wanted = {versions[pid, v]['path'] for pid, v in state}
            for p in source.iterdir():
                if p.name not in wanted: p.unlink()
            for name in wanted:
                if not (source/name).exists(): shutil.copyfile(ROOT/'data/elife-revisions'/name, source/name)
            built = store.add(source, label=f'{label_prefix}-{n:02d}', chunker_backend='rust' if case=='gear' else 'python', native_library=str(library) if case=='gear' else None)
            sid = built['snapshot_id']; truth = {name: digest(p.read_bytes()) for p, name in files_in(source)}; history.append((sid, truth))
            with store.snapshot(sid) as snap:
                assert all(snap.read_range(name) == (source/name).read_bytes() for name in wanted)
            current = {mode: current_rows(state, versions, mode) for mode in modes}
            if n:
                for mode in modes:
                    for projection in (False, True):
                        plans.append({'case': case, 'stage': n, 'mode': mode, 'projection_rebinding': projection,
                                      **plan(store, previous_sid, sid, previous[mode], current[mode], projection)})
            cas_stats.append({'case': case, 'stage': n, 'snapshot_id': sid, 'stats': store.stats(),
                'simple_locator_metadata_bytes': {mode: sum(len(_json({k: v for k, v in f.items() if k != 'text'})) for pid, version in state
                    for f in units((ROOT/'data/elife-revisions'/versions[pid, version]['path']).read_bytes(), mode)) for mode in modes}})
            previous_sid = sid; previous = current
        before = inventory(store.root)
        for sid, truth in history:
            with store.snapshot(sid) as snap:
                assert set(snap.files) == set(truth)
                assert all(digest(snap.read_range(name)) == sha for name, sha in truth.items())
        assert before == inventory(store.root)
    assert checks == implementation_checksums() and digest(library.read_bytes()) == native['sha256']
    save(args.out/'plans.json', {'plans': plans, 'adjacent_state_necessary_condition_only': True, 'not_actual_index_savings': True})
    save(args.out/'cas-history.json', {'stages': cas_stats, 'historical_full_source_snapshots_verified': 26, 'persistent_trees_unchanged_by_reads': True})
    print(json.dumps({'ranges_verified': verified, 'adjacent_plans': len(plans), 'parser_trials': len(parser_trials)}))


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--out', type=Path); p.add_argument('--work', type=Path); p.add_argument('--native-library', type=Path)
    p.add_argument('--worker', action='store_true'); p.add_argument('--mode', choices=MODES); p.add_argument('--round', type=int); p.add_argument('--result', type=Path)
    a = p.parse_args()
    if a.worker: worker(a)
    else: main(a)

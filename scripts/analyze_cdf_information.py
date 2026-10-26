"""Analyze frozen aggregate JSON only; never reads scientific prefixes or models."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')


def analyze(raw_path, output):
    out = Path(output)
    out.mkdir(exist_ok=False)
    raw = Path(raw_path).read_bytes()
    data = json.loads(raw)
    frozen = (ROOT/'scripts/audit_cdf_information.py').read_bytes()
    assert sha(frozen) == data['diagnostic_source_sha256']
    assert data['original_frames_verified'] == 24 and data['unique_conditions'] == 8
    assert data['new_scientific_encodes'] == 0 and not data['numpy_imported']
    assert data['remote_model_calls'] == 0
    # Keep the original record and its lifecycle flag byte-for-byte.
    (out/'aggregate.json').write_bytes(raw)
    previous = json.loads((ROOT/'results/v0.37.0/round-1.json').read_text('utf-8'))['trials']
    derived = []
    for row in data['conditions']:
        assert row['payload_bytes']*8-row['logical_bits'] == row['padding_bits']
        assert 0 <= row['padding_bits'] <= 7
        assert row['engineering_gate_pass'] == (-1 <= row['excess_bits'] <= 4)
        for codec in ('zlib', 'zstd', 'lzma'):
            baseline = next(t for t in previous if t['id'] == row['id'] and t['method'] == codec)
            gap = row['logical_bits']-baseline['pack']['info']['payload_bits']
            derived.append(dict(id=row['id'], method=row['method'], baseline=codec,
                                original_logical_payload_gap_bits=gap,
                                fixed_CDF_ideal_gap_bits=gap-row['excess_bits'],
                                overhead_fraction_of_positive_gap=row['excess_bits']/gap if gap > 0 else None))
    controls = data['synthetic_controls']
    validation = dict(original_24_frame_identities_verified=True, independent_information_conditions=8,
                      engineering_conditions_passed=sum(x['engineering_gate_pass'] for x in data['conditions']),
                      synthetic_exact=sum(x['exact'] for x in controls),
                      synthetic_uniform_golden=sum(x['uniform_golden_pass'] is True for x in controls),
                      no_new_scientific_encoding_or_recovery=True,
                      original_raw_sha256=sha(raw), frozen_audit_source_sha256=sha(frozen),
                      threshold_bits=[-1,4], all_gates_pass=all(x['engineering_gate_pass'] for x in data['conditions']+controls),
                      raw_status_is_measurement_time_flag_not_release_status=True)
    save(out/'validation.json', validation)
    save(out/'derived-metrics.json', dict(comparisons=derived, logical_not_byte_padding=True,
                                         scope='Diagnostic reuse of previously evaluated prefixes; no new scientific trial'))
    ledger = json.loads((ROOT/'results/v0.37.0/source-resource.json').read_text('utf-8'))
    assert {k.removeprefix('rkv1/'):v['sha256'] for k,v in ledger['files'].items()} == data['runtime_sha256']
    save(out/'measured-source-resource.json', ledger)
    for name in ('source-checksums.json','source-resource.json'):
        shutil.copyfile(ROOT/'results/v0.37.0'/name, out/name)
    local_log = ROOT/'.tools/v038-cdf-information-audit.log'
    if local_log.exists():
        preflight_log_sha = sha(local_log.read_bytes())
    else:
        published_context = json.loads((ROOT/'results/v0.38.0/measurement-context.json').read_text('utf-8'))
        preflight_log_sha = published_context['prior_preflight_failure']['retained_log_sha256']
    save(out/'measurement-context.json', dict(initial_freeze='270e20f', corrected_pre_computation_freeze='396d111',
         initial_freeze_CI=40297239511, corrected_freeze_CI=40297364464,
         measured_runtime='v0.37.0 byte-identical all61 Python modules plus HTML',
         prior_preflight_failure=dict(category='Full source set compared against Python-only ledger',
             scientific_information_computed=False, retained_log_sha256=preflight_log_sha,
             correction='Use original full source-resource files ledger before any CDF calculation'),
         resumed_after_quota_checkpoint=True, scientific_measurement_repeated=False,
         raw_status='Original diagnostic_only_not_release retained unchanged; current release status is separately verified',
         new_model_training_runs=0, new_static_model_builds=0, new_scientific_encodes=0,
         diagnostic_cost=dict(wall_s=data['diagnostic_wall_s'],cpu_s=data['diagnostic_cpu_s'],
             peak_rss_bytes=data['peak_rss_bytes'],source_bytes=data['diagnostic_source_bytes']),
         analysis_source_bytes=Path(__file__).stat().st_size, analysis_source_sha256=sha(Path(__file__).read_bytes()),
         cold_cache=None,cross_machine=None,additional_remote_model_calls=0))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    names = ['SciPy','SymPy','LaTeX','Noise']
    ids = ['scipy__scipy__linalg___basic.py','sympy__sympy__integrals__integrals.py','latex3__base__ltmath.dtx','control_noise_256k.bin']
    fig, axes = plt.subplots(1,3,figsize=(14,4.6),layout='constrained')
    colors = {'neural':'#2563eb','unigram':'#d97706'}
    for method, offset in (('neural',-.18),('unigram',.18)):
        rows = [next(r for r in data['conditions'] if r['id']==i and r['method']==method) for i in ids]
        axes[0].bar([n+offset for n in range(4)],[r['excess_bits'] for r in rows],.34,label=method,color=colors[method])
        for n,r in enumerate(rows):axes[0].text(n+offset,r['excess_bits']+.07,f"{r['excess_bits']:.2f}",ha='center',fontsize=8)
        gaps=[next(r['original_logical_payload_gap_bits'] for r in derived if r['id']==i and r['method']==method and r['baseline']=='zlib') for i in ids]
        axes[1].bar([n+offset for n in range(4)],gaps,.34,color=colors[method])
        axes[2].bar([n+offset for n in range(4)],[r['model_zlib_bytes'] for r in rows],.34,color=colors[method])
    axes[0].axhspan(-1,4,color='#16a34a',alpha=.08,label='Frozen engineering band')
    axes[0].set_ylim(-1.2,4.4)
    axes[0].set_ylabel('Logical bits minus CDF information (bits)')
    axes[0].set_title('Fixed-CDF coder overhead')
    axes[1].set_ylabel('Original logical payload minus zlib (bits)')
    axes[1].set_title('Previously measured payload gap')
    axes[2].set_ylabel('Embedded model bytes per frame')
    axes[2].set_title('Model cost, separate from coder bits')
    for ax in axes:
        ax.set_xticks(range(4),names);ax.grid(axis='y',alpha=.18);ax.set_axisbelow(True)
    fig.legend(*axes[0].get_legend_handles_labels(),loc='outside lower center',ncol=3,frameon=False)
    fig.suptitle('RKV-1 v0.38 diagnostic: same existing 8 conditions / 24 original frame identities')
    fig.savefig(out/'cdf-information-audit.png',dpi=160)
    plt.close(fig)
    print(json.dumps(validation))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw',required=True)
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    analyze(args.raw,args.output)

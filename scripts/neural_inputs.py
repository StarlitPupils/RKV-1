"""Pinned archival sources; disjoint train/test files, fixed byte prefixes."""
import json
from pathlib import Path
from rkv1.core import digest

TRAIN=('scipy__scipy__optimize___linprog.py','sympy__sympy__core__expr.py','latex3__required__amsmath__amsmath.dtx')
TEST=('scipy__scipy__linalg___basic.py','sympy__sympy__integrals__integrals.py','latex3__base__ltmath.dtx','control_noise_256k.bin')
ROOT=Path(__file__).resolve().parents[1]


def load(folder,split):
    manifest=json.loads((ROOT/'docs/text-lanes-inputs.json').read_text('utf-8'))
    entries={x['id']:x for x in manifest['files']+[manifest['negative_control']]};jobs=[]
    for name in TRAIN if split=='train' else TEST:
        item=entries[name];full=(Path(folder)/name).read_bytes()
        assert len(full)==item['bytes'] and digest(full)==item['sha256'],name
        raw=full[:32768 if split=='train' else 8192]
        jobs.append(({'id':name,'split':split,'family':item['family'],'full_bytes':len(full),'full_sha256':digest(full),
                      'prefix_bytes':len(raw),'prefix_sha256':digest(raw),'source_url':item.get('source_url'),'source_path':item.get('source_path')},raw))
    return jobs

"""Fixed unscored suffix ranges; manifest preparation never runs a compressor."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
FILES=('scipy__scipy__linalg___basic.py','sympy__sympy__integrals__integrals.py','latex3__base__ltmath.dtx')


def load(folder):
    manifest=json.loads((ROOT/'docs/text-lanes-inputs.json').read_text('utf-8'))
    entries={x['id']:x for x in manifest['files']}
    jobs=[]
    for name in FILES:
        entry=entries[name];full=(Path(folder)/name).read_bytes()
        assert len(full)==entry['bytes'] and hashlib.sha256(full).hexdigest()==entry['sha256']
        raw=full[32768:40960];assert len(raw)==8192
        meta={'id':name+'@32768','family':entry['family'],'scientific':True,
              'offset':32768,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),
              'full_bytes':len(full),'full_sha256':entry['sha256'],'source_url':entry['source_url']}
        jobs.append((meta,raw))
    for name,raw in (('new_noise',hashlib.shake_256(b'RKV-1 online-counts v039 fixed noise seed20261026').digest(8192)),
                     ('byte_cycle',bytes(range(256))*32)):
        jobs.append(({'id':name,'family':'synthetic','scientific':False,'offset':0,'bytes':8192,
                      'sha256':hashlib.sha256(raw).hexdigest()},raw))
    return jobs


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--inputs',required=True);p.add_argument('--manifest',required=True)
    args=p.parse_args()
    with Path(args.manifest).open('x',encoding='utf-8',newline='\n') as stream:
        json.dump({'scope':'Fresh fixed ranges within previously seen files, not unseen projects',
                   'inputs':[m for m,_ in load(args.inputs)],'compression_runs':0},stream,indent=2)
        stream.write('\n')

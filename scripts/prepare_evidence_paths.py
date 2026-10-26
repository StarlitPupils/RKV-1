"""Prepare input hashes only, after candidate freeze and before ingestion/scoring."""
import argparse
import json
from pathlib import Path
from rkv1.core import digest
from scripts.evidence_path_fixture import corpus

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--manifest',required=True)
    args=p.parse_args()
    epochs=[]
    for epoch in range(13):
        raw=corpus(epoch)
        epochs.append({'epoch':epoch,'bytes':len(raw),'records':len(raw.splitlines()),'sha256':digest(raw)})
    record={'synthetic_only':True,'schema':'rkv-explicit-path-fixture-1','epochs':epochs,
            'ingestions_or_queries':0,'questions_generated_after_all_ingestions':True,
            'scope':'Deterministic public fixture, operational delay only, no unknown-task claim'}
    with Path(args.manifest).open('x',encoding='utf-8',newline='\n') as stream:
        json.dump(record,stream,indent=2);stream.write('\n')

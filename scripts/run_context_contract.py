"""Actual loopback HTTP/CLI contract, not a real model or scientific QA test."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request,urlopen

from rkv1.controlled import implementation_checksums
from rkv1.core import digest
from rkv1.memory import Memory
from rkv1.memory_model import answer
from scripts.run_memory_history import clean_env,inventory
from scripts.run_units import save
from tests.context_protocol_support import FixtureService,corpus,demo_service

ROOT=Path(__file__).resolve().parents[1]


def main(args):
    args.out.mkdir();args.work.mkdir();checks=implementation_checksums();source=args.work/'source';source.mkdir()
    raw=corpus();(source/'fixture.jsonl').write_bytes(raw);m=Memory.create(args.work/'memory');built=m.add(source,label='v028-context-contract')
    before={k:v for k,v in inventory(m.root).items() if not k.startswith('answers/')}
    source_identity=m.search('rareanchor')['hits'][0]['locator'];records=[]
    def check(record,expected,request):
        assert record['accepted'] and record['exposed_sentences']['doc:1']==expected
        assert record['request_body_bytes']==len(request['raw']) and record['prompt_sha256']==digest(request['raw'])
        texts=[s['text'] for h in request['context'] for s in h['sentences']]
        assert sum(len(t.encode()) for t in texts)==record['context_body_utf8_bytes']<=record['context_body_budget']
        assert len(json.dumps(request['context'],ensure_ascii=False).encode())==record['context_json_bytes']
        assert record['answer']['evidence'][0]['locator']==source_identity
        assert record['answer']['scientific_entailment_verified'] is False and not request['authorization_present']
        stored=json.loads((m.root/'answers'/(record['writeback']['answer_id']+'.json')).read_bytes());assert stored['primary_evidence'] is False
        records.append({k:record[k] for k in ('context_selector','context_body_budget','context_body_utf8_bytes','context_json_bytes','request_body_bytes','prompt_sha256','exposed_sentences')})
    with FixtureService() as fixture,patch.dict(os.environ,{'RKV_LLM_API_KEY':''}):
        for selector in ('source-order','lexical'):
            for b,ids in [(8000,[0] if selector=='source-order' else [2]),(24000,[0,1] if selector=='source-order' else [0,2]),(48000,[0,1,2])]:
                r=answer(m,'rareanchor',config=fixture.config,context_selector=selector,context_body_budget=b);check(r,ids,fixture.requests[-1])
        default=answer(m,'rareanchor',config=fixture.config);check(default,[0,1],fixture.requests[-1]);default_wire=fixture.requests[-1]['raw']
        explicit=answer(m,'rareanchor',config=fixture.config,context_selector='source-order',context_body_budget=24000)
        check(explicit,[0,1],fixture.requests[-1]);assert default_wire==fixture.requests[-1]['raw']
        seen=len(fixture.requests);answers=inventory(m.root/'answers')
        for kwargs in ({'context_selector':'bad'},{'context_body_budget':True},{'context_body_budget':'8000'},{'context_body_budget':7999}):
            try:answer(m,'rareanchor',config=fixture.config,**kwargs)
            except ValueError:pass
            else:raise AssertionError('Invalid controls accepted')
        assert len(fixture.requests)==seen and answers==inventory(m.root/'answers')
        env=clean_env();env.update({'RKV_LLM_BASE_URL':fixture.url,'RKV_LLM_MODEL':'rkv-local-protocol-fixture'})
        cli=[sys.executable,'-m','rkv1','memory-answer',str(m.root.resolve()),'rareanchor']
        p=subprocess.run([*cli,'--context-selector','lexical','--context-body-budget','8000'],env=env,capture_output=True,text=True,encoding='utf-8',check=True)
        check(json.loads(p.stdout),[2],fixture.requests[-1])
        def post(base,client,value):
            req=Request(base+'/api/answer',data=json.dumps(value).encode(),headers={'Content-Type':'application/json','X-RKV-Client':client})
            with urlopen(req,timeout=5) as response:return json.load(response)
        with demo_service(m.root.resolve(),fixture.url,env=env) as (base,status):
            assert status['context_api_version']==2 and status['context_selectors']==['source-order','lexical'] and status['context_body_budgets']==[8000,24000,48000]
            check(post(base,'memory-v2',{'question':'rareanchor','context_selector':'lexical','context_body_budget':8000}),[2],fixture.requests[-1])
            seen=len(fixture.requests)
            for client,value in [('memory-v1',{'context_selector':'lexical'}),('memory-v2',{'context_selector':'bad'}),('memory-v2',{'context_body_budget':True})]:
                try:post(base,client,{'question':'rareanchor',**value})
                except HTTPError as e:assert e.code==400
                else:raise AssertionError('Invalid HTTP context controls accepted')
            assert len(fixture.requests)==seen
            check(post(base,'memory-v1',{'question':'rareanchor'}),[0,1],fixture.requests[-1])
        fixture.reply_mode='omitted';bad=answer(m,'rareanchor',config=fixture.config,context_selector='lexical',context_body_budget=8000)
        assert not bad['accepted'];fixture.reply_mode='echo-visible'
        old=ROOT/'.tools/published-wheel-v0.26';wheel=ROOT/'.tools/published-v0.26/rkv1-0.26.0-py3-none-any.whl'
        proof=json.loads((ROOT/'.tools/published-v0.26/published-verification.json').read_text('utf-8'))
        assert digest(wheel.read_bytes())==proof['assets'][wheel.name]['sha256']
        assert json.loads((ROOT/'results/v0.26.0/source-checksums.json').read_text('utf-8'))['memory_model.py']==json.loads((ROOT/'results/v0.27.0/source-checksums.json').read_text('utf-8'))['memory_model.py']
        p=subprocess.run(cli,cwd=args.work,env={**env,'PYTHONPATH':str(old)},capture_output=True,text=True,encoding='utf-8',check=True)
        legacy=json.loads(p.stdout);assert legacy['accepted'] and fixture.requests[-1]['raw']==default_wire
        seen=len(fixture.requests);p=subprocess.run([*cli,'--context-selector','lexical'],cwd=args.work,env={**env,'PYTHONPATH':str(old)},capture_output=True,text=True,encoding='utf-8')
        assert p.returncode!=0 and 'unrecognized arguments' in p.stderr and len(fixture.requests)==seen
        assert len(fixture.requests)==13 and len(records)==11
    assert checks==implementation_checksums() and before=={k:v for k,v in inventory(m.root).items() if not k.startswith('answers/')}
    with m.store.snapshot(built['snapshot_id']) as snap:assert snap.read_range('fixture.jsonl')==raw
    save(args.out/'source-checksums.json',checks)
    files={p.as_posix():{'bytes':p.stat().st_size,'sha256':digest(p.read_bytes())} for p in [*sorted(Path('rkv1').rglob('*.py')),Path('rkv1/memory_demo.html')]}
    save(args.out/'source-resource.json',{'files':files,'total_bytes':sum(v['bytes'] for v in files.values()),'native_specific_bytes':0,'model_bytes':0})
    save(args.out/'contract.json',{'fixture_source_bytes':len(raw),'fixture_source_sha256':digest(raw),'conditions_and_default_CLI_HTTP_records':records,
        'local_fixture_model_HTTP_requests':13,'remote_model_calls':0,'invalid_Python_controls_rejected_before_request_or_write':4,
        'invalid_HTTP_controls_rejected_without_upstream':3,'omitted_citation_rejected_without_retry':True,
        'default_wire_matches_actual_released_v026_responder_identical_to_v027':True,'old_CLI_rejects_new_controls_without_upstream':True,
        'old_wheel_sha256':digest(wheel.read_bytes()),'primary_persistent_tree_unchanged':True,'full_original_bytes_verified':True,
        'answers_are_derived_and_not_primary':True,'not_scientific_QA_or_model_quality':True})
    save(args.out/'storage.json',m.stats());print('13 local fixture HTTP requests; 0 remote model calls; contract verified',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--work',type=Path,required=True)
    main(p.parse_args())

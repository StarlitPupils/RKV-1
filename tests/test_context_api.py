import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request,urlopen

from rkv1.core import digest
from rkv1.memory import Memory
from rkv1.memory_model import answer,exposed_hits,messages
from tests.context_protocol_support import FixtureService,corpus,demo_service


class ContextAPITests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.source=self.root/'source';self.source.mkdir();(self.source/'corpus.jsonl').write_bytes(corpus())
        self.memory=Memory.create(self.root/'memory');self.memory.add(self.source)

    def test_default_request_exact_legacy_prompt_and_logged_real_body_bytes(self):
        with FixtureService() as service,patch.dict(os.environ,{'RKV_LLM_API_KEY':''}):
            r=answer(self.memory,'rareanchor',config=service.config)
            expected=messages('rareanchor',exposed_hits(self.memory.search('rareanchor')['hits']))
            self.assertEqual(service.requests[0]['body']['messages'],expected)
            self.assertEqual(r['context_selector'],'source-order');self.assertEqual(r['context_body_budget'],24000)
            self.assertEqual(r['request_body_bytes'],len(service.requests[0]['raw']))
            self.assertEqual(r['prompt_sha256'],digest(service.requests[0]['raw']))
            self.assertEqual(r['context_body_utf8_bytes'],23980);self.assertTrue(r['accepted'])
            again=answer(self.memory,'rareanchor',config=service.config,context_selector='source-order',context_body_budget=24000)
            self.assertEqual(service.requests[0]['raw'],service.requests[1]['raw'])
            self.assertEqual(r['prompt_sha256'],again['prompt_sha256'])

    def test_lexical_original_id_and_budget_all_three_choices(self):
        with FixtureService() as service,patch.dict(os.environ,{'RKV_LLM_API_KEY':''}):
            for budget,expected in [(8000,[2]),(24000,[0,2]),(48000,[0,1,2])]:
                r=answer(self.memory,'rareanchor',config=service.config,context_selector='lexical',context_body_budget=budget)
                self.assertTrue(r['accepted']);self.assertLessEqual(r['context_body_utf8_bytes'],budget)
                self.assertEqual(r['exposed_sentences']['doc:1'],expected)
                self.assertEqual(r['answer']['evidence'][0]['sentence'],2)
                self.assertEqual(r['request_body_bytes'],len(service.requests[-1]['raw']))
                self.assertFalse(r['answer']['scientific_entailment_verified'])
            self.assertEqual(len(service.requests),3)

    def test_invalid_context_controls_do_not_request_or_write(self):
        before=list((self.memory.root/'answers').iterdir())
        with FixtureService() as service,patch.dict(os.environ,{'RKV_LLM_API_KEY':''}):
            for kwargs in ({'context_selector':'unknown'},{'context_body_budget':True},{'context_body_budget':7999},{'context_body_budget':'8000'}):
                with self.subTest(kwargs=kwargs),self.assertRaises(ValueError):answer(self.memory,'rareanchor',config=service.config,**kwargs)
            self.assertEqual(service.requests,[])
        self.assertEqual(before,list((self.memory.root/'answers').iterdir()))

    def test_cli_explicit_controls_and_omitted_citation_fail_closed(self):
        with FixtureService() as service,patch.dict(os.environ,{'RKV_LLM_API_KEY':''}):
            env={k:v for k,v in os.environ.items() if not k.startswith('RKV_LLM_')}
            env.update({'RKV_LLM_BASE_URL':service.url,'RKV_LLM_MODEL':'rkv-local-protocol-fixture'})
            p=subprocess.run([sys.executable,'-m','rkv1','memory-answer',str(self.memory.root),'rareanchor','--context-selector','lexical','--context-body-budget','8000'],env=env,capture_output=True,text=True,encoding='utf-8')
            self.assertEqual(p.returncode,0,p.stderr);r=json.loads(p.stdout)
            self.assertEqual(r['exposed_sentences']['doc:1'],[2]);self.assertTrue(r['accepted'])
            service.reply_mode='omitted';r=answer(self.memory,'rareanchor',config=service.config,context_selector='lexical',context_body_budget=8000)
            self.assertFalse(r['accepted']);self.assertEqual(len(service.requests),2)
            self.assertFalse(json.loads((self.memory.root/'answers'/(r['writeback']['answer_id']+'.json')).read_bytes())['primary_evidence'])

    def test_http_v2_capabilities_forwarding_and_v1_controls_rejection(self):
        def post(base,client,body):
            req=Request(base+'/api/answer',data=json.dumps(body).encode(),headers={'Content-Type':'application/json','X-RKV-Client':client})
            with urlopen(req,timeout=5) as response:return json.load(response)
        with FixtureService() as service,demo_service(self.memory.root,service.url) as (base,status):
            self.assertEqual(status['context_api_version'],2);self.assertEqual(status['context_body_budgets'],[8000,24000,48000])
            with self.assertRaises(HTTPError) as rejected:
                post(base,'memory-v1',{'question':'rareanchor','context_selector':'lexical'})
            self.assertEqual(rejected.exception.code,400);self.assertEqual(service.requests,[])
            r=post(base,'memory-v2',{'question':'rareanchor','context_selector':'lexical','context_body_budget':8000})
            self.assertEqual(r['exposed_sentences']['doc:1'],[2]);self.assertTrue(r['accepted'])
            with self.assertRaises(HTTPError):post(base,'memory-v2',{'question':'rareanchor','context_body_budget':'8000'})
            self.assertEqual(len(service.requests),1)
            r=post(base,'memory-v1',{'question':'rareanchor'})
            self.assertEqual(r['context_selector'],'source-order');self.assertEqual(r['context_body_budget'],24000)
            self.assertEqual(len(service.requests),2)


if __name__=='__main__':unittest.main()

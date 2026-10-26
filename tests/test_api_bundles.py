import json
import unittest
from scripts.api_bundles import catalog,bundles,audit,assert_text_free,public_proof
from scripts.science_bundles import bundles as prior_bundles


class APIBundleTests(unittest.TestCase):
    def test_nested_fixed_sizes_original_rank_and_independent_binding(self):
        raw=b''.join(json.dumps({'doc_id':i,'title':'Synthetic title','abstract':['Synthetic sentence.']}).encode()+b'\n' for i in range(1100))
        index=catalog(raw);selected={}
        for size in (1,3,32):
            plan=bundles(index,size,1);self.assertEqual(len(plan),32)
            self.assertTrue(all(len(q['keys'])==size for q in plan))
            self.assertEqual(plan,bundles(dict(reversed(list(index.items()))),size,1))
            selected[size]={k for q in plan for k in q['keys']};self.assertEqual(len(selected[size]),32*size)
        self.assertLess(selected[1],selected[3]);self.assertLess(selected[3],selected[32])
        self.assertEqual([q['keys'] for q in bundles(index,3,1)],[q['keys'] for q in prior_bundles(index,'spread',1)])
        for bad in (True,0,2,33):
            with self.assertRaises(ValueError):bundles(index,bad,1)
        with self.assertRaises(ValueError):bundles({},32,1)
        keys=bundles(index,1,1)[0]['keys'];key=keys[0];rec=index[key];obj=rec['object'];sid='a'*64
        proof={'snapshot_id':sid,'keys':keys,'hits':[[{'citation_id':'D0','key':key,'title':obj['title'],'sentences':obj['abstract'],
            'rank':None,'source_bytes_verified':True,'locator':{'snapshot_id':sid,'path':'corpus.jsonl','offset':rec['offset'],'length':rec['length'],'sha256':rec['sha256']}}]]}
        self.assertEqual(audit(index,proof,sid),1);assert_text_free(public_proof(proof))
        proof['hits'][0][0]['locator']['offset']+=1
        with self.assertRaises(ValueError):audit(index,proof,sid)

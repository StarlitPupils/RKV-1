import copy
import json
from pathlib import Path
import tempfile
import unittest
from rkv1.memory import Memory
from scripts.query_view import QueryView
from scripts.science_bundles import catalog,bundles,audit,canonical,public_proof,assert_text_free


class ScienceBundleTests(unittest.TestCase):
    def test_rank_plan_preserves_original_offsets_and_workloads(self):
        raw=b''.join(json.dumps({'doc_id':i,'title':'Synthetic Unicode \u4e2d','abstract':['Sentence '+str(i)]},ensure_ascii=False).encode()+b'\r\n' for i in range(140))
        index=catalog(raw);a=bundles(index,'spread',1);b=bundles(index,'repeated',1)
        self.assertEqual(a,bundles(dict(reversed(list(index.items()))),'spread',1))
        self.assertEqual(len({k for x in a for k in x['keys']}),96)
        self.assertEqual(len({k for x in b for k in x['keys']}),32)
        self.assertFalse({k for x in a for k in x['keys']}&{k for x in b for k in x['keys']})
        self.assertTrue(all(len(set(x['keys']))==1 for x in b))
        for key,rec in index.items():self.assertEqual(json.loads(raw[rec['offset']:rec['offset']+rec['length']])['doc_id'],int(key[4:]))
        with self.assertRaises(ValueError):catalog(raw+raw[:raw.index(b'\r\n')+2])
        with self.assertRaises(ValueError):bundles(index,'unknown',1)
        with self.assertRaises(ValueError):bundles({},'spread',1)

    def test_real_store_view_matches_independent_audit_and_public_has_no_text(self):
        raw=b''.join(json.dumps({'doc_id':i,'title':'Synthetic title '+str(i),'abstract':['Synthetic evidence.']}).encode()+b'\n' for i in range(4))
        index=catalog(raw)
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);src=root/'source';src.mkdir();(src/'corpus.jsonl').write_bytes(raw)
            m=Memory.create(root/'memory');sid=m.add(src)['snapshot_id'];keys=['doc:0','doc:1','doc:2']
            expected={'snapshot_id':sid,'keys':keys,'hits':[m.lookup(k,snapshot=sid)['hits'] for k in keys]}
            with QueryView(m,sid):actual={'snapshot_id':sid,'keys':keys,'hits':[m.lookup(k,snapshot=sid)['hits'] for k in keys]}
            self.assertEqual(actual,expected);self.assertEqual(audit(index,actual,sid),3)
            public=public_proof(actual);assert_text_free(public)
            self.assertNotIn(b'Synthetic',canonical(public))
            for field in ('title','sentences','locator'):
                bad=copy.deepcopy(actual)
                if field=='locator':bad['hits'][0][0][field]['offset']+=1
                elif field=='title':bad['hits'][0][0][field]+=' changed'
                else:bad['hits'][0][0][field]=['changed']
                with self.assertRaises(ValueError):audit(index,bad,sid)
            bad=copy.deepcopy(actual);bad['snapshot_id']='0'*64
            with self.assertRaises(ValueError):audit(index,bad,sid)
            with self.assertRaises(ValueError):assert_text_free({'sentences':['hidden']})

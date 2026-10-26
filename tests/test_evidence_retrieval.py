import copy
import json
import math
from pathlib import Path
import tempfile
import unittest
from rkv1.store import Store
from scripts.evidence_retrieval import build_model,lexical,ranking,admit,verified_hits,gold_targets,metrics,encoded,question_identity


def row(qid,keys):
    return {'id':qid,'question':'Synthetic query '+qid,'proof':' & '.join('sent'+str(i+1) for i in range(len(keys)))+' -> hypothesis;',
        'meta':{'triples':{'sent'+str(i+1):'Annotation differs.' for i in range(len(keys))},
                'worldtree_provenance':{'sent'+str(i+1):{'uuid':key} for i,key in enumerate(keys)}}}


class RetrievalTests(unittest.TestCase):
    def test_hand_bm25_exact_alias_and_deterministic_tie(self):
        raw=b'{"a":"alpha alpha beta","b":"beta gamma","alias":"alpha alpha beta","c":"noise"}'
        model,cost=build_model(raw,[]);s=model['shared'];order,score=lexical(s,'alpha')
        expected=math.log(1+(3-1+.5)/(1+.5))*2*2.2/(2+1.2*(.25+.75*3/2))
        self.assertAlmostEqual(score['a'],expected);self.assertEqual(order,['a']);self.assertEqual(s['N'],3)
        self.assertEqual(lexical(s,'missing words')[0],[])
        self.assertEqual(question_identity(' A  QUESTION '),question_identity('a question'))
        with self.assertRaises(ValueError):ranking(model,{'question':'alpha'},'lexical')
        with self.assertRaises(ValueError):ranking(model,'alpha','unknown')

    def test_train_graph_deduplicates_qids_and_permutation_preserves_degree(self):
        raw=b'{"a":"alpha","b":"beta","c":"gamma","d":"delta"}'
        training=[row('one',['a','b']),row('one',['a','b']),row('two',['a','b','c'])]
        m,c=build_model(raw,training);self.assertEqual(m['graph']['a']['b'],2)
        self.assertEqual(m['graph']['a']['c'],1)
        degrees=lambda g:sorted((len(v),sum(v.values())) for v in g.values())
        self.assertEqual(degrees(m['graph']),degrees(m['permuted_graph']))
        self.assertEqual(encoded(m),encoded(build_model(raw,list(reversed(training)))[0]))
        r=ranking(m,'alpha','graph');self.assertEqual(len(r),len(set(r)));self.assertEqual(r[0],'a')
        changed=copy.deepcopy(training)
        for x in changed:x.update(context='GOLD LEAK',answer='SECRET',hypothesis='SECRET',relevance=100)
        self.assertEqual(encoded(m),encoded(build_model(raw,changed)[0]))

    def test_admission_literal_gold_and_unresolved_denominator(self):
        raw=b'{"a":"alpha","b":"beta"}';m,c=build_model(raw,[])
        length=m['shared']['locators']['a']['length']
        selected,used=admit(m,['a','a','b'],max_facts=1,max_source_bytes=length)
        self.assertEqual((selected,used),(['a'],length));self.assertEqual(admit(m,['a'],max_source_bytes=length-1),([],0))
        for args in ({'max_facts':0},{'max_facts':True},{'max_source_bytes':4097}):
            with self.assertRaises(ValueError):admit(m,['a'],**args)
        from scripts.source_alignment import corpus_records
        facts,aliases=corpus_records(raw);r=row('one',['a','missing']);r['meta']['triples']['sent1']='alpha'
        targets,audit,literal=gold_targets(r,facts,aliases)
        self.assertEqual(len(targets),2);self.assertEqual(metrics(['a'],targets)['leaf_recall'],.5)
        self.assertFalse(metrics(['a'],targets)['complete_coverage']);self.assertEqual(len(literal),2)
        self.assertEqual(audit['unresolved'],1)

    def test_verified_hits_exact_original_store_and_corruption(self):
        raw=b'{"a":"alpha fact","b":"beta fact"}';model,c=build_model(raw,[])
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);src=root/'src';src.mkdir();(src/'corpus.json').write_bytes(raw)
            st=Store.create(root/'store',compression='zlib',io_backend='bounded');sid=st.add(src)['snapshot_id']
            with st.snapshot(sid) as snapshot:
                hits=verified_hits(snapshot,model,['a','b']);self.assertEqual([h['fact_id'] for h in hits],['a','b'])
                self.assertTrue(all(h['locator']['snapshot_id']==sid for h in hits))
                ref=snapshot.files['corpus.json']['chunks'][0]
            path=st.object_path(ref['id']);damaged=bytearray(path.read_bytes());damaged[-1]^=1;path.write_bytes(damaged)
            with self.assertRaises(ValueError),st.snapshot(sid) as snapshot:verified_hits(snapshot,model,['a'])

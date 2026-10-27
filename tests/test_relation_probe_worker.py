import argparse,hashlib,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from scripts.evidence_retrieval import encoded,ranking,admit
from scripts.scifact_graph import build_model
from scripts.relation_probe import fit,majority
from scripts import run_relation_probe as runner

class RelationWorkerTests(unittest.TestCase):
 def test_actual_source_four_roles_predict_before_gold_and_missing_unknown_denominators(self):
  raw=b''.join(encoded({'doc_id':i,'title':title,'abstract':[body]})+b'\n' for i,title,body in ((1,'Alpha effect','alpha improves effect'),(2,'Beta effect','beta does not improve effect'),(3,'Other mechanism','unrelated mechanism')));base,_=build_model(raw,[]);base_raw=encoded(base)
  examples=[{'claim':q,'document':d,'target':label} for q,d,label in [('alpha improves','alpha improves',1),('beta improves','beta improves',1),('alpha not improves','alpha improves',0),('beta not improves','beta improves',0)]]
  rows=[{'id':201,'claim':'alpha effect','evidence':{'1':[{'label':'SUPPORT','sentences':[0]}]}},{'id':202,'claim':'beta effect','evidence':{'2':[{'label':'CONTRADICT','sentences':[0]}]}},{'id':203,'claim':'unknown query','evidence':{}}]
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);(root/'docs').mkdir();inputs=root/'inputs';inputs.mkdir();dev=b''.join(encoded(row)+b'\n' for row in rows);(inputs/'corpus.jsonl').write_bytes(raw);(inputs/'claims_dev.jsonl').write_bytes(dev);(root/'docs/scifact-graph-inputs.json').write_bytes(encoded({'files':{'corpus.jsonl':{'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()},'claims_dev.jsonl':{'bytes':len(dev),'sha256':hashlib.sha256(dev).hexdigest()}}}));(root/'base.json').write_bytes(base_raw);models={}
   train_rows=[{'id':i+1,'claim':e['claim'],'evidence':{str(1+i%2):[{'label':'SUPPORT' if e['target'] else 'CONTRADICT','sentences':[0]}]}} for i,e in enumerate(examples)];train_raw=b''.join(encoded(r)+b'\n' for r in train_rows);(inputs/'claims_train.jsonl').write_bytes(train_raw)
   manifest=json.loads((root/'docs/scifact-graph-inputs.json').read_bytes());manifest['files']['claims_train.jsonl']={'bytes':len(train_raw),'sha256':hashlib.sha256(train_raw).hexdigest()};(root/'docs/scifact-graph-inputs.json').write_bytes(encoded(manifest))
   with patch.object(runner,'ROOT',root):runner.train(argparse.Namespace(work=root/'trained',inputs=inputs))
   training=json.loads((root/'trained/training.json').read_bytes());self.assertEqual(training['individual_fits'],3);self.assertEqual(training['majority_count_models'],1);self.assertEqual(training['explicit_training_label_counts']['unannotated_rows'],0)
   models=training['models']
   freeze=root/'freeze.json';freeze.write_bytes(encoded({'source_retrieval_model_sha256':hashlib.sha256(base_raw).hexdigest(),'models':models}));original_probe=runner.RelationProbe;original_gold=runner.labels_for_claim
   for method in runner.METHODS:
    calls=[]
    class Spy:
     def __init__(self,*args,**kwargs):self.probe=original_probe(*args,**kwargs)
     def predict(self,claim,document):calls.append(claim);return self.probe.predict(claim,document)
    def guarded_gold(doc,papers):
     selected=admit(base,ranking(base,doc['claim'],'lexical'))[0];self.assertEqual(calls.count(doc['claim']),len(selected));return original_gold(doc,papers)
    report=root/(method+'-report.json');args=argparse.Namespace(work=root/method,inputs=inputs,model=root/'base.json',model_freeze=freeze,round=1,method=method,worker_report=report)
    with patch.object(runner,'ROOT',root),patch.object(runner,'RelationProbe',Spy),patch.object(runner,'labels_for_claim',guarded_gold):runner.worker(args)
    r=json.loads(report.read_bytes());self.assertEqual(r['retrieved_rows'],3);self.assertEqual(r['annotated_rows'],2);self.assertEqual(r['unannotated_rows'],1);self.assertEqual(r['relation_metrics']['all_explicit_labeled_gold_pairs'],2);self.assertGreater(r['relation_metrics']['selected_without_gold_annotation'],0);self.assertTrue(r['store_unchanged']);self.assertTrue(all(not pred['scientific_entailment_verified'] and pred['generated_answer'] is None for rec in r['records'] for pred in rec['predictions']))
    self.assertEqual(r['recovery']['source_sha256'],hashlib.sha256(raw).hexdigest());self.assertTrue(all(rec['retrieval']['admitted_record_bytes']<=4096 and len(rec['retrieval']['selected_ids'])<=12 for rec in r['records']))

if __name__=='__main__':unittest.main()

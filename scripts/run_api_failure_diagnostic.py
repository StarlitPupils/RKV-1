"""Audit all original outputs without model transport, classify original provided sources."""
import json,hashlib,time,sys,os
from pathlib import Path
from scripts.audit_api_intervention import audit
from scripts.api_failure_taxonomy import classify,summarize
from rkv1.benchmark import peak_rss

def sha(raw):return hashlib.sha256(raw).hexdigest()
def write(p,obj):
 with p.open('x',encoding='utf-8',newline='\n') as f:json.dump(obj,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
def run(config,out):
 out=Path(out);out.mkdir(exist_ok=False);start=time.perf_counter();cpu=time.process_time();ok=False
 try:
  if len(config['cohorts'])!=2:raise ValueError('Exactly two original cohorts required')
  for name,meta in config['inputs'].items():
   raw=Path(name).read_bytes();assert len(raw)==meta['bytes'] and sha(raw)==meta['sha256'],name
  allrows=[];groups={};seen=set();bindings=returned=0
  for cohort in config['cohorts']:
   draft=Path(cohort['draft']);folder=Path(cohort['campaign']);plan=json.loads((draft/'plan.json').read_bytes());questions={str(v['claim_id']):v['claim'] for v in json.loads((draft/'questions-private.json').read_bytes())};gold={str(v['id']):v for v in json.loads((draft/'gold-private.json').read_bytes())};context=json.loads((draft/'retrieval-context-private.json').read_bytes());assert not seen&set(questions),'CohortID overlap';seen.update(questions)
   a=audit(folder,context['store_root_private'],plan,questions,gold);assert a['complete'] and a['H1_mechanical_audit'];assert a['groups']==json.loads(Path(cohort['prior_derived']).read_bytes())['groups'];bindings+=a['source_records_independently_checked'];returned+=a['source_application_B'];hits=json.loads((folder/'retrieval-private.json').read_bytes())
   for row in a['rows']:
    job=plan['jobs'][row['index']];provided=[] if row['condition']=='empty' else hits[job['donor_claim_id']];gold_ids={str(k) for k,v in gold[row['claim_id']]['evidence'].items() if v};selected_ids={h['key'].removeprefix('doc:') for h in provided};label=classify(gold_ids,selected_ids,row['correct'],row['grounded_annotated_correct']);allrows.append({'cohort':cohort['name'],'index':row['index'],'claim_id':row['claim_id'],'condition':row['condition'],'gold_papers':sorted(gold_ids),'provided_papers':sorted(selected_ids),'any_annotated_paper_available':bool(gold_ids&selected_ids),'correct':row['correct'],'grounded':row['grounded_annotated_correct'],'category':label})
   for condition in ('empty','retrieved','rotated'):groups[cohort['name']+':'+condition]=summarize([x['category'] for x in allrows if x['cohort']==cohort['name'] and x['condition']==condition])
  assert len(allrows)==96 and len(seen)==32
  result={'H1_original_source_scores_and_denominators':True,'H2_per_cohort':{c['name']:groups[c['name']+':retrieved']['missing_paper_strict_majority'] for c in config['cohorts']},'rows':allrows,'groups':groups,'old_output_count':96,'unique_questions':32,'primary_annotated_retrieved':24,'new_model_calls':0,'new_retrieval_trials':0,'source_bindings':bindings,'application_returned_B':returned,'posthoc_known_outputs_not_new_science':True};write(out/'worker.json',result);ok=True;return result
 finally:write(out/'body-finally.json',{'success':ok,'full_body_wall_s':time.perf_counter()-start,'full_body_CPU_s':time.process_time()-cpu,'peak_RSS_B':peak_rss()})
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--out',required=True);a=p.parse_args();t=time.perf_counter();c=time.process_time();ok=False
 try:run(json.loads(Path(a.config).read_bytes()),a.out);ok=True
 finally:write(Path(a.out)/'process-finally.json',{'success':ok,'module_main_wall_s':time.perf_counter()-t,'module_main_CPU_s':time.process_time()-c,'peak_RSS_B':peak_rss()})

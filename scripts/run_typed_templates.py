"""Original-human pipeline with scoped train-only compiler injection."""
import argparse,json,time
from pathlib import Path
from collections import Counter
from unittest.mock import patch
import scripts.run_human_source_coverage as original
from scripts.typed_templates import LearnedCompiler,load_model
from rkv1.core import digest
from rkv1.benchmark import peak_rss
from scripts.evidence_retrieval import encoded
from scripts.run_source_alignment import exclusive

def run_theory(raw,work,index,*,role,model=None,compiler=None,gold_observer=None):
 if role=='baseline':return original.run_theory(raw,work,index,method='human',gold_observer=gold_observer)
 if role not in ('learned','control'):raise ValueError('Explicit matching trained model role required')
 if compiler is None:
  if model is None or model['role']!=role:raise ValueError('Matching training model role required')
  compiler=LearnedCompiler(model,world='OWA')
 if compiler.model['role']!=role:raise ValueError('Compiler model role differs')
 with patch.object(original,'HumanSourceCompiler',side_effect=lambda *,world:compiler):
  return original.run_theory(raw,work,index,method='human',gold_observer=gold_observer)

def worker(a):
 start=time.perf_counter();cpu=time.process_time();folder=Path(a.work);folder.mkdir(exist_ok=False);meta=json.loads(Path(a.input_meta).read_bytes());prefix=Path(meta['prefix_path']).read_bytes();assert digest(prefix)==meta['prefix_sha256'] and len(prefix)==meta['prefix_bytes'];rows=prefix.splitlines(keepends=True);assert len(rows)==32;model=None;compiler=None;loaded_B=0;load_wall=load_cpu=0.;model_sha=None
 if a.role!='baseline':
  mm=json.loads(Path(a.model_meta).read_bytes());e=mm['models'][a.role];t=time.perf_counter();c=time.process_time();model=load_model(e['path'],e['sha256']);compiler=LearnedCompiler(model,world='OWA');model=None;load_wall=time.perf_counter()-t;load_cpu=time.process_time()-c;loaded_B=Path(e['path']).stat().st_size;model_sha=e['sha256']
 theories=[]
 for i,raw in enumerate(rows):
  rec=run_theory(raw,folder,i,role=a.role,compiler=compiler);exclusive(folder/('theory-'+str(i)+'-aggregate.json'),encoded(rec)+b'\n');theories.append(rec)
 flat=[q for t in theories for q in t['records']];total=len(flat);correct=sum(q['correct'] for q in flat);accepted=sum(q['accepted_controlled_English_with_reference_alignment'] for q in flat);classes={label:{'total':sum(q['gold']==label for q in flat),'correct':sum(q['gold']==label and q['correct'] for q in flat)} for label in ('True','False','Unknown')};retained={p.relative_to(folder).as_posix():{'bytes':p.stat().st_size,'sha256':digest(p.read_bytes())} for p in folder.rglob('*') if p.is_file()};report={'round':a.round,'role':a.role,'theories':32,'questions':total,'correct':correct,'accepted':accepted,'allquestion_accuracy':correct/total if total else None,'H1_learned_atleast95percent_and3classes':a.role=='learned' and total>0 and correct*100>=95*total and all(c['total']>0 for c in classes.values()),'H2_learned_allaccepted_and32_actual_recoveries':a.role=='learned' and accepted==total and all(t['recovery'] and t['compilation_audit'] for t in theories),'classes':classes,'accepted_wrong':sum(q['accepted_controlled_English_with_reference_alignment'] and not q['correct'] for q in flat),'source_failure_theories':sum(t['compilation_failure'] is not None for t in theories),'source_failure_counts':dict(Counter(t['compilation_failure'] for t in theories if t['compilation_failure'])),'postreference_alignment_failure_theories':sum(t['compilation_audit_error'] is not None for t in theories),'original_recovery_theories':sum(t['recovery'] is not None for t in theories),'source_English_bindings':sum(t['source_English_bindings'] for t in theories),'derived_record_DAG_bindings':sum(t['derived_record_DAG_bindings'] for t in theories),'theory_records':theories,'current_loaded_model_bytes':loaded_B,'model_sha256':model_sha,'model_load_wall_s':load_wall,'model_load_cpu_s':load_cpu,'worker_wall_s':time.perf_counter()-start,'worker_cpu_s':time.process_time()-cpu,'peak_RSS_bytes':peak_rss(),'retained_all_work_files':retained,'retained_all_work_bytes':sum(e['bytes'] for e in retained.values()),'new_training_runs_in_worker':0,'new_remote_model_calls':0,'scientific_entailment_verified':False,'unrestricted_English_NLI_verified':False,'generated_answers':0,'physical_SSD_bytes':None,'all_system_IO_bytes':None,'cold_cache':None,'cross_machine':None,'scope':'Train-only typedtemplate model vs frozenhuman grammar andequalB permutedcontrol; originalsentence/mapping/reference/goldpostprediction audit, not broadNLI','abstention_speed_not_gain':True};exclusive(Path(a.report),encoded(report)+b'\n');print(json.dumps({'role':a.role,'round':a.round,'questions':total,'correct':correct,'accepted':accepted,'sourcefail':report['source_failure_theories']}),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);p.add_argument('--input-meta',type=Path,required=True);p.add_argument('--model-meta',type=Path,required=True);p.add_argument('--role',choices=('baseline','learned','control'),required=True);p.add_argument('--round',type=int,required=True);p.add_argument('--report',type=Path,required=True);worker(p.parse_args())

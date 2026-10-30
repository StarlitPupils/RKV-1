"""Owned model/campaign integration only; no real scientific evaluation yet."""
import json
from pathlib import Path
import time
from rkv1.experiments.paper_retriever import PaperRetriever, ranking
from rkv1.benchmark import peak_rss
from scripts.source_evidence_views import build_view, verify_view, METHODS
from scripts.view_admission import canonical


class ViewRetriever:
    def __init__(self, root, sid, model_path, model_sha):
        self.reader=PaperRetriever(root,sid,model_path,model_sha256=model_sha)
        info=self.reader.model_info()
        self.header={'snapshot_id':sid,'path':'corpus.jsonl','source_sha256':info['source_sha256']}
        self.root=root
        self.info=info

    def query(self, question, *, method):
        ordered=ranking(self.reader._model,question,'lexical')[:12]
        rows=[{'id':key,'binding':{**self.header,'record_offset':self.reader._model['shared']['locators'][key]['offset'],
                'record_length':self.reader._model['shared']['locators'][key]['length'],
                'record_sha256':self.reader._model['shared']['locators'][key]['sha256'],'field':'abstract'}} for key in ordered]
        view=build_view(self.root,question,rows,method=method,byte_cap=20000,source_header=self.header)
        verified=verify_view(self.root,bytes.fromhex(view['encoded_hex']),question,rows,method=method,byte_cap=20000,source_header=self.header)
        return {'ordered_candidate_ids':ordered,'trusted_records':rows,'view':view,'source_verification':verified}


def run(root,sid,model_path,model_sha,questions,*,method,out,guard=None):
    if method not in METHODS or type(questions) is not list or not 1<=len(questions)<=270:
        raise ValueError('Bounded exact question cohort and method required')
    ids=set();normalized=set()
    for q in questions:
        if type(q) is not dict or set(q)!={'id','question'} or type(q['id']) is not str or not q['id'] or type(q['question']) is not str or not q['question'].strip() or len(q['question'].encode())>4096:
            raise ValueError('Question-only schema; no annotation or answer fields')
        identity=' '.join(q['question'].split()).casefold()
        if q['id'] in ids or identity in normalized:raise ValueError('Duplicate cohort ID or normalized question')
        ids.add(q['id']);normalized.add(identity)
    out=Path(out);out.mkdir(exist_ok=False)
    start,cpu,success,rows=time.perf_counter(),time.process_time(),False,[]
    try:
        if guard:guard()
        t,c=time.perf_counter(),time.process_time()
        reader=ViewRetriever(root,sid,model_path,model_sha)
        constructor={'wall_s':time.perf_counter()-t,'CPU_s':time.process_time()-c,'model_info':reader.info}
        for index,q in enumerate(questions):
            if guard:guard()
            t,c=time.perf_counter(),time.process_time()
            result=reader.query(q['question'],method=method)
            row={'index':index,'id':q['id'],'question':q['question'],'result':result,
                 'query_wall_s':time.perf_counter()-t,'query_CPU_s':time.process_time()-c}
            with (out/f'prediction-{index}.json').open('xb') as stream:stream.write(canonical(row)+b'\n')
            rows.append({'index':index,'id':q['id']})
        result={'method':method,'planned_queries':len(questions),'completed_queries':len(rows),'constructor':constructor,'prediction_ids':rows,'model_SHA':model_sha,'snapshot_id':sid,'gold_read_by_worker':False,'new_model_API_calls':0}
        with (out/'worker.json').open('xb') as stream:stream.write(canonical(result)+b'\n')
        success=True
        return result
    finally:
        with (out/'worker-finally.json').open('xb') as stream:stream.write(canonical({'success':success,'completed_queries':len(rows),'planned_queries':len(questions),'full_wall_s':time.perf_counter()-start,'full_CPU_s':time.process_time()-cpu,'peak_RSS_B':peak_rss(),'formal_retries':0})+b'\n')

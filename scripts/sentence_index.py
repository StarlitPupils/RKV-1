"""Private candidate utility: lexical abstract-unit index and original parent checks."""
from collections import Counter,defaultdict
import json
from rkv1.core import digest
from scripts.evidence_retrieval import tokens,encoded,ranking,admit,lexical
from scripts.source_string_spans import abstract_units

def build_index(raw,paper_model):
    shared=paper_model['shared']
    if digest(raw)!=shared['source_sha256'] or shared['source_kind']!='scifact-whole-original-record-v1':raise ValueError('Original paper source/model identity differs')
    locators={};parents={};postings=defaultdict(dict);lengths={}
    for paper,loc in sorted(shared['locators'].items()):
        original=raw[loc['offset']:loc['offset']+loc['length']]
        if len(original)!=loc['length'] or digest(original)!=loc['sha256']:raise ValueError('Original parent record differs')
        units=abstract_units(original,parent_offset=loc['offset']);obj=json.loads(original)
        if 'doc:'+str(obj['doc_id'])!=paper:raise ValueError('Original parent paper ID differs')
        parents[paper]={**loc,'sentence_count':len(units),'title_sha256':digest(obj['title'].encode('utf-8'))}
        for unit in units:
            if unit['paper_id']!=paper or unit['unit_id'] in locators:raise ValueError('Original abstract unit identity differs')
            key=unit['unit_id'];locators[key]={k:v for k,v in unit.items() if k not in ('text','unit_id','parent_offset','parent_length','parent_sha256')}
            tf=Counter(tokens(unit['text']));lengths[key]=sum(tf.values())
            for token,n in tf.items():postings[token][key]=n
    if not locators or not sum(lengths.values()):raise ValueError('No tokenized abstract source units')
    model={'shared':{'source_sha256':digest(raw),'source_kind':'scifact-json-string-abstract-v1','locators':locators,
        'postings':dict(postings),'doc_lengths':lengths,'N':len(locators),'avgdl':sum(lengths.values())/len(locators),
        'parameters':{'k1':1.2,'b':.75,'text_projection':'abstract_sentence_only','parent_score':'max_sentence_score'}},'parents':parents}
    return model,{'parent_papers':len(parents),'abstract_units':len(locators),'empty_token_units':sum(n==0 for n in lengths.values()),
        'source_kind':'scifact-json-string-abstract-v1','new_training_runs':0,'new_unlabelled_source_index_builds':1,
        'component_bytes':{k:len(encoded(v)) for k,v in model.items()}}

def verified_units(snapshot,model,selected):
    if snapshot.files['corpus.jsonl']['sha256']!=model['shared']['source_sha256']:raise ValueError('Snapshot/model source differs')
    hits=[]
    for key in selected:
        unit=model['shared']['locators'][key];paper=unit['paper_id'];parent=model['parents'][paper]
        # Intentionally revalidate full original parent for every selected unit;
        # no decoded-parent reuse is assumed free or hidden in admission bytes.
        original=snapshot.read_range('corpus.jsonl',parent['offset'],parent['length'])
        if digest(original)!=parent['sha256']:raise ValueError('Original scientific parent SHA differs')
        obj=json.loads(original);i=unit['sentence_index']
        if 'doc:'+str(obj['doc_id'])!=paper or not 0<=i<len(obj['abstract']) or digest(obj['title'].encode())!=parent['title_sha256']:raise ValueError('Original scientific parent identity differs')
        raw=snapshot.read_range('corpus.jsonl',unit['offset'],unit['length'])
        begin=unit['offset']-parent['offset']
        if begin<0 or begin+unit['length']>len(original) or raw!=original[begin:begin+unit['length']] or digest(raw)!=unit['sha256']:raise ValueError('Original abstract byte span differs')
        decoded=json.loads(raw)
        if decoded!=obj['abstract'][i] or digest(decoded.encode('utf-8'))!=unit['decoded_text_sha256']:raise ValueError('Original abstract sentence identity differs')
        hits.append({'unit_id':key,'paper_id':paper,'sentence_index':i,'locator':{'snapshot_id':snapshot.snapshot_id,'path':'corpus.jsonl',
            **{k:unit[k] for k in ('offset','length','sha256')}},'parent_locator':{'snapshot_id':snapshot.snapshot_id,'path':'corpus.jsonl',
            **{k:parent[k] for k in ('offset','length','sha256')}},'decoded_text_sha256':unit['decoded_text_sha256']})
    return hits

def parent_ranking(model,claim):
    ordered,scores=lexical(model['shared'],claim);best={};parent_scores={}
    for key in ordered:
        paper=model['shared']['locators'][key]['paper_id']
        if paper not in best:best[paper]=key;parent_scores[paper]=scores[key]
    ranked=sorted(best,key=lambda paper:(-parent_scores[paper],paper))
    return ranked,best

def verified_parent_hits(snapshot,paper_model,unit_model,selected,best):
    if snapshot.files['corpus.jsonl']['sha256']!=paper_model['shared']['source_sha256'] or unit_model['shared']['source_sha256']!=paper_model['shared']['source_sha256']:raise ValueError('Snapshot/parent/unit source differs')
    hits=[];hints=[]
    for paper in selected:
        parent=paper_model['shared']['locators'][paper];raw=snapshot.read_range('corpus.jsonl',parent['offset'],parent['length'])
        if digest(raw)!=parent['sha256'] or unit_model['parents'][paper]['sha256']!=parent['sha256']:raise ValueError('Original whole-parent SHA differs')
        obj=json.loads(raw)
        if 'doc:'+str(obj['doc_id'])!=paper:raise ValueError('Original parent ID differs')
        key=best[paper];unit=unit_model['shared']['locators'][key];offset=unit['offset']-parent['offset'];i=unit['sentence_index']
        if unit['paper_id']!=paper or not 0<=i<len(obj['abstract']) or offset<0 or offset+unit['length']>len(raw):raise ValueError('Best unit outside original parent')
        original=raw[offset:offset+unit['length']]
        if digest(original)!=unit['sha256'] or json.loads(original)!=obj['abstract'][i] or digest(obj['abstract'][i].encode('utf-8'))!=unit['decoded_text_sha256']:raise ValueError('Best original sentence identity differs')
        hits.append({'paper_id':paper,'locator':{'snapshot_id':snapshot.snapshot_id,'path':'corpus.jsonl',**parent},
            'abstract_sha256':digest(encoded(obj['abstract'])),'title_sha256':digest(obj['title'].encode('utf-8'))})
        hints.append({'paper_id':paper,'unit_id':key,'sentence_index':i,'locator':{'snapshot_id':snapshot.snapshot_id,'path':'corpus.jsonl',
            **{k:unit[k] for k in ('offset','length','sha256')}},'decoded_text_sha256':unit['decoded_text_sha256']})
    return hits,hints

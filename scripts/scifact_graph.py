"""Known SciFact transfer adapter; frozen retrieval math, whole original records."""
from collections import Counter,defaultdict
import itertools
import json
from rkv1.core import digest
from rkv1.memory import records
from scripts.evidence_retrieval import encoded,tokens,question_identity,ranking,admit,metrics


def paper_records(raw):
    papers={}
    for key,title,sentences,offset,original,kind in records('corpus.jsonl',raw):
        if key in papers:raise ValueError('Duplicate paper identity')
        papers[key]={'title':title,'sentences':sentences,'projection':'\n'.join([title,*sentences]),
            'offset':offset,'length':len(original),'sha256':digest(original),'kind':kind}
    if not papers:raise ValueError('Empty paper corpus')
    return papers


def evidence_ids(claim,papers):
    result=set()
    for docid,sets in claim['evidence'].items():
        key='doc:'+str(docid)
        if key not in papers or not sets:raise ValueError('Evidence source identity missing')
        for evidence in sets:
            if not evidence['sentences'] or any(type(i) is not int or not 0<=i<len(papers[key]['sentences']) for i in evidence['sentences']):
                raise ValueError('Invalid original rationale sentence index')
        result.add(key)
    return result


def build_model(raw,training):
    papers=paper_records(raw);postings=defaultdict(dict);lengths={};pairs=defaultdict(set);annotated=0
    for key,rec in papers.items():
        tf=Counter(tokens(rec['projection']));lengths[key]=sum(tf.values())
        for token,n in tf.items():postings[token][key]=n
    for claim in training:
        gold=evidence_ids(claim,papers);annotated+=bool(gold)
        for pair in itertools.combinations(sorted(gold),2):pairs[pair].add(str(claim['id']))
    graph=defaultdict(dict)
    for (a,b),ids in sorted(pairs.items()):graph[a][b]=graph[b][a]=len(ids)
    ids=sorted(papers);permutation=dict(zip(ids,sorted(ids,key=lambda k:(digest(('rkv050control:'+k).encode()),k))))
    control={permutation[k]:{permutation[n]:w for n,w in sorted(edges.items())} for k,edges in sorted(graph.items())}
    shared={'source_sha256':digest(raw),'locators':{k:{name:rec[name] for name in ('offset','length','sha256')} for k,rec in papers.items()},
        'postings':dict(postings),'doc_lengths':lengths,'N':len(papers),'avgdl':sum(lengths.values())/len(papers),
        'train_ids':sorted({str(c['id']) for c in training}),'train_question_sha256':sorted({question_identity(c['claim']) for c in training}),
        'parameters':{'k1':1.2,'b':.75,'max_facts':12,'source_budget':4096,'seeds':6,'neighbors':6},
        'source_kind':'scifact-whole-original-record-v1','identity_policy':'Distinct original paper IDs never merged by equal text'}
    model={'shared':shared,'graph':dict(graph),'permuted_graph':control}
    return model,{'corpus_documents':len(papers),'training_rows':len(training),'annotated_training_rows':annotated,
        'graph_nodes':len(graph),'undirected_graph_edges':len(pairs),'component_bytes':{k:len(encoded(v)) for k,v in model.items()},
        'component_sha256':{k:digest(encoded(v)) for k,v in model.items()},'whole_original_record_budget':True}


def verified_hits(snapshot,model,selected):
    result=[]
    for key in selected:
        loc=model['shared']['locators'][key];raw=snapshot.read_range('corpus.jsonl',loc['offset'],loc['length'])
        if digest(raw)!=loc['sha256']:raise ValueError('Original scientific record SHA differs')
        obj=json.loads(raw)
        if 'doc:'+str(obj['doc_id'])!=key:raise ValueError('Original paper ID differs')
        result.append({'paper_id':key,'locator':{'snapshot_id':snapshot.snapshot_id,'path':'corpus.jsonl',**loc},
            'abstract_sha256':digest(encoded(obj['abstract'])),'title_sha256':digest(obj['title'].encode())})
    return result

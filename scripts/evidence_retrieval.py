"""Assessment-only question-to-fact retrieval; train graph, exact source aliases."""
from collections import Counter,defaultdict
import itertools
import json
import math
import re
from rkv1.core import digest
from rkv1.memory import STOP
from rkv1.memory_qasper import members

MAX_FACTS=12
SOURCE_BUDGET=4096
SEEDS=6
NEIGHBORS=6
K1=1.2
B=0.75


def encoded(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')


def question_identity(text):return digest(re.sub(r'\s+',' ',text.strip().casefold()).encode('utf-8'))


def tokens(text):return [t for t in re.findall('[a-z0-9]+',text.casefold()) if len(t)>1 and t not in STOP]


from scripts.source_alignment import corpus_records,alignments


def gold_targets(row,facts,aliases):
    records=alignments(row,facts,aliases);targets=set();literal=set();counts=Counter()
    for rec in records:
        key=rec['fact_id'];counts[rec['resolution']]+=1
        missing='unresolved:'+rec['annotation_text_sha256']
        targets.add(key if key is not None else missing)
        literal.add(key if key is not None and rec['annotation_exact'] else 'nonliteral:'+rec['annotation_text_sha256'])
        if key is not None and not rec['annotation_exact']:counts['annotated_text_differs']+=1
    return targets,dict(counts),literal


def build_model(raw,training):
    facts,aliases=corpus_records(raw);postings=defaultdict(dict);lengths={};pair_questions=defaultdict(set);counts=Counter()
    for key,rec in facts.items():
        tf=Counter(tokens(rec['text']));lengths[key]=sum(tf.values())
        for token,n in tf.items():postings[token][key]=n
    for row in training:
        targets,audit,_=gold_targets(row,facts,aliases);counts.update(audit)
        resolved=sorted(k for k in targets if k in facts)
        for pair in itertools.combinations(resolved,2):pair_questions[pair].add(row['id'])
    graph=defaultdict(dict)
    for (a,b),questions in sorted(pair_questions.items()):graph[a][b]=graph[b][a]=len(questions)
    ids=sorted(facts);shuffled=sorted(ids,key=lambda k:(digest(('rkv050control:'+k).encode()),k));permutation=dict(zip(ids,shuffled))
    control={permutation[k]:{permutation[n]:w for n,w in sorted(v.items())} for k,v in sorted(graph.items())}
    shared={'source_sha256':digest(raw),'aliases':aliases,'locators':{key:{k:rec[k] for k in ('offset','length','sha256')} for key,rec in facts.items()},
        'postings':dict(postings),'doc_lengths':lengths,'N':len(facts),'avgdl':sum(lengths.values())/len(facts),
        'train_ids':sorted({r['id'] for r in training}),'train_question_sha256':sorted({question_identity(r['question']) for r in training}),
        'parameters':{'k1':K1,'b':B,'max_facts':MAX_FACTS,'source_budget':SOURCE_BUDGET,'seeds':SEEDS,'neighbors':NEIGHBORS}}
    return {'shared':shared,'graph':dict(graph),'permuted_graph':control},{'train_rows':len(training),'train_unique_ids':len(shared['train_ids']),
        'source_alias_ids':len(aliases),'exact_unique_facts':len(facts),'graph_nodes':len(graph),'undirected_graph_edges':len(pair_questions),
        'gold_mapping_counts':dict(counts),'shared_bytes':len(encoded(shared)),'positive_graph_bytes':len(encoded(graph)),
        'control_graph_bytes':len(encoded(control))}


def lexical(shared,question):
    if not isinstance(question,str):raise ValueError('Only question text is a retrieval query')
    scores=defaultdict(float);N=shared['N'];avg=shared['avgdl']
    for token,qf in sorted(Counter(tokens(question)).items()):
        posting=shared['postings'].get(token,{})
        if not posting:continue
        idf=math.log(1+(N-len(posting)+.5)/(len(posting)+.5))
        for key,tf in sorted(posting.items()):
            scores[key]+=qf*idf*tf*(K1+1)/(tf+K1*(1-B+B*shared['doc_lengths'][key]/avg))
    return sorted(scores,key=lambda key:(-scores[key],key)),dict(scores)


def ranking(model,question,method):
    ordered,scores=lexical(model['shared'],question)
    if method=='lexical':return ordered
    if method not in ('graph','permuted_graph'):raise ValueError('Unknown method')
    graph=model[method];seeds=ordered[:SEEDS];neighbors=defaultdict(float)
    for seed in seeds:
        edges=graph.get(seed,{ });total=sum(edges.values())
        if total:
            for node,weight in sorted(edges.items()):
                if node not in seeds:neighbors[node]+=scores[seed]*weight/total
    expansion=sorted(neighbors,key=lambda node:(-neighbors[node],node))[:NEIGHBORS]
    return list(dict.fromkeys(seeds+expansion+ordered))


def admit(model,ranked,*,max_facts=MAX_FACTS,max_source_bytes=SOURCE_BUDGET):
    if type(max_facts) is not int or not 1<=max_facts<=MAX_FACTS:raise ValueError('Invalid fact-count admission budget')
    if type(max_source_bytes) is not int or not 0<=max_source_bytes<=SOURCE_BUDGET:raise ValueError('Invalid source-byte admission budget')
    selected=[];seen=set();used=0
    for key in ranked:
        if key in seen:continue
        seen.add(key);length=model['shared']['locators'][key]['length']
        if used+length>max_source_bytes:continue
        selected.append(key);used+=length
        if len(selected)==max_facts:break
    return selected,used


def verified_hits(snapshot,model,selected):
    hits=[]
    for key in selected:
        loc=model['shared']['locators'][key];raw=snapshot.read_range('corpus.json',loc['offset'],loc['length'])
        if digest(raw)!=loc['sha256']:raise ValueError('Original corpus member SHA differs')
        value=json.loads(b'{'+raw+b'}')
        if set(value)!={key} or not isinstance(value[key],str):raise ValueError('Original member identity differs')
        hits.append({'fact_id':key,'locator':{'snapshot_id':snapshot.snapshot_id,'path':'corpus.json',**loc},
                     'decoded_text_sha256':digest(value[key].encode('utf-8'))})
    return hits


def metrics(selected,gold):
    hits=len(set(selected)&set(gold));n=len(gold)
    return {'gold_groups':n,'recovered_groups':hits,'leaf_recall':hits/n if n else 0.0,
            'complete_coverage':bool(n) and hits==n}

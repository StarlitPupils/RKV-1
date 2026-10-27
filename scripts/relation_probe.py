"""Small lexical relation classifier, never a scientific entailment certificate."""
from collections import Counter,defaultdict
import hashlib,json,math,random,re
from scripts.evidence_retrieval import question_identity
BUCKETS=128
DIMENSION=389
EPOCHS=200
LEARNING_RATE=.5
L2=.01
NEGATION=frozenset(('no','not','never','without','neither','nor'))
LABELS=('CONTRADICT','SUPPORT')
PARAMETERS={'buckets_per_channel':128,'dimension':389,'epochs':200,'learning_rate':.5,'L2_excluding_bias':.01,'features':'hashed-claim_document_shared-logTF-L2-plus4scalars-bias-v1','tokenizer':'casefold-ascii-alnum-all-including-stopwords','threshold':.5,'shuffle_seed':20261027}

def words(value):
    if type(value) is not str or len(value)>1_048_576:raise ValueError('Bounded original string required')
    return re.findall('[a-z0-9]+',value.casefold())

def features(claim,document,*,claim_only=False):
    if type(claim_only) is not bool:raise ValueError('Explicit boolean feature switch required')
    c=Counter(words(claim))
    if type(document) is not str or len(document)>1_048_576:raise ValueError('Bounded original document required')
    d=Counter() if claim_only else Counter(words(document));result=[0.]*DIMENSION
    channels=(c,Counter() if claim_only else d,Counter() if claim_only else Counter({t:min(c[t],d[t]) for t in c.keys()&d.keys()}))
    for channel,counts in enumerate(channels):
        values=[0.]*BUCKETS
        for token,count in sorted(counts.items()):values[int.from_bytes(hashlib.sha256(token.encode()).digest()[:8],'little')%BUCKETS]+=1+math.log(count)
        norm=math.sqrt(sum(v*v for v in values))
        if norm:
            for i,value in enumerate(values):result[channel*BUCKETS+i]=value/norm
    cn=bool(c.keys()&NEGATION);dn=bool(d.keys()&NEGATION)
    result[384]=float(cn);result[385]=0. if claim_only else float(dn);result[386]=0. if claim_only else float(cn!=dn);result[387]=0. if claim_only else len(c.keys()&d.keys())/max(1,len(c));result[388]=1.
    return result

def labeled_pairs(rows,papers):
    groups={};counts=Counter({'input_rows':0,'unannotated_rows':0,'physical_annotated_claim_paper_rows':0,'ambiguous_unique_pairs':0,'unique_SUPPORT':0,'unique_CONTRADICT':0})
    for row in rows:
        if type(row.get('claim')) is not str or type(row.get('evidence')) is not dict:raise ValueError('Original claim/evidence mapping required')
        counts['input_rows']+=1
        if not row['evidence']:counts['unannotated_rows']+=1
        for doc_id,rationales in row['evidence'].items():
            key='doc:'+str(doc_id)
            if key not in papers or type(rationales) is not list or not rationales:raise ValueError('Annotated original document required')
            labels=set()
            for evidence in rationales:
                label=evidence.get('label');indices=evidence.get('sentences')
                if label not in LABELS or type(indices) is not list or not indices or any(type(i) is not int or not 0<=i<len(papers[key]['sentences']) for i in indices):raise ValueError('Explicit support/contradict rationale label/index required')
                labels.add(label)
            identity=(question_identity(row['claim']),key);g=groups.setdefault(identity,{'question_sha256':identity[0],'paper_id':key,'claim':row['claim'],'document':papers[key]['projection'],'labels':set(),'original_claim_ids':set()});g['labels'].update(labels);g['original_claim_ids'].add(str(row['id']));counts['physical_annotated_claim_paper_rows']+=1
    result=[]
    for key,g in sorted(groups.items()):
        if len(g['labels'])!=1:counts['ambiguous_unique_pairs']+=1;continue
        label=next(iter(g['labels']));counts['unique_'+label]+=1;result.append({k:v for k,v in g.items() if k not in ('labels','original_claim_ids')}|{'target':LABELS.index(label),'original_claim_ids':sorted(g['original_claim_ids'])})
    counts['unique_unambiguous_pairs']=len(result);counts['all_unique_pair_groups']=len(groups)
    return result,dict(counts)

def sigmoid(value):return 1/(1+math.exp(-max(-40.,min(40.,value))))

def gradient(matrix,targets,weights):
    if not matrix or len(matrix)!=len(targets):raise ValueError('Nonempty aligned training rows required')
    g=[0.]*DIMENSION
    for x,y in zip(matrix,targets):
        delta=sigmoid(sum(a*b for a,b in zip(x,weights)))-y
        for i,value in enumerate(x):g[i]+=delta*value
    return [value/len(matrix)+(L2*weights[i] if i!=DIMENSION-1 else 0.) for i,value in enumerate(g)]

def objective(matrix,targets,weights):
    values=[]
    for x,y in zip(matrix,targets):
        z=sum(a*b for a,b in zip(x,weights));values.append(max(z,0)+math.log1p(math.exp(-abs(z)))-y*z)
    return sum(values)/len(values)+.5*L2*sum(w*w for w in weights[:-1])

def fit(examples,method):
    if method not in ('pair','claim_only','permuted_pair') or not examples:raise ValueError('Fixed nonempty training role required')
    labels=[e['target'] for e in examples]
    if any(type(y) is not int or y not in (0,1) for y in labels) or set(labels)!={0,1}:raise ValueError('Both explicit relation classes required')
    original_labels=list(labels)
    if method=='permuted_pair':random.Random(20261027).shuffle(labels)
    matrix=[features(e['claim'],e['document'],claim_only=method=='claim_only') for e in examples];weights=[0.]*DIMENSION;weights[-1]=math.log((sum(labels)+.5)/(len(labels)-sum(labels)+.5));trace=[]
    for epoch in range(EPOCHS):
        g=gradient(matrix,labels,weights);weights=[w-LEARNING_RATE*delta for w,delta in zip(weights,g)]
        if epoch in (0,24,49,99,199):trace.append({'epoch':epoch+1,'training_objective':objective(matrix,labels,weights)})
    if not all(math.isfinite(w) for w in weights):raise ValueError('Nonfinite trained weights')
    model={'schema':'lexical-scientific-relation-probe-v1','method':method,'parameters':dict(PARAMETERS),'weights':weights,'training_pairs':len(labels),'training_class_counts':{'CONTRADICT':len(labels)-sum(labels),'SUPPORT':sum(labels)},'scientific_entailment_verified':False}
    return model,{'individual_fit':1,'permuted_label_positions_changed':sum(a!=b for a,b in zip(original_labels,labels)) if method=='permuted_pair' else None,'epochs':EPOCHS,'class_counts_preserved_by_shuffle':model['training_class_counts'],'training_objective_trace':trace,'feature_matrix_float_values':len(matrix)*DIMENSION}

def majority(examples):
    counts=Counter(e['target'] for e in examples)
    if set(counts)!={0,1}:raise ValueError('Both explicit relation classes required')
    return {'schema':'lexical-scientific-relation-probe-v1','method':'majority','parameters':dict(PARAMETERS),'weights':None,'training_pairs':len(examples),'training_class_counts':{'CONTRADICT':counts[0],'SUPPORT':counts[1]},'scientific_entailment_verified':False}

class RelationProbe:
    def __init__(self,raw,*,sha256):
        if type(raw) is not bytes or len(raw)>1<<20 or type(sha256) is not str or hashlib.sha256(raw).hexdigest()!=sha256:raise ValueError('Explicit bounded relation model SHA differs')
        model=json.loads(raw)
        if model.get('schema')!='lexical-scientific-relation-probe-v1' or model.get('parameters')!=PARAMETERS or model.get('method') not in ('majority','pair','claim_only','permuted_pair') or model.get('scientific_entailment_verified') is not False:raise ValueError('Unsupported relation probe identity/parameters')
        counts=model.get('training_class_counts',{});n=model.get('training_pairs')
        if type(n) is not int or n<2 or set(counts)!=set(LABELS) or any(type(v) is not int or v<1 for v in counts.values()) or sum(counts.values())!=n:raise ValueError('Invalid explicit training class denominator')
        w=model.get('weights');method=model['method']
        if method=='majority':
            if w is not None:raise ValueError('Majority baseline has no fitted weights')
        elif type(w) is not list or len(w)!=DIMENSION or any(type(v) not in (int,float) or not math.isfinite(v) for v in w):raise ValueError('Invalid relation weight vector')
        self._method=method;self._weights=tuple(w) if w is not None else None;self._prior=counts['SUPPORT']/n
    def predict(self,claim,document):
        if type(claim) is not str or type(document) is not str or len(claim)>1_048_576 or len(document)>1_048_576:raise ValueError('Bounded original strings required')
        score=self._prior if self._method=='majority' else sigmoid(sum(a*b for a,b in zip(features(claim,document,claim_only=self._method=='claim_only'),self._weights)))
        return {'predicted_relation':'SUPPORT' if score>=.5 else 'CONTRADICT','support_score_uncalibrated':score,'scientific_entailment_verified':False,'generated_answer':None}

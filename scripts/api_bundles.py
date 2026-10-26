"""Frozen nested batch-size workload; original scientific text stays private."""
import random
from rkv1.core import digest
from scripts.science_bundles import SOURCE_SHA,SOURCE_BYTES,catalog,canonical,public_proof,assert_text_free,exclusive,ledger


def bundles(index,size,round_number):
    if type(size) is not int or size not in (1,3,32):raise ValueError('Unsupported batch size')
    ordered=sorted(index,key=lambda k:(digest(('rkv046:'+k).encode('ascii')),k))
    if len(ordered)<32*size:raise ValueError('Insufficient original keys')
    result=[{'case_id':f'k{size}-c{i:02d}','keys':ordered[size*i:size*(i+1)]} for i in range(32)]
    random.Random(20261026+round_number).shuffle(result)
    return result


def audit(index,proof,snapshot):
    size=len(proof['keys'])
    if proof['snapshot_id']!=snapshot or size not in (1,3,32) or len(proof['hits'])!=size:raise ValueError('Bundle identity/count differs')
    for key,group in zip(proof['keys'],proof['hits']):
        rec=index[key];obj=rec['object']
        locator={'snapshot_id':snapshot,'path':'corpus.jsonl','offset':rec['offset'],'length':rec['length'],'sha256':rec['sha256']}
        expected={'citation_id':'D0','key':key,'title':obj['title'],'sentences':obj['abstract'],'rank':None,'source_bytes_verified':True,'locator':locator}
        if group!=[expected]:raise ValueError('Original byte/JSON member binding differs')
    return size

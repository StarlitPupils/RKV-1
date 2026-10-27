"""Owned deterministic random-posting control, not random-byte entropy noise."""
import random
from scripts.postings_transform import canonical

def control(seed=20261027):
    rng=random.Random(seed);ids=['ctrl:'+format(rng.getrandbits(96),'024x') for _ in range(256)];assert len(set(ids))==256
    lengths={key:0 for key in ids};posts={}
    for _ in range(1024):
        token='tok_'+format(rng.getrandbits(96),'024x');assert token not in posts;posting={}
        for key in rng.sample(ids,8):
            tf=rng.randrange(1,65536);posting[key]=tf;lengths[key]+=tf
        posts[token]=posting
    return canonical({'shared':{'source_kind':'owned-random-posting-control-v1','N':len(ids),'avgdl':sum(lengths.values())/len(ids),'doc_lengths':lengths,'postings':posts},'graph':{},'permuted_graph':{}})

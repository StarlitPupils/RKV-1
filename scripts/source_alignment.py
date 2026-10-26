"""Train-only source identity audit; exact aliases, never a semantic matcher."""
from collections import defaultdict
import json
import re
from rkv1.core import digest
from rkv1.memory_qasper import members


def corpus_records(raw):
    if not raw.lstrip().startswith(b'{'):raise ValueError('Complete corpus object required')
    records={};groups=defaultdict(list)
    for key,value,offset,original in members(raw):
        if not isinstance(value,str):raise ValueError('Corpus facts must be strings')
        records[key]={'text':value,'offset':offset,'length':len(original),'sha256':digest(original)}
        groups[value].append(key)
    if not records:raise ValueError('Empty corpus')
    aliases={key:min(group) for group in groups.values() for key in group}
    return {key:records[key] for key in sorted(records) if aliases[key]==key},aliases


def alignments(row,facts,aliases):
    leaves=sorted(set(re.findall(r'\bsent\d+\b',row['proof'])))
    if not leaves:raise ValueError('Authoritative proof has no source leaves')
    bytext={r['text']:key for key,r in facts.items()};result=[]
    for leaf in leaves:
        obj=row['meta']['worldtree_provenance'][leaf];text=row['meta']['triples'][leaf];uid=obj['uuid']
        if uid in aliases:key=aliases[uid];method='provided_UUID'
        elif text in bytext:key=bytext[text];method='exact_decoded_text'
        else:key=None;method='unresolved'
        result.append({'leaf_id':leaf,'resolution':method,'fact_id':key,
            'annotation_text_sha256':digest(text.encode('utf-8')),
            'annotation_exact':text==facts[key]['text'] if key is not None else None})
    return result


def verify_binding(snapshot,facts,key):
    rec=facts[key];raw=snapshot.read_range('corpus.json',rec['offset'],rec['length'])
    if digest(raw)!=rec['sha256'] or json.loads(b'{'+raw+b'}')!={key:rec['text']}:
        raise ValueError('Original corpus member identity differs')
    return {'snapshot_id':snapshot.snapshot_id,'path':'corpus.json',
            **{k:rec[k] for k in ('offset','length','sha256')}}

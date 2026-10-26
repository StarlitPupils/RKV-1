"""Synthetic facts and an independent original-record proof auditor."""
import json
from rkv1.core import digest

CHAINS=32
DISTRACTORS=768


def revision(chain,epoch):
    return max([0]+[e for e in range(1,epoch+1) if chain in {((e-1)*6+k)%30 for k in range(6)}])


def value(chain,epoch):
    return f'assay-{chain:02d} revision-{revision(chain,epoch):02d} literal=1.00e-3 caf'+chr(233)+' '+chr(38634)


def corpus(epoch):
    records=[]
    for chain in range(CHAINS):
        base=chain*3;rev=revision(chain,epoch)
        for step in range(3):
            if chain==31 and step==1 and epoch>=6:continue
            directive=(f'RKVNEXT doc:{base+step+1}' if step<2 else 'RKVVALUE '+value(chain,epoch))
            if chain==30 and step==1 and epoch>=12:directive=f'RKVNEXT doc:{base}'
            records.append({'doc_id':base+step,'title':f'Synthetic assay {chain:02d}, record {step}',
                            'abstract':['Synthetic fixture only; escaped "quote", caf'+chr(233)+' '+chr(38634),
                                        'Revision padding '+('x'*rev if step==2 else ''),directive]})
    for i in range(DISTRACTORS):
        records.append({'doc_id':10000+i,'title':f'Synthetic distractor {i:04d}',
                        'abstract':['Unrelated calibration. No executable reference. '+('z'*80)]})
    return b''.join(json.dumps(r,ensure_ascii=True,sort_keys=True,separators=(',',':')).encode()+b'\r\n' for r in records)


def gold(chain,epoch):
    base=chain*3
    if chain==31 and epoch>=6:return 'missing',None,[f'doc:{base}']
    if chain==30 and epoch>=12:return 'cycle',None,[f'doc:{base}',f'doc:{base+1}']
    return 'complete',value(chain,epoch),[f'doc:{base+i}' for i in range(3)]


def audit(memory,proof,*,snapshot,root_key):
    """Do not call trace/lookup or import its regexes; read actual CAS records."""
    if proof['snapshot_id']!=snapshot or proof['root_key']!=root_key or proof['primary_evidence'] is not False:
        raise ValueError('Proof identity mismatch')
    expected=root_key;requested=0
    with memory.store.snapshot(snapshot) as source:
        for hop in proof['evidence']:
            loc=hop['locator']
            if hop['key']!=expected or loc['snapshot_id']!=snapshot:raise ValueError('Hop binding mismatch')
            raw=source.read_range(loc['path'],loc['offset'],loc['length']);requested+=len(raw)
            if digest(raw)!=loc['sha256']:raise ValueError('Original record SHA differs')
            obj=json.loads(raw)
            if 'doc:'+str(obj['doc_id'])!=hop['key']:raise ValueError('Original member identity differs')
            quote=obj['abstract'][hop['sentence_index']]
            if quote!=hop['quote'] or digest(quote.encode('utf-8'))!=hop['quote_utf8_sha256']:
                raise ValueError('Quote differs from original JSON member')
            if hop['directive']=='next':
                if not quote.startswith('RKVNEXT doc:'):raise ValueError('Not an explicit reference')
                expected=quote[len('RKVNEXT '):]
            elif hop['directive']=='value':
                if not quote.startswith('RKVVALUE ') or quote[len('RKVVALUE '):]!=proof['value']:
                    raise ValueError('Terminal value differs')
                if hop is not proof['evidence'][-1]:raise ValueError('Evidence after terminal')
            else:raise ValueError('Unknown directive')
    if requested!=proof['admitted_record_bytes']:raise ValueError('Admitted bytes differ')
    if proof['status']=='complete' and (not proof['evidence'] or proof['evidence'][-1]['directive']!='value'):
        raise ValueError('Incomplete terminal proof')
    if proof['status']!='complete' and proof['value'] is not None:raise ValueError('Unsupported terminal value')
    return {'bindings':len(proof['evidence']),'requested_record_bytes':requested,
            'physical_read_or_decompressed_bytes':None}

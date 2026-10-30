"""Deterministic owned update stream, not scientific claims or human dialogue."""
import json

SIZES=(9,65,257)
ROLES=('fresh','reuse_two','disabled')
ORDER=(ROLES,(ROLES[1],ROLES[2],ROLES[0]),(ROLES[2],ROLES[0],ROLES[1]))
REVISIONS=12


def corpus(size,revision):
    if type(size) is not int or not 1<=size<=257 or type(revision) is not int or not 0<=revision<REVISIONS:
        raise ValueError('Bounded explicit owned size/revision required')
    rows=[]
    for i in range(size):
        state=revision if i%7==0 else 0
        rows.append({'doc_id':i,'title':'Owned alpha beta group'+str(i%5),
                     'abstract':['Owned observation '+str(i)+' epoch'+str(state)+' alpha gamma.',
                                 'Local negative evidence beta delta epsilon '+str(i%11)+'.',
                                 'Literal '+('supports' if (i+state)%2==0 else 'contradicts')+' owned rule.',
                                 'Duplicate owned sentence.','Duplicate owned sentence.']})
    return b''.join(json.dumps(r,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()+b'\n' for r in rows)


def requests(revision):
    previous=max(0,revision-1)
    return [(revision,'alpha beta'),(revision,'gamma delta'),(previous,'alpha epoch0'),
            (revision,'zzznomatchterm'),(0,'beta epsilon'),(revision,'alpha gamma'),
            (previous,'beta delta'),(revision,'group3')]

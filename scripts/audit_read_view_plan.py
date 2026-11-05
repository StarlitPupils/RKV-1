"""Saved output audit from original JSONL/Store; does not call candidate methods."""
import copy,json,shutil
from pathlib import Path
from rkv1.memory import Memory
from scripts.read_view_fixture import meta,ledger,publish,sha

def verify(memory,result,original,sid,operation):
    if result['snapshot_id']!=sid:raise ValueError('Independent SID mismatch')
    with memory.store.snapshot(sid) as snap:
        raw=snap.read_range('corpus.jsonl')
    if raw!=original:raise ValueError('Independent entire source mismatch')
    bykey={};pos=0
    for line in original.splitlines(keepends=True):
        obj=json.loads(line);key='doc:'+str(obj['doc_id'])
        if key in bykey:raise ValueError('Duplicate source key')
        bykey[key]=(pos,line,obj);pos+=len(line)
    if operation=='batch':
        if [g['source_key'] for g in result['results']]!=['doc:0','doc:1','doc:0']:raise ValueError('Independent batch groups differ')
        groups=[g['hits'] for g in result['results']]
        if any(len(g)!=1 for g in groups):raise ValueError('Independent batch occurrences differ')
        hits=[h for g in groups for h in g]
        if result['admitted_source_bytes']!=sum(h['locator']['length'] for h in hits):raise ValueError('Independent admission byte count differs')
    else:hits=result['hits']
    keys=[h['key'] for h in hits]
    expected=['doc:0','doc:1','doc:2','doc:3'] if operation=='search' else ['doc:2'] if operation=='lookup' else ['doc:0','doc:1','doc:0']
    if (sorted(keys)!=expected if operation=='search' else keys!=expected):raise ValueError('Independent source selection differs')
    for h in hits:
        offset,line,obj=bykey[h['key']]
        locator=h['locator']
        if set(locator)!=set(('snapshot_id','path','offset','length','sha256')) or locator['snapshot_id']!=sid or locator['path']!='corpus.jsonl':raise ValueError('Independent locator binding differs')
        if type(locator['offset']) is not int or type(locator['length']) is not int or (locator['offset'],locator['length'],locator['sha256'])!=(offset,len(line),sha(line)):raise ValueError('Independent physical boundary differs')
        if h['title']!=obj['title'] or h['sentences']!=obj['abstract'] or h['source_bytes_verified'] is not True:raise ValueError('Independent original text mismatch')
    return len(raw)

def audit(root,out,external):
    root,out=Path(root),Path(out);before=ledger(root);out.mkdir(exist_ok=False)
    summary=json.loads((root/'summary.json').read_bytes());n=summary['size'];m=Memory(root/'memory');raws={};sids={0:summary['old_sid']};total=0;clocks=[];norm={}
    for epoch in (0,1,2):
        path=root/'originals'/f'{epoch}.jsonl'
        if meta(path)!=external[f'{n}:{epoch}']:raise ValueError('External source anchor mismatch')
        raws[epoch]=path.read_bytes()
        if epoch:sids[epoch]=json.loads((root/f'PUBLISHED-{epoch}').read_bytes())['new_sid']
    if m.current()!=sids[2]:raise ValueError('Final HEAD differs')
    roles=('pinned','explicit','current');sequence=[('baseline',op) for op in ('search','lookup','batch')]
    for epoch in (1,2):sequence += [(f'overlap-{epoch}','search')]+[(f'after-{epoch}',op) for op in ('search','lookup','batch')]
    for role in roles:
        rows=sorted((root/role).glob('row-*.json'))
        if len(rows)!=11:raise ValueError('Full planned query denominator not saved')
        if [p.name for p in rows]!=[f'row-{i:02}.json' for i in range(11)]:raise ValueError('Query sequence differs')
        norm[role]=[]
        for p,(phase,op) in zip(rows,sequence):
            row=json.loads(p.read_bytes());epoch=0
            if role=='current' and phase!='baseline':
                number=int(phase[-1]);epoch=number-1 if phase.startswith('overlap') else number
            if (row['role'],row['operation'],row['phase'],row['expected_epoch'])!=(role,op,phase,epoch):raise ValueError('Independent fixed schedule differs')
            total+=verify(m,row['result'],raws[epoch],sids[epoch],op)
            if row['primary_audit']['source_SHA']!=sha(raws[epoch]) or row['primary_audit']['whole_source_application_return_B']!=len(raws[epoch]):raise ValueError('Primary source charge differs')
            result=copy.deepcopy(row['result']);result.pop('wall_s');norm[role].append(result)
            if phase.startswith('overlap'):
                number=int(phase[-1]);entered=json.loads((root/role/f'QUERY-ENTERED-{number}').read_bytes());wready=json.loads((root/f'WRITER-READY-{number}').read_bytes());wend=json.loads((root/f'PUBLISHED-{number}').read_bytes())
                if entered['selected_sid']!=sids[epoch] or not wready['before_head_ns']<=entered['entered_ns']<=wend['after_head_ns']<=row['finished_ns']:raise ValueError('Actual cross-process publication/query overlap not proved')
                clocks.append({'role':role,'revision':number,'selected_sid':entered['selected_sid'],'before_head_ns':wready['before_head_ns'],'query_entered_ns':entered['entered_ns'],'after_head_ns':wend['after_head_ns'],'query_finished_ns':row['finished_ns']})
    if norm['pinned']!=norm['explicit']:raise ValueError('New view differs from unchanged explicit-SID API')
    for row in summary['parent_exits']:
        parent=json.loads((root/(row['role']+'-PARENT-EXIT')).read_bytes());started=json.loads((root/(row['role']+'-STARTED')).read_bytes());footer=json.loads((root/(row['role']+'-entry-finally.json')).read_bytes())
        if parent!=row or parent['producer_observed_exit_code']!=0 or parent['launcher_exit_code']!=0 or parent['actual_pid']!=started['actual_pid'] or footer['actual_pid']!=started['actual_pid'] or footer['success'] is not True:raise ValueError('Observed process exit/footer identity differs')
    old=json.loads((root/'baseline-identities.json').read_bytes());now=ledger(root/'memory')
    for name,v in old.items():
        if name!='HEAD.json' and now[name]!=v:raise ValueError('Retained source/index changed')
    # Corruption controls are isolated copies; original memory and saved queries immutable.
    from rkv1.memory_view import ReadView
    controls=[];control_source_B=0
    bad=copy.deepcopy(json.loads((root/'pinned'/'row-00.json').read_bytes())['result']);bad['hits'][0]['sentences'][0]='tampered owned evidence'
    publish(out/'bad-returned-query.json',bad)
    try:verify(m,bad,raws[0],sids[0],'search')
    except ValueError:controls.append('returned_literal_tamper_refused');control_source_B+=len(raws[0])
    else:raise ValueError('Returned text tamper accepted')
    for kind in ('CAS','manifest','HEAD'):
        dest=out/('bad-'+kind);shutil.copytree(root/'memory',dest);cm=Memory(dest);view=ReadView(cm,snapshot=sids[0])
        if kind=='CAS':
            with cm.store.snapshot(sids[0]) as snap:key=snap.header['files'][0]['chunks'][0]['id']
            path=cm.store.object_path(key);data=bytearray(path.read_bytes());data[-1]^=1;path.write_bytes(data)
        elif kind=='manifest':
            path=cm.root/'manifests'/(sids[0]+'.json');data=json.loads(path.read_bytes());data['records']+=1;path.write_bytes(json.dumps(data).encode())
        else:
            path=cm.root/'HEAD.json';path.write_bytes(b'{"version":1,"snapshot_id":"'+b'0'*64+b'"}')
        if kind=='HEAD':
            result=view.lookup('doc:2');control_source_B+=verify(cm,result,raws[0],sids[0],'lookup')
            try:ReadView(cm)
            except (ValueError,FileNotFoundError):controls.append('existing_pin_independent_of_later_bad_HEAD_new_pin_refused')
            else:raise ValueError('Bad HEAD substituted for implicit pin')
        else:
            try:view.lookup('doc:2')
            except ValueError:controls.append('existing_pin_reverifies_'+kind)
            else:raise ValueError('Open view skipped corruption verification')
        view.close()
    if ledger(root)!=before:raise ValueError('Audit mutated original workload')
    answer={'size':n,'processes':4,'saved_operations_verified':33,'full_source_restores':33,'source_application_return_B':total,'control_full_source_restores':2,'control_source_application_return_B':control_source_B,'corruption_controls':controls,'overlap_intervals':clocks,'pinned_equals_unchanged_explicit_SID':True,'originals_immutable':True,'no_writer_replay':True,'not_answer_or_semantic_quality':True}
    publish(out/'audit.json',answer);return answer

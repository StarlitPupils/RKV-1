"""Original-source/history/actual exits; never acquire candidate lock for main audit."""
import json,copy,shutil
from pathlib import Path
from rkv1.memory import Memory
from scripts.audit_read_view_plan import verify as original_verify
from scripts.writer_scope_fixture import ledger,meta,publish,PHASES

def audit(root,out,external):
    root,out=Path(root),Path(out);before=ledger(root);out.mkdir(exist_ok=False)
    summary=json.loads((root/'summary.json').read_bytes());n=summary['size'];rows=summary['rows'];restores=total=control_B=0;controls=[]
    if len(rows)!=3 or [r['phase'] for r in rows]!=list(PHASES):raise ValueError('Full fixed case denominator absent')
    for row in rows:
        folder=root/row['phase'];raws={}
        for e in (0,1,2):
            p=folder/'originals'/f'{e}.jsonl'
            if meta(p)!=external[f'{n}:{e}']:raise ValueError('External source identity differs')
            raws[e]=p.read_bytes()
        m=Memory(folder/'memory');old=json.loads((folder/'BASELINE').read_bytes());ready=json.loads((folder/'A-READY').read_bytes());blocked=json.loads((folder/'B-CONTENTION').read_bytes());acquired=json.loads((folder/'B-ACQUIRED').read_bytes());bready=json.loads((folder/'B-READY').read_bytes());parentblocked=json.loads((folder/'PARENT-B-CONTENTION').read_bytes())
        phase=row['phase'];epoch=0 if phase=='before_HEAD' else 1;sids={0:old['old_sid'],1:ready['known_sid'],2:bready['snapshot_id']}
        if row['old_sid']!=sids[0] or row['A_known_sid']!=sids[1] or row['B_distinct_source_sid']!=sids[2] or len(set(sids.values()))!=3:raise ValueError('Three distinct source intents differ')
        if m.current()!=sids[2] or row['A_visible_epoch_while_held']!=epoch or row['A_call_completed']!=(phase=='clean_close'):raise ValueError('Visibility conflated with operation completion')
        if not blocked['refused_before_add'] or not parentblocked['refused']:raise ValueError('Contender not refused')
        if json.loads((folder/'BEFORE-CONTENTION-IDENTITIES').read_bytes())!=json.loads((folder/'HELD-IDENTITIES').read_bytes()):raise ValueError('Refused writer changed Memory')
        if not ready['ready_ns']<=blocked['observed_ns']<row['parents']['A']['observed_ns']<acquired['acquired_ns']<=bready['returned_ns']<=parentblocked['observed_ns']<row['parents']['B']['observed_ns']:raise ValueError('Actual competition/exit/acquisition timeline differs')
        for role in ('A','B'):
            parent=json.loads((folder/(role+'-PARENT-EXIT')).read_bytes());started=json.loads((folder/(role+'-STARTED')).read_bytes());cleanup=json.loads((folder/(role+'-CLEANUP')).read_bytes());footer=folder/(role+'-entry-finally.json')
            if parent!=row['parents'][role] or parent['producer_pid']!=started['producer_pid'] or cleanup['actual_producer_exit']!=parent['producer_observed_exit'] or cleanup['terminated_by_cleanup']:raise ValueError('Observed producer identity/exit differs')
            complete=(role=='B' or phase=='clean_close')
            if (parent['producer_observed_exit']==0)!=complete or footer.exists()!=complete:raise ValueError('Missing footer converted to completion')
            if complete:
                f=json.loads(footer.read_bytes())
                if not f['success'] or f['producer_pid']!=parent['producer_pid']:raise ValueError('Worker finally differs')
        for role in ('current','pin','explicit'):
            for label,current in [('A-held',epoch),('B-held',2)]:
                q=json.loads((folder/f'{label}-{role}-query.json').read_bytes());e=current if role=='current' else 0
                if (q['phase'],q['reader'],q['source_epoch'])!=(label,role,e):raise ValueError('Fixed read schedule differs')
                total+=original_verify(m,q['result'],raws[e],sids[e],'search');restores+=1
                if q['primary_audit']['whole_source_application_return_B']!=len(raws[e]):raise ValueError('Source charge differs')
        now=ledger(folder/'memory')
        for name,identity in old['files'].items():
            if name!='HEAD.json' and now[name]!=identity:raise ValueError('Old history changed')
        if not (folder/'memory'/'.writer.lock').is_file():raise ValueError('Persistent lock pathname was removed')
        # Independent isolated selected-CAS/manifest and returned literal controls.
        for kind in ('CAS','manifest'):
            bad=out/(phase+'-bad-'+kind);shutil.copytree(folder/'memory',bad);cm=Memory(bad);pin=cm.pin(snapshot=sids[0])
            if kind=='CAS':
                with cm.store.snapshot(sids[0]) as snap:key=snap.header['files'][0]['chunks'][0]['id']
                path=cm.store.object_path(key);data=bytearray(path.read_bytes());data[-1]^=1;path.write_bytes(data)
            else:
                path=cm.root/'manifests'/(sids[0]+'.json');value=json.loads(path.read_bytes());value['records']+=1;path.write_bytes(json.dumps(value).encode())
            try:pin.search('RKV99PROBE',top_k=8)
            except ValueError:controls.append({'phase':phase,'kind':kind,'refused':True})
            else:raise ValueError('Corrupt old source accepted')
            finally:pin.close()
        bad=copy.deepcopy(json.loads((folder/'A-held-pin-query.json').read_bytes())['result']);bad['hits'][0]['sentences'][0]='changed owned evidence';publish(out/(phase+'-bad-returned.json'),bad)
        try:original_verify(m,bad,raws[0],sids[0],'search')
        except ValueError:controls.append({'phase':phase,'kind':'returned_literal','refused':True});control_B+=len(raws[0])
        else:raise ValueError('Bad returned literal accepted')
    if ledger(root)!=before:raise ValueError('Original workload mutated by audit')
    answer={'size':n,'cases':3,'actual_A_terminations':2,'fresh_writer_processes':6,'queries_verified':restores,'source_application_return_B':total,'corrupt_controls':controls,'control_full_source_restores':3,'control_source_application_return_B':control_B,'old_source_history_and_case_timelines_verified':True,'lock_release_not_operation_completion':True,'all_original_files_unchanged':True,'no_writer_or_candidate_lock_replay_in_main_audit':True}
    publish(out/'audit.json',answer);return answer

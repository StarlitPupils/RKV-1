from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from rkv1.memory import Memory,_json
from rkv1.memory_budget import DEFAULT_BUDGET,budget,evaluate,range_work
from rkv1.memory_index import configuration


class ReplayBudgetTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.source=self.root/'source';self.source.mkdir()

    def write(self,docs):
        (self.source/'corpus.jsonl').write_bytes(b''.join(_json(d)+b'\n' for d in docs))

    def compare(self,left,right):
        for q in ('calibration','marker','absentword'):
            self.assertEqual(left.search(q,top_k=20)['hits'],right.search(q,top_k=20)['hits'])

    def test_change_count_boundary_checkpoints_without_losing_old_snapshot(self):
        docs=[{'doc_id':i,'title':f'Calibration {i}','abstract':['short marker']} for i in range(256)]
        self.write(docs);m=Memory.create(self.root/'bounded');full=Memory.create(self.root/'full',index_profile='compact-full-v2')
        first=m.add(self.source,label='base')['snapshot_id'];full.add(self.source,label='base')
        for doc in docs[:32]:doc['title']='X'+doc['title'][1:]
        self.write(docs);allowed=m.add(self.source,label='32');full.add(self.source,label='32')
        self.assertEqual(allowed['delta_depth'],1);self.assertIsNone(allowed['replay_budget']['reason']);self.compare(m,full)
        docs[32]['title']='X'+docs[32]['title'][1:];self.write(docs)
        checked=m.add(self.source,label='33');full.add(self.source,label='33')
        self.assertEqual(checked['checkpoint_reason'],'budget-changes');self.assertEqual(checked['delta_depth'],0);self.compare(m,full)
        self.assertTrue(m.search('calibration',snapshot=first)['hits'])

    def test_record_bytes_and_cas_amplification_are_independent_guards(self):
        docs=[{'doc_id':i,'title':f'Calibration {i}','abstract':['marker '+('z'*1024)]} for i in range(64)]
        self.write(docs);limits={**DEFAULT_BUDGET,'max_record_bytes':4096,'max_cas_bytes':1<<30}
        m=Memory.create(self.root/'bytes',replay_budget=limits);full=Memory.create(self.root/'full',index_profile='compact-full-v2')
        m.add(self.source,label='base');full.add(self.source,label='base')
        for doc in docs[:2]:doc['title']='X'+doc['title'][1:]
        self.write(docs);result=m.add(self.source,label='two');full.add(self.source,label='two')
        self.assertEqual(result['checkpoint_reason'],'budget-record-bytes');self.compare(m,full)
        docs=[{'doc_id':i,'title':f'Calibration {i}','abstract':['marker '+('x'*200)]} for i in range(256)]
        self.write(docs);m=Memory.create(self.root/'cas',chunk_size=4096,replay_budget={**DEFAULT_BUDGET,'max_cas_bytes':8192})
        m.add(self.source,label='base')
        docs[1]['title']='X'+docs[1]['title'][1:];self.write(docs);one=m.add(self.source,label='one')
        self.assertEqual(one['replay_budget']['cas_bytes'],8192);self.assertEqual(one['delta_depth'],1)
        docs[2]['title']='X'+docs[2]['title'][1:];self.write(docs);two=m.add(self.source,label='two')
        self.assertEqual(two['checkpoint_reason'],'budget-cas-bytes');self.assertEqual(two['replay_budget']['cas_bytes'],16384)

    def test_range_work_matches_real_cross_chunk_reads_and_counts_repeated_reads(self):
        raw=b'0123456789abcdef'*1000;(self.source/'text.txt').write_bytes(raw)
        m=Memory.create(self.root/'memory',chunk_size=4096);sid=m.add(self.source)['snapshot_id']
        with m.store.snapshot(sid) as snap:
            meta=['file:text.txt','text.txt',4088,32,'unused','text']
            calls=[];original=m.store.block
            def block(key,size):calls.append(size);return original(key,size)
            with patch.object(m.store,'block',side_effect=block):self.assertEqual(snap.read_range('text.txt',4088,32),raw[4088:4120])
            self.assertEqual(range_work(snap,meta),sum(calls));self.assertEqual(range_work(snap,meta),8192)
            empty=[*meta[:2],0,0,*meta[4:]];self.assertEqual(range_work(snap,empty),0)
            prior={'file:text.txt':meta};changed=[*meta[:4],'different',meta[5]]
            measured=evaluate(m,sid,sid,prior,[],[changed],{**DEFAULT_BUDGET,'max_cas_bytes':1<<30})
            self.assertEqual(measured['record_reads'],2);self.assertEqual(measured['cas_bytes'],2*sum(calls))
            # Same SHA/path-only metadata needs no old/new FTS text read.
            measured=evaluate(m,sid,sid,prior,[],[[*meta[:1],'elsewhere',*meta[2:]]],DEFAULT_BUDGET)
            self.assertEqual(measured['record_reads'],0);self.assertEqual(measured['cas_bytes'],0)

    def test_configuration_is_validated_before_root_or_cas_publication(self):
        for value in ({}, {**DEFAULT_BUDGET,'max_changes':True},{**DEFAULT_BUDGET,'version':True},
                      {**DEFAULT_BUDGET,'max_cas_bytes':0},{**DEFAULT_BUDGET,'extra':1}):
            with self.assertRaises(ValueError):Memory.create(self.root/'invalid',replay_budget=value)
            self.assertFalse((self.root/'invalid').exists())
        with self.assertRaises(ValueError):Memory.create(self.root/'legacy',index_profile='compact-base-v3',replay_budget=DEFAULT_BUDGET)
        (self.source/'note.txt').write_bytes(b'marker');m=Memory.create(self.root/'valid');first=m.add(self.source)
        path=m.root/'indexes/config.json';value=configuration(m);value['replay_budget']['max_changes']=False;path.write_bytes(_json(value))
        before=set((m.root/'cas/snapshots').iterdir());(self.source/'note.txt').write_bytes(b'marker changed')
        with self.assertRaisesRegex(ValueError,'replay budget'):m.add(self.source,label='bad')
        self.assertEqual(before,set((m.root/'cas/snapshots').iterdir()));self.assertEqual(m.current(),first['snapshot_id'])
        value['replay_budget']=None;path.write_bytes(_json(value))
        with self.assertRaisesRegex(ValueError,'replay budget'):m.add(self.source,label='null')
        self.assertEqual(before,set((m.root/'cas/snapshots').iterdir()))

    def test_legacy_configuration_is_preserved_and_cli_selects_new_or_old_profile(self):
        (self.source/'note.txt').write_bytes(b'marker')
        for profile in ('compact-base-v3','compact-budget-v3','compact-full-v2'):
            path=self.root/profile
            cmd=[sys.executable,'-m','rkv1','memory-init',str(path),str(self.source),'--index-profile',profile]
            result=subprocess.run(cmd,capture_output=True,text=True,encoding='utf-8');self.assertEqual(result.returncode,0,result.stderr)
            m=Memory(path);self.assertEqual(configuration(m)['profile'],profile)
            self.assertEqual('replay_budget' in configuration(m),profile=='compact-budget-v3')

    def test_explicit_enable_changes_only_future_policy_and_failed_publish_is_atomic(self):
        (self.source/'note.txt').write_bytes(b'marker')
        m=Memory.create(self.root/'legacy-enable',index_profile='compact-base-v3');first=m.add(self.source)
        head=(m.root/'HEAD.json').read_bytes();manifest=(m.root/'manifests'/(first['snapshot_id']+'.json')).read_bytes()
        previous=(m.root/'indexes/config.json').read_bytes()
        with patch('rkv1.memory.os.replace',side_effect=OSError('injected')):
            with self.assertRaises(OSError):m.enable_replay_budget()
        self.assertEqual((m.root/'indexes/config.json').read_bytes(),previous)
        result=subprocess.run([sys.executable,'-m','rkv1','memory-budget',str(m.root)],capture_output=True,text=True,encoding='utf-8')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(configuration(m)['profile'],'compact-budget-v3')
        self.assertEqual((m.root/'HEAD.json').read_bytes(),head)
        self.assertEqual((m.root/'manifests'/(first['snapshot_id']+'.json')).read_bytes(),manifest)
        self.assertTrue(m.search('marker',snapshot=first['snapshot_id'])['hits'])
        (self.source/'note.txt').write_bytes(b'marker new revision');changed=m.add(self.source,label='new-writer-policy')
        self.assertIsNotNone(changed['replay_budget']);self.assertEqual(changed['replay_budget']['limits'],DEFAULT_BUDGET)


if __name__=='__main__':unittest.main()

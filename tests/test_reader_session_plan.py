import json,tempfile,unittest,hashlib
from pathlib import Path
from scripts.run_reader_session_plan import run
from scripts.audit_reader_session import audit


class OwnedUpdatePlan(unittest.TestCase):
    def test_three_fresh_processes_fixed_updates_reference_and_packet_conservation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);config=root/'config.json';config.write_text(json.dumps({'owned_test':True,'revisions':2,'authorized_reference':None}))
            rows=run(config,root/'plan');packets=[]
            for row in rows:
                folder=root/'plan'/row['name'];before={p.relative_to(folder).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.rglob('*') if p.is_file()}
                result=audit(folder);self.assertEqual(result['verified_queries'],16);self.assertEqual(result['original_source_restores'],2)
                self.assertEqual(before,{p.relative_to(folder).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.rglob('*') if p.is_file()})
                packets.append(result['packet_SHAs'])
                body=json.loads((folder/'worker-finally.json').read_bytes());entry=json.loads((folder/'process-entry-finally.json').read_bytes())
                self.assertTrue(body['success'] and entry['success']);self.assertLessEqual(body['full_wall_s'],entry['full_wall_s']);self.assertLessEqual(entry['full_wall_s'],row['parent_full_wall_s'])
            self.assertEqual(packets[0],packets[1]);self.assertEqual(packets[0],packets[2])
            with self.assertRaises(FileExistsError):run(config,root/'plan')
            target=root/'plan'/rows[1]['name']/'query-000.json';obj=json.loads(target.read_bytes());obj['requested_revision']=1;target.write_text(json.dumps(obj))
            with self.assertRaises(ValueError):audit(target.parent)

    def test_parent_denial_leaves_fixed_denominator_and_no_new_worker(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);config=root/'config.json';config.write_text(json.dumps({'owned_test':True,'revisions':2,'authorized_reference':None}))
            count=0
            def guard():
                nonlocal count
                count+=1
                if count==2:raise RuntimeError('Owned stop before child2')
            with self.assertRaises(RuntimeError):run(config,root/'plan',guard=guard)
            final=json.loads((root/'plan/plan-finally.json').read_bytes());self.assertFalse(final['success'])
            self.assertEqual((final['completed_workers'],final['planned_workers'],final['planned_queries']),(1,3,48))
            self.assertEqual(len(list((root/'plan').glob('*/worker.json'))),1)

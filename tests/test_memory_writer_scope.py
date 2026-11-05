import gc,json,tempfile,threading,unittest
from pathlib import Path
from rkv1.memory import Memory
from scripts.writer_scope_fixture import source,sha,ledger
from scripts.run_writer_scope_plan import run
from scripts.audit_writer_scope_plan import audit

class MemoryWriterScopeTests(unittest.TestCase):
    def memory(self,root):
        (root/'source').mkdir();(root/'source'/'corpus.jsonl').write_bytes(source(9,0))
        m=Memory.create(root/'memory');m.add(root/'source');return m

    def test_competing_process_crash_release_and_original_history_audit(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);run(root/'plan')
            external={f'9:{e}':{'bytes':len(source(9,e)),'sha256':sha(source(9,e))} for e in (0,1,2)}
            v=audit(root/'plan',root/'audit',external)
            self.assertEqual(v['queries_verified'],18);self.assertEqual(v['actual_A_terminations'],2)
            self.assertEqual(len(v['corrupt_controls']),9);self.assertTrue(v['lock_release_not_operation_completion'])

    def test_lifecycle_thread_owner_noninherit_and_failed_add_keeps_scope(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);m=self.memory(root);view=m.writer();info=view.info();self.assertFalse(info['handle_inheritable'])
            info['closed']=True;self.assertFalse(view.closed)
            with self.assertRaises(BlockingIOError):Memory(m.root).writer()
            denied=[]
            def other_thread():
                for op in (lambda:view.add(root/'source'),view.close,view.__enter__):
                    try:op()
                    except ValueError:denied.append(True)
            t=threading.Thread(target=other_thread);t.start();t.join();self.assertEqual(len(denied),3)
            before=ledger(m.root,held=True)
            with self.assertRaises((FileNotFoundError,ValueError)):view.add(root/'missing')
            self.assertEqual(ledger(m.root,held=True),before)
            with self.assertRaises(BlockingIOError):m.writer()
            with view:
                with self.assertRaisesRegex(ValueError,'Nested'):view.__enter__()
            self.assertTrue(view.closed);view.close()
            for op in (lambda:view.add(root/'source'),view.__enter__):
                with self.assertRaisesRegex(ValueError,'closed'):op()
            with m.writer() as fresh:self.assertFalse(fresh.closed)
            self.assertEqual(len(m.search('RKV99PROBE',top_k=8)['hits']),4)

    def test_lock_file_is_not_ownership_metadata_and_finalizer_releases(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);m=self.memory(root);p=m.root/'.writer.lock';raw=b'untrusted old metadata is not a live owner';p.write_bytes(raw)
            scope=m.writer()
            with self.assertRaises(BlockingIOError):m.writer()
            del scope;gc.collect()
            with m.writer():pass
            self.assertEqual(p.read_bytes(),raw)
            # No forced unlink/recreate is needed for a retained pathname.
            with m.writer():pass
            self.assertEqual(p.read_bytes(),raw)

    def test_invalid_lock_path_fixture_anchor_and_plan_input_refuse(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);m=self.memory(root);(m.root/'.writer.lock').mkdir()
            with self.assertRaises(ValueError):m.writer()
            for n in (False,8,1024):
                with self.assertRaises(ValueError):run(root/'not-created',n)
            self.assertFalse((root/'not-created').exists())
            fake=root/'fake';fake.mkdir();(fake/'summary.json').write_text(json.dumps({'size':9,'rows':[{'phase':p} for p in ('before_HEAD','after_HEAD','clean_close')]}))
            (fake/'before_HEAD'/'originals').mkdir(parents=True);raw=source(9,0);(fake/'before_HEAD'/'originals'/'0.jsonl').write_bytes(raw)
            with self.assertRaisesRegex(ValueError,'External source'):audit(fake,root/'audit',{'9:0':{'bytes':len(raw),'sha256':'0'*64}})

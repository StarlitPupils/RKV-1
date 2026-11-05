import copy,json,tempfile,unittest
from pathlib import Path
from rkv1.memory import Memory
from scripts.read_view_fixture import source,sha
from scripts.run_read_view_plan import run
from scripts.audit_read_view_plan import audit,verify

class MemoryReadViewTests(unittest.TestCase):
    def test_three_readers_overlapping_writer_and_independent_original_audit(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);run(root/'plan')
            external={f'9:{e}':{'bytes':len(source(9,e)),'sha256':sha(source(9,e))} for e in (0,1,2)}
            result=audit(root/'plan',root/'audit',external)
            self.assertEqual(result['saved_operations_verified'],33)
            self.assertEqual(len(result['overlap_intervals']),6)
            self.assertEqual(len(result['corruption_controls']),4)
            self.assertTrue(result['pinned_equals_unchanged_explicit_SID'])

    def test_failed_reader_retains_denominator_and_does_not_advance_writer(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)/'plan'
            with self.assertRaisesRegex(RuntimeError,'failed'):run(root,failure_role='pinned')
            footer=json.loads((root/'plan-finally.json').read_bytes())
            self.assertFalse(footer['success']);self.assertEqual(footer['planned_operations'],33)
            self.assertFalse((root/'WRITE-1').exists());self.assertFalse((root/'summary.json').exists())
            with self.assertRaises(FileExistsError):run(root)

    def test_pin_identity_strict_inputs_context_close_and_same_memory_usable(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/'source').mkdir();(root/'source'/'corpus.jsonl').write_bytes(source(9,0))
            m=Memory.create(root/'memory');sid=m.add(root/'source')['snapshot_id']
            for wrong in (False,0,'', 'bad',[],{}):
                with self.assertRaises(ValueError):m.pin(snapshot=wrong)
            with self.assertRaises(FileNotFoundError):m.pin(snapshot='0'*64)
            with m.pin(snapshot=sid) as v:
                self.assertEqual(v.snapshot_id,sid)
                info=v.info();info['snapshot_id']='0'*64;self.assertEqual(v.snapshot_id,sid)
                with self.assertRaises(AttributeError):v.snapshot_id='0'*64
                self.assertEqual(v.search('RKV98PROBE')['snapshot_id'],sid)
            self.assertTrue(v.closed);v.close()
            for f in (lambda:v.search('RKV98PROBE'),lambda:v.lookup('doc:0'),lambda:v.lookup_many(['doc:0']),v.__enter__):
                with self.assertRaisesRegex(ValueError,'closed'):f()
            self.assertEqual(m.search('RKV98PROBE')['snapshot_id'],sid)

    def test_independent_original_boundary_duplicate_and_literal_tamper_refused(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/'source').mkdir();raw=source(9,0);(root/'source'/'corpus.jsonl').write_bytes(raw)
            m=Memory.create(root/'memory');sid=m.add(root/'source')['snapshot_id'];r=m.search('RKV98PROBE',top_k=8)
            for kind in ('literal','offset','duplicate'):
                bad=copy.deepcopy(r)
                if kind=='literal':bad['hits'][0]['sentences'][0]='changed'
                elif kind=='offset':bad['hits'][0]['locator']['offset']=False
                else:bad['hits'].append(bad['hits'][0])
                with self.assertRaises(ValueError):verify(m,bad,raw,sid,'search')
            fake=root/'fake';fake.mkdir();(fake/'summary.json').write_text(json.dumps({'size':9,'old_sid':sid}));(fake/'originals').mkdir();(fake/'originals'/'0.jsonl').write_bytes(raw)
            # Bind the untouched original Memory so wrong fixture refusal is reached.
            import shutil
            shutil.copytree(root/'memory',fake/'memory')
            with self.assertRaisesRegex(ValueError,'External source'):audit(fake,root/'audit',{'9:0':{'bytes':len(raw),'sha256':'0'*64}})

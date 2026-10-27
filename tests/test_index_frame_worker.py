import json,subprocess,sys,tempfile,unittest
from pathlib import Path
from collections import Counter
from rkv1.core import digest
from scripts.index_frame import decode
from scripts.index_frame_fixture import control
from scripts.postings_transform import canonical

class IndexFrameWorkerTests(unittest.TestCase):
    def test_pack_unpack_CLI_exclusive_output_and_original_preserved(self):
        source=canonical({'shared':{'doc_lengths':{'p':1},'postings':{'alpha':{'p':1}}}})
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);src=root/'model.json';src.write_bytes(source);frame=root/'model.rkvpost';restored=root/'restored.json'
            pack=[sys.executable,'-m','scripts.index_frame','pack',str(src),str(frame),'--method','typed','--codec','zstd']
            result=subprocess.run(pack,capture_output=True,text=True);self.assertEqual(result.returncode,0,result.stderr);before=frame.read_bytes()
            result=subprocess.run([sys.executable,'-m','scripts.index_frame','unpack',str(frame),str(restored)],capture_output=True,text=True);self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(restored.read_bytes(),source)
            result=subprocess.run(pack,capture_output=True,text=True);self.assertNotEqual(result.returncode,0);self.assertEqual(frame.read_bytes(),before);self.assertEqual(src.read_bytes(),source)
    def test_owned_random_posting_control_deterministic_and_semantic_counts(self):
        raw=control();self.assertEqual(raw,control());obj=json.loads(raw);shared=obj['shared'];totals=Counter()
        for posting in shared['postings'].values():self.assertEqual(len(posting),8);totals.update(posting)
        self.assertEqual(dict(totals),shared['doc_lengths']);self.assertEqual(shared['N'],256);self.assertEqual(len(shared['postings']),1024)
    def test_eight_real_workers_persisted_frame_model_ready_and_bad_SHA_refusal(self):
        source=canonical({'shared':{'doc_lengths':{'p1':3,'p2':1},'postings':{'alpha':{'p1':2,'p2':1},'beta':{'p1':1}}},'other':['Unicode β',1.25,None]})
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);path=root/'source.json';path.write_bytes(source);manifest={'datasets':{'toy':{'path':str(path),'sha256':digest(source),'bytes':len(source),'role':'owned_fixture'}}}
            (root/'manifest.json').write_bytes(canonical(manifest))
            for method in ('plain','typed'):
                for codec in ('raw','zlib','zstd','lzma'):
                    label=method+'-'+codec;work=root/label;report=root/(label+'.json');args=[sys.executable,'-m','scripts.run_index_frames','--manifest',str(root/'manifest.json'),'--work',str(work),'--round','1','--dataset','toy','--method',method,'--codec',codec,'--worker-report',str(report)]
                    result=subprocess.run(args,capture_output=True,text=True);self.assertEqual(result.returncode,0,result.stderr);r=json.loads(report.read_bytes())
                    self.assertTrue(r['exact_original_bytes_and_model_ready']);self.assertEqual((work/'restored-index.json').read_bytes(),source)
                    self.assertEqual(decode((work/'index.rkvpost').read_bytes()),source);self.assertEqual(r['restored_sha256'],digest(source));self.assertEqual(r['semantic_index_documents'],2)
                    self.assertEqual(r['frame_write']['fsyncs'],1);self.assertEqual(r['restored_write']['fsyncs'],1)
                    self.assertGreaterEqual(r['decode_to_model_ready_wall_s'],r['decode_wall_s'])
            path.write_bytes(source+b' ');args[args.index('--work')+1]=str(root/'bad-work');args[args.index('--worker-report')+1]=str(root/'bad-result.json')
            result=subprocess.run(args,capture_output=True,text=True);self.assertNotEqual(result.returncode,0);self.assertFalse((root/'bad-result.json').exists())

if __name__=='__main__':unittest.main()

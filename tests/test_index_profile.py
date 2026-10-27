import json,subprocess,sys,tempfile,unittest
from pathlib import Path
from rkv1.core import digest
from scripts.index_frame import encode
from scripts.postings_transform import canonical
from scripts.run_index_profile import load

class IndexProfileTests(unittest.TestCase):
    def source(self):return canonical({'shared':{'doc_lengths':{'a':3,'β':1},'postings':{'alpha':{'a':2,'β':1},'beta':{'a':1}}},'opaque':[None,True,1.25]})
    def test_off_preserves_bytes_and_null_counters(self):
        raw=self.source();frame,_=encode(raw,codec='lzma');restored,model,r=load(frame)
        self.assertEqual(restored,raw);self.assertEqual(canonical(model),raw);self.assertIsNone(r['functions']);self.assertIsNone(r['profiler_total_self_s']);self.assertGreater(r['model_ready_wall_s'],0)
        with self.assertRaises(ValueError):load(frame,1)
    def test_on_exact_varint_calls_and_self_time_conservation(self):
        raw=self.source();frame,_=encode(raw,codec='lzma');restored,model,r=load(frame,True)
        self.assertEqual(restored,raw);v=[x for x in r['functions'] if x['function']=='read_uvar' and x['file']=='scripts/postings_transform.py'];self.assertEqual(len(v),1);self.assertEqual(v[0]['calls'],4+2*2+2*3)
        self.assertAlmostEqual(sum(x['instrumented_self_s'] for x in r['functions']),r['profiler_total_self_s']);self.assertEqual(canonical(model),raw)
    def test_error_disables_observer_and_both_reject_corruption(self):
        frame,_=encode(self.source(),codec='lzma');broken=frame[:-1]+bytes([frame[-1]^1])
        for on in (False,True):
            with self.assertRaises(ValueError):load(broken,on)
            self.assertIsNone(sys.getprofile())
    def test_fresh_worker_switches_identity_and_frozen_input_refusal(self):
        raw=self.source();frame,_=encode(raw,codec='lzma')
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);src=root/'model.json';src.write_bytes(raw);fr=root/'input.rkvpost';fr.write_bytes(frame);entry={'path':str(src),'bytes':len(raw),'sha256':digest(raw),'frame_path':str(fr),'frame_bytes':len(frame),'frame_sha256':digest(frame),'role':'owned_fixture'};manifest=root/'manifest.json';manifest.write_bytes(canonical({'datasets':{'toy':entry}}))
            for mode in ('off','on'):
                report=root/(mode+'.json');args=[sys.executable,'-m','scripts.run_index_profile','--manifest',str(manifest),'--round','1','--dataset','toy','--profiler',mode,'--worker-report',str(report)]
                result=subprocess.run(args,capture_output=True,text=True);self.assertEqual(result.returncode,0,result.stderr);r=json.loads(report.read_bytes());self.assertEqual(r['restored_sha256'],digest(raw));self.assertEqual(r['posting_pairs'],3);self.assertEqual(r['functions'] is None,mode=='off')
            src.write_bytes(raw+b' ');args[args.index('--worker-report')+1]=str(root/'bad.json');result=subprocess.run(args,capture_output=True,text=True);self.assertNotEqual(result.returncode,0);self.assertFalse((root/'bad.json').exists())

if __name__=='__main__':unittest.main()

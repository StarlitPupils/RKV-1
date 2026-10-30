import copy,json,tempfile,unittest
from pathlib import Path
from rkv1.store import Store
from scripts.sentence_spans import digest
from scripts.source_evidence_views import build_view,verify_view
from scripts.audit_evidence_view_packet import check
from scripts.view_admission import canonical


class OwnedViewIntegration(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);root=Path(temp.name)
        src=root/'source';src.mkdir()
        rows=[json.dumps({'doc_id':i,'abstract':['unrelated','alpha','alpha beta','same']},separators=(',',':')).encode()+b'\r\n' for i in range(3)]
        self.source=b''.join(rows);(src/'corpus.jsonl').write_bytes(self.source)
        self.store=Store.create(root/'store',compression='zlib',chunk_size=65536,io_backend='bounded');sid=self.store.add(src)['snapshot_id']
        self.records=[];offset=0
        for i,raw in enumerate(rows):
            self.records.append({'id':'doc:'+str(i),'binding':{'snapshot_id':sid,'path':'corpus.jsonl','source_sha256':digest(self.source),
                'record_offset':offset,'record_length':len(raw),'record_sha256':digest(raw),'field':'abstract'}});offset+=len(raw)

    def test_three_arms_have_independent_exact_bytes_and_source_choices(self):
        for method in ('whole_record','first_two','overlap_two'):
            result=build_view(self.store.root,'alpha beta',self.records,method=method)
            encoded=bytes.fromhex(result['encoded_hex'])
            ref=check(self.source,'alpha beta',self.records,method,encoded,20000)
            actual=verify_view(self.store.root,encoded,'alpha beta',self.records,method=method)
            self.assertEqual(ref,actual['available_original_sentence_indices'])
            self.assertEqual(result['preparation_record_return_B'],len(self.source))

    def test_exact_cap_and_rejected_preparation_reads_still_count(self):
        result=build_view(self.store.root,'alpha beta',self.records,method='overlap_two')
        cap=result['encoded_B']
        self.assertEqual(build_view(self.store.root,'alpha beta',self.records,method='overlap_two',byte_cap=cap)['encoded_B'],cap)
        low=build_view(self.store.root,'alpha beta',self.records,method='overlap_two',byte_cap=cap-1)
        check(self.source,'alpha beta',self.records,'overlap_two',bytes.fromhex(low['encoded_hex']),cap-1)
        self.assertLess(len(low['packet']['items']),3)
        self.assertEqual(low['preparation_record_return_B'],len(self.source))

    def test_wrong_source_index_transport_and_noncanonical_refuse(self):
        result=build_view(self.store.root,'alpha beta',self.records,method='overlap_two')
        for kind in ('token','index','header','duplicate'):
            packet=copy.deepcopy(result['packet'])
            if kind=='token':packet['items'][0]['original_token_hex'][0]='00'
            elif kind=='index':packet['items'][0]['witness']['sentences'][0]['sentence_index']=0
            elif kind=='header':packet['header']['source_sha256']='0'*64
            else:packet['items'].append(packet['items'][0])
            with self.assertRaises(ValueError):verify_view(self.store.root,canonical(packet),'alpha beta',self.records,method='overlap_two')
        with self.assertRaises(ValueError):verify_view(self.store.root,bytes.fromhex(result['encoded_hex'])+b' ','alpha beta',self.records,method='overlap_two')

    def test_invalid_preparation_bounds_duplicate_oracles_refuse(self):
        with self.assertRaises(ValueError):build_view(self.store.root,'alpha beta',self.records,method='oracle')
        with self.assertRaises(ValueError):build_view(self.store.root,'alpha beta',self.records,method='first_two',byte_cap=True)
        with self.assertRaises(ValueError):build_view(self.store.root,'alpha beta',[self.records[0]]*2,method='first_two')
        with self.assertRaises(TypeError):build_view(self.store.root,'alpha beta',self.records,method='first_two',gold=[0])

    def test_no_candidates_retains_explicit_anchor_and_empty_view(self):
        b=self.records[0]['binding'];anchor={k:b[k] for k in ('snapshot_id','path','source_sha256')}
        for method in ('whole_record','first_two','overlap_two'):
            result=build_view(self.store.root,'no matching candidates',[],method=method,source_header=anchor)
            self.assertEqual(result['packet']['items'],[])
            self.assertEqual(result['preparation_record_return_B'],0)
            self.assertEqual(verify_view(self.store.root,bytes.fromhex(result['encoded_hex']),'no matching candidates',[],method=method,source_header=anchor)['available_original_sentence_indices'],{})
        with self.assertRaises(ValueError):build_view(self.store.root,'alpha',[],method='whole_record')

    def test_bool_metadata_cannot_impersonate_original_integer_zero(self):
        for method in ('whole_record','first_two'):
            result=build_view(self.store.root,'alpha',self.records,method=method)
            bad=copy.deepcopy(result['packet'])
            if method=='whole_record':bad['items'][0]['binding']['record_offset']=False
            else:bad['items'][0]['witness']['sentences'][0]['sentence_index']=False
            with self.assertRaises(ValueError):verify_view(self.store.root,canonical(bad),'alpha',self.records,method=method)


if __name__=='__main__':unittest.main()

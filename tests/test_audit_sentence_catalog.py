import copy,json,unittest
from scripts.scifact_graph import build_model
from scripts.sentence_index import build_index
from scripts.audit_sentence_catalog import audit_catalog

class IndependentSentenceCatalogTests(unittest.TestCase):
    def test_duplicate_text_title_and_neighbor_offset_cannot_impersonate_sentence(self):
        obj={'doc_id':1,'title':'same β','abstract':['same β','same β']};raw=(json.dumps(obj,ensure_ascii=False)+'\r\n').encode();paper,_=build_model(raw,[]);index,_=build_index(raw,paper)
        corpus={'doc:1':{'object':obj,'raw':raw,'offset':0}};self.assertEqual(audit_catalog(corpus,index)['independent_catalog_raw_unit_bindings'],2)
        bad=copy.deepcopy(index);bad['shared']['locators']['doc:1:abstract:1']['offset']=bad['shared']['locators']['doc:1:abstract:0']['offset']
        with self.assertRaises(AssertionError):audit_catalog(corpus,bad)
        bad=copy.deepcopy(index);bad['shared']['locators']['doc:1:abstract:0']['offset']=raw.index(json.dumps('same β',ensure_ascii=False).encode())
        with self.assertRaises(AssertionError):audit_catalog(corpus,bad)
        bad=copy.deepcopy(index);bad['shared']['postings']['same']['doc:1:abstract:0']=99
        with self.assertRaises(AssertionError):audit_catalog(corpus,bad)

if __name__=='__main__':unittest.main()

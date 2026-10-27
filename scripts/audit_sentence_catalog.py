"""Independent original-member decoder audit, separate from span constructor."""
from collections import Counter,defaultdict
import json
from rkv1.core import digest
from rkv1.memory_qasper import members
from scripts.evidence_retrieval import tokens

def audit_catalog(corpus,index):
    expected={};postings=defaultdict(dict);lengths={};decoder=json.JSONDecoder()
    for paper,record in corpus.items():
        obj=record['object'];parent=index['parents'][paper]
        assert parent['offset']==record['offset'] and parent['length']==len(record['raw']) and parent['sha256']==digest(record['raw'])
        assert parent['sentence_count']==len(obj['abstract']) and parent['title_sha256']==digest(obj['title'].encode('utf-8'))
        found=False
        for key,value,member_offset,original in members(record['raw']):
            if key!='abstract':continue
            assert not found and value==obj['abstract'];found=True;text=original.decode('utf-8');_,at=decoder.raw_decode(text)
            while text[at] in ' \t\r\n':at+=1
            assert text[at]==':';at+=1
            while text[at] in ' \t\r\n':at+=1
            assert text[at]=='[';at+=1
            for i,sentence in enumerate(obj['abstract']):
                while text[at] in ' \t\r\n':at+=1
                begin=at;decoded,end=decoder.raw_decode(text,at);assert decoded==sentence
                a=member_offset+len(text[:begin].encode('utf-8'));b=member_offset+len(text[:end].encode('utf-8'));raw=record['raw'][a:b]
                unit_id=paper+':abstract:'+str(i);expected[unit_id]={'paper_id':paper,'sentence_index':i,'offset':record['offset']+a,'length':b-a,'sha256':digest(raw),'decoded_text_sha256':digest(sentence.encode('utf-8'))}
                tf=Counter(tokens(sentence));lengths[unit_id]=sum(tf.values())
                for token,n in tf.items():postings[token][unit_id]=n
                at=end
                while text[at] in ' \t\r\n':at+=1
                if i+1<len(obj['abstract']):assert text[at]==',';at+=1
            while text[at] in ' \t\r\n':at+=1
            assert text[at]==']'
        assert found
    shared=index['shared'];assert shared['locators']==expected and shared['doc_lengths']==lengths and shared['postings']==dict(postings)
    assert set(index['parents'])==set(corpus) and shared['N']==len(expected) and shared['avgdl']==sum(lengths.values())/len(expected)
    return {'independent_catalog_raw_unit_bindings':len(expected),'source_parents':len(corpus),'token_occurrences':sum(lengths.values()),'all_original_structural_offsets_and_postings_equal':True}

import json,unittest
from scripts.source_string_spans import abstract_units
from rkv1.core import digest

class SourceStringSpansTests(unittest.TestCase):
    def test_original_escaped_unicode_repeated_string_spans(self):
        obj={'doc_id':7,'title':'same repeated','abstract':['same repeated','same repeated','quote " and slash \\ and newline\n','β汉字😀']}
        for ascii_only in (False,True):
            raw=(' \t'+json.dumps(obj,ensure_ascii=ascii_only)+'\r\n').encode('utf-8');units=abstract_units(raw,parent_offset=91)
            self.assertEqual(len(units),4);self.assertNotEqual(units[0]['offset'],units[1]['offset'])
            for i,unit in enumerate(units):
                original=raw[unit['offset']-91:unit['offset']-91+unit['length']]
                self.assertEqual(json.loads(original),obj['abstract'][i]);self.assertEqual(digest(original),unit['sha256'])
                self.assertEqual(unit['parent_sha256'],digest(raw));self.assertEqual(unit['sentence_index'],i)
    def test_member_order_nested_extras_empty_and_spacing(self):
        raw=b'{"extra":{"abstract":["decoy"]}, "abstract" : [ "real one" , "real two" ],"title":"real one","doc_id":2}\n'
        self.assertEqual([r['text'] for r in abstract_units(raw)],['real one','real two'])
        self.assertEqual(abstract_units(b'{"doc_id":2,"title":"empty","abstract":[]}'),[])
    def test_duplicate_bad_schema_invalid_JSON_range_and_UTF8_refuse(self):
        bad=(b'{"doc_id":1,"title":"x","abstract":[],"abstract":["wrong"]}',
            b'{"doc_id":true,"title":"x","abstract":[]}',b'{"doc_id":1,"title":"x","abstract":[2]}',
            b'{"doc_id":1,"title":"x","abstract":["x",]}',b'{"doc_id":1,"title":"x","abstract":[],"value":NaN}',
            b'{"doc_id":1,"title":"x","abstract":[]} trailing',b'\xff')
        for raw in bad:
            with self.assertRaises((ValueError,UnicodeError)):abstract_units(raw)
        with self.assertRaises(ValueError):abstract_units(b'{}',parent_offset=True)

if __name__=='__main__':unittest.main()

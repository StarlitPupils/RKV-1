import copy
import json
from pathlib import Path
import tempfile
import unittest
from rkv1.store import Store
from scripts.sentence_spans import digest, locate
from scripts.store_sentence_spans import make_witness, recover_witness


class OwnedStoreBinding(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.source = self.root/'source'
        self.source.mkdir()
        self.record = json.dumps({'doc_id': 2, 'title': '\u539f\u6587', 'abstract': ['same', 'same', 'escaped " \u03b1']}, ensure_ascii=False).encode() + b'\r\n'
        self.prefix = b'{"doc_id":1,"abstract":["decoy"]}\r\n'
        self.raw = self.prefix + self.record
        (self.source/'corpus.jsonl').write_bytes(self.raw)
        self.store = Store.create(self.root/'store', compression='zlib', chunk_size=65536, io_backend='bounded')
        self.sid = self.store.add(self.source)['snapshot_id']
        self.binding = {'snapshot_id': self.sid, 'path': 'corpus.jsonl', 'source_sha256': digest(self.raw), 'record_offset': len(self.prefix), 'record_length': len(self.record), 'record_sha256': digest(self.record), 'field': 'abstract'}

    def test_explicit_actual_abstract_field_and_original_source_bytes(self):
        with self.assertRaises(ValueError):
            locate(self.record)  # No silent abstract->sentences fallback.
        witness = make_witness(self.store.root, self.binding, [1, 2])
        tokens = recover_witness(self.store.root, witness, expected_binding=self.binding)
        for row, token in zip(witness['sentences'], tokens):
            self.assertEqual(token, self.record[row['offset']:row['offset']+row['length']])
        self.assertEqual([json.loads(t) for t in tokens], ['same', 'escaped " \u03b1'])
        self.assertEqual(witness['application_record_return_B'], len(self.record))

    def test_new_head_does_not_rebind_old_witness(self):
        witness = make_witness(self.store.root, self.binding, [0])
        (self.source/'corpus.jsonl').write_bytes(self.raw.replace(b'same', b'else'))
        new_sid = self.store.add(self.source)['snapshot_id']
        self.assertNotEqual(new_sid, self.sid)
        self.assertEqual(json.loads(recover_witness(self.store.root, witness, expected_binding=self.binding)[0]), 'same')
        altered = copy.deepcopy(witness)
        altered['binding']['snapshot_id'] = new_sid
        with self.assertRaises(ValueError):
            recover_witness(self.store.root, altered, expected_binding=self.binding)

    def test_source_record_field_count_and_sentence_corruption_refuse(self):
        witness = make_witness(self.store.root, self.binding, [0])
        for key, value in [('source_sha256', '0'*64), ('record_sha256', '0'*64), ('record_offset', True), ('record_length', len(self.raw)+1), ('field', 'sentences')]:
            bad = dict(self.binding)
            bad[key] = value
            with self.assertRaises(ValueError):
                make_witness(self.store.root, bad, [0])
        for change in ('duplicate', 'count', 'position'):
            bad = copy.deepcopy(witness)
            if change == 'duplicate':
                bad['sentences'] *= 2
            elif change == 'count':
                bad['application_record_return_B'] += 1
            else:
                bad['sentences'][0]['sentence_index'] = 1
            with self.assertRaises(ValueError):
                recover_witness(self.store.root, bad, expected_binding=self.binding)

    def test_original_cas_corruption_not_bypassed(self):
        witness = make_witness(self.store.root, self.binding, [0])
        with self.store.snapshot(self.sid) as snapshot:
            chunk = snapshot.files['corpus.jsonl']['chunks'][0]
        target = self.store.object_path(chunk['id'])
        damaged = bytearray(target.read_bytes())
        damaged[-1] ^= 1
        target.write_bytes(damaged)
        with self.assertRaises(ValueError):
            recover_witness(self.store.root, witness, expected_binding=self.binding)


if __name__ == '__main__':
    unittest.main()

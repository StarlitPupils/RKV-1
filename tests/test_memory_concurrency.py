import copy
from pathlib import Path
import tempfile
import unittest

from rkv1.core import digest
from rkv1.memory import Memory
from scripts.run_memory_concurrency import audit, corpus


class ConcurrencyAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        root=Path(self.temp.name);source=root/'source';source.mkdir()
        self.raw=corpus(0);(source/'corpus.jsonl').write_bytes(self.raw)
        self.memory=Memory.create(root/'memory');self.sid=self.memory.add(source)['snapshot_id']
        self.result=self.memory.search('RKV33EPOCH',top_k=20);self.hashes={digest(self.raw):0}

    def test_valid_audit_binds_all_four_original_records_and_rejects_projection_or_locator_damage(self):
        self.assertEqual(audit(self.memory,self.result,self.hashes,self.sid)['verified_records'],4)
        for mutate in (lambda r:r['hits'][0]['sentences'].__setitem__(0,'RKV33EPOCH epoch 0001 sentinel 0.'),
                       lambda r:r['hits'][0]['locator'].__setitem__('snapshot_id','0'*64),
                       lambda r:r['hits'][0]['locator'].__setitem__('offset',1),
                       lambda r:r['hits'].pop()):
            damaged=copy.deepcopy(self.result);mutate(damaged)
            with self.assertRaises(AssertionError):audit(self.memory,damaged,self.hashes,self.sid)

    def test_full_source_identity_and_retained_epoch_are_independently_required(self):
        with self.assertRaises(KeyError):audit(self.memory,self.result,{'0'*64:0})
        with self.assertRaisesRegex(AssertionError,'Retained epoch'):
            audit(self.memory,self.result,{digest(self.raw):1},self.sid)
        with self.assertRaisesRegex(AssertionError,'Retained SID'):
            audit(self.memory,self.result,self.hashes,'0'*64)


if __name__=='__main__':unittest.main()

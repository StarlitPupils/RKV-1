import copy
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from rkv1.memory import Memory,_json
from rkv1.memory_index import load_delta
from rkv1.memory_projection import view
from test_memory_projection import paper


class ProjectionQueryTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);self.root=Path(temp.name)
        self.source=self.root/'source';self.source.mkdir();self.path=self.source/'qasper.json'
        self.docs={str(i):paper(i) for i in range(300)};self.write()
        self.mem=Memory.create(self.root/'mem',index_profile='compact-projection-v4')
        self.full=Memory.create(self.root/'full',index_profile='compact-full-v2')
        self.first=self.add('initial')['snapshot_id']

    def write(self):self.path.write_bytes(_json(self.docs))

    def add(self,label):
        self.full.add(self.source,label=label);return self.mem.add(self.source,label=label)

    def compare(self):
        for q in ('silver','token000','token001','token299','TRUEEDITQ22','unfindableq22'):
            self.assertEqual(self.mem.search(q,top_k=20)['hits'],self.full.search(q,top_k=20)['hits'])

    def test_metadata_only_uses_base_readonly_checks_all_rows_and_batches(self):
        for d in self.docs.values():d['qas'].append({'question':'changed annotation and offset'})
        self.write();result=self.add('metadata');self.assertEqual(result['overlay_rebindings'],300)
        manifest=self.mem._manifest(self.mem.current());sql=[];connect=sqlite3.connect
        def traced(*args,**kwargs):
            db=connect(*args,**kwargs);db.set_trace_callback(sql.append);return db
        with patch('rkv1.memory_projection.sqlite3.connect',side_effect=traced):
            with view(self.mem,manifest,deferred=True) as (db,(_,_,bindings)):
                self.assertEqual(len(bindings),300)
                self.assertEqual(Path(db.execute('PRAGMA database_list').fetchone()[2]).resolve(),(self.mem.root/'indexes'/(manifest['base_snapshot_id']+'.sqlite')).resolve())
        self.assertFalse(any(s.lstrip().upper().startswith(('UPDATE','INSERT','DELETE','BEGIN')) for s in sql))
        self.assertEqual(sum('WHERE l.key IN (' in s for s in sql),2)
        self.compare()

    def test_nonhit_corruption_absent_key_duplicate_and_operation_overlap_rejected(self):
        for d in self.docs.values():d['qas'].append({'question':'changed'})
        self.write();self.add('annotations');v=self.mem._manifest(self.mem.current());delta=load_delta(self.mem,v['deltas'][0])
        bads=[]
        bad=copy.deepcopy(delta);bad['rebound'][-1][1]='0'*64;bads.append(bad)
        bad=copy.deepcopy(delta);bad['rebound'][-1][0][0]='qasper:absent';bads.append(bad)
        bad=copy.deepcopy(delta);bad['rebound'].append(bad['rebound'][0]);bads.append(bad)
        bad=copy.deepcopy(delta);bad['removed'].append(bad['rebound'][0][0][0]);bads.append(bad)
        for bad in bads:
            with self.subTest(case=len(bad['rebound'])):
                with patch('rkv1.memory_index.load_delta',return_value=bad):
                    with self.assertRaisesRegex(ValueError,'fingerprint|Overlapping'):self.mem.search('unfindableq22')

    def test_mixed_FTS_and_rebinding_and_moves_keep_copy_and_current_offsets(self):
        self.docs['0']['qas'].append({'question':'annotation grows and moves following unchanged members'*3})
        self.docs['299']['title']+=' TRUEEDITQ22';self.write();result=self.add('mixed')
        self.assertEqual(result['overlay_upserts'],1);self.assertEqual(result['overlay_rebindings'],1);self.assertGreater(result['relocation_ranges'],0)
        manifest=self.mem._manifest(self.mem.current())
        with view(self.mem,manifest,deferred=True) as (db,(_,_,bindings)):
            self.assertEqual(db.execute('PRAGMA database_list').fetchone()[2],'');self.assertEqual(set(bindings),{'qasper:0'})
        self.compare();self.assertFalse(self.mem.search('TRUEEDITQ22',snapshot=self.first)['hits'])

    def test_forced_copy_ablation_and_materialized_writer_view_match_lazy(self):
        self.docs['0']['qas'].append({'question':'metadata growth'});self.write();self.add('metadata')
        manifest=self.mem._manifest(self.mem.current())
        with view(self.mem,manifest) as db:material={r[0]:r[1:] for r in db.execute('SELECT key,path,offset,length,lower(hex(sha)),kind FROM locators')}
        with view(self.mem,manifest,deferred=True,copy_base=True) as (db,(ranges,updated,bindings)):
            self.assertEqual(db.execute('PRAGMA database_list').fetchone()[2],'')
            from rkv1.memory_index import moved
            for row in db.execute('SELECT key,path,offset,length,lower(hex(sha)),kind FROM locators'):
                projected=bindings.get(row[0],row if row[0] in updated else moved(row,ranges))
                self.assertEqual(tuple(projected[1:]),material[row[0]])
        self.compare()


if __name__=='__main__':unittest.main()

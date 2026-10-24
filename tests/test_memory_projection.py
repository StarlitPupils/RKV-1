import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from rkv1.core import digest
from rkv1.memory import Memory,_json,records
from rkv1.memory_index import load_delta
from rkv1.memory_projection import replay,view


def paper(i):
    return {'title':f'Silver calibration {i}', 'abstract':f'Neutrino token{i:03d} 雪.',
            'full_text':[{'section_name':'ignored heading','paragraphs':['Rare variants confirm beacon.']}],
            'qas':[{'question':'ANNOTATIONONLYQ21','answers':[{'answer':'PRIVATEANSWERQ21'}]}]}


class ProjectionMemoryTests(unittest.TestCase):
    def test_annotations_renames_reorder_unicode_and_true_edits_keep_exact_identity(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);source=root/'source';source.mkdir();path=source/'qasper-v1.json'
            docs={str(i):paper(i) for i in range(20)}
            full=Memory.create(root/'full',index_profile='compact-full-v2')
            mem=Memory.create(root/'v4',index_profile='compact-projection-v4');first=None
            for stage in range(6):
                if stage==1:
                    for d in docs.values():d['qas'][0]['question']+=' annotation resized';d['full_text'][0]['section_name']='Changed ignored heading'
                if stage==2:path.rename(source/'qasper-v2.json');path=source/'qasper-v2.json';docs=dict(reversed(list(docs.items())))
                if stage==3:docs['0']['full_text'][0]['paragraphs'][0]+=' FUTURETEXTQ21'
                if stage==4:del docs['1'];docs['new']=paper(99)
                if stage==5:docs['0']['full_text'][0]['paragraphs'][0]='Rare variants confirm beacon.'
                path.write_text(json.dumps(docs,ensure_ascii=stage%2==0,indent=stage%3+1),encoding='utf-8')
                a=full.add(source,label=str(stage));b=mem.add(source,label=str(stage));self.assertEqual(a['snapshot_id'],b['snapshot_id'])
                if first is None:first=b['snapshot_id']
                else:self.assertEqual(b['delta_depth'],1)
                if stage in (1,2):self.assertEqual(b['overlay_rebindings'],20);self.assertEqual(b['overlay_upserts'],0);self.assertEqual(b['replay_budget']['cas_bytes'],0)
                for q in ('calibration','rare variants','token000','FUTURETEXTQ21','token099'):
                    self.assertEqual(mem.search(q,top_k=20)['hits'],full.search(q,top_k=20)['hits'])
                self.assertFalse(mem.search('ANNOTATIONONLYQ21')['hits']);self.assertFalse(mem.search('PRIVATEANSWERQ21')['hits'])
                for h in mem.search('calibration',top_k=20)['hits']:
                    loc=h['locator'];raw=path.read_bytes()[loc['offset']:loc['offset']+loc['length']]
                    self.assertEqual(digest(raw),loc['sha256']);self.assertEqual(list(records(path.name,raw))[0][0],h['key'])
            self.assertFalse(mem.search('FUTURETEXTQ21',snapshot=first)['hits'])
            self.assertEqual(mem._manifest(mem.current())['base_snapshot_id'],first)

    def test_rebinding_does_not_parse_or_rewrite_FTS_and_checks_fingerprint(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);source=root/'source';source.mkdir();path=source/'qasper.json';docs={str(i):paper(i) for i in range(8)}
            path.write_bytes(_json(docs));m=Memory.create(root/'mem',index_profile='compact-projection-v4');m.add(source)
            for d in docs.values():d['qas'].append({'question':'another annotation'})
            path.write_bytes(_json(docs));m.add(source,label='annotations');manifest=m._manifest(m.current());delta=load_delta(m,manifest['deltas'][0])
            with patch('rkv1.memory_index.parse_record',side_effect=AssertionError('unexpected FTS replay read')):
                with view(m,manifest) as db:self.assertEqual(db.execute('SELECT count(*) FROM locators').fetchone()[0],8)
            bad=copy.deepcopy(delta);bad['rebound'][0][1]='0'*64
            base=copy.deepcopy(manifest);base['deltas']=[]
            with view(m,base,writable=True) as db:
                with self.assertRaisesRegex(ValueError,'fingerprint'):replay(m,db,bad)
            bad=copy.deepcopy(delta);bad['rebound'].append(bad['rebound'][0])
            with view(m,base,writable=True) as db:
                with self.assertRaisesRegex(ValueError,'Overlapping'):replay(m,db,bad)

    def test_changed_text_cannot_hide_as_rebinding_and_budget_checkpoint_remains(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);source=root/'source';source.mkdir();path=source/'qasper.json';docs={str(i):paper(i) for i in range(160)}
            path.write_bytes(_json(docs));m=Memory.create(root/'mem',index_profile='compact-projection-v4');m.add(source)
            # Same token postings but different paragraph boundaries must have
            # different projection fingerprints and follow ordinary replay.
            docs['0']['full_text'][0]['paragraphs']=['Rare variants','confirm beacon.']
            path.write_bytes(_json(docs));b=m.add(source,label='boundaries')
            self.assertEqual(b['overlay_upserts'],1);self.assertEqual(b['overlay_rebindings'],0)
            for i in range(33):docs[str(i)]['title']+=' ACTUALTEXTQ21'
            path.write_bytes(_json(docs));b=m.add(source,label='33-text-changes')
            self.assertEqual(b['checkpoint_reason'],'budget-changes');self.assertEqual(b['delta_depth'],0)
            self.assertEqual(len(m.search('ACTUALTEXTQ21',top_k=20)['hits']),20)

    def test_rebinding_limit_creates_checkpoint(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);source=root/'source';source.mkdir();path=source/'qasper.json';docs={str(i):paper(i) for i in range(8)}
            path.write_bytes(_json(docs));m=Memory.create(root/'mem',index_profile='compact-projection-v4');m.add(source)
            for d in docs.values():d['qas'].append({'question':'changed'})
            path.write_bytes(_json(docs))
            with patch('rkv1.memory_projection.MAX_REBINDINGS',7):result=m.add(source,label='rebinding-overflow')
            self.assertEqual(result['checkpoint_reason'],'rebinding-limit')

    def test_hit_fingerprint_mismatch_and_overlay_damage_fail(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);source=root/'source';source.mkdir();path=source/'qasper.json';docs={str(i):paper(i) for i in range(8)}
            path.write_bytes(_json(docs));m=Memory.create(root/'mem',index_profile='compact-projection-v4');m.add(source)
            docs['0']['qas'].append({'question':'annotation'});path.write_bytes(_json(docs));m.add(source,label='annotation')
            with patch('rkv1.memory_projection.fingerprint',return_value='0'*64):
                with self.assertRaisesRegex(ValueError,'projection differs'):m.search('token000')
            desc=m._manifest(m.current())['deltas'][0];overlay=m.root/'indexes'/(desc['sha256']+'.delta');raw=overlay.read_bytes();overlay.write_bytes(raw+b'x')
            with self.assertRaisesRegex(ValueError,'delta SHA mismatch'):m.search('token000')

    def test_explicit_profile_validation_and_old_profiles_stay_default(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);m=Memory.create(root/'default');self.assertEqual(json.loads((m.root/'indexes/config.json').read_bytes())['profile'],'compact-budget-v3')
            from rkv1.cli import main
            source=root/'source';source.mkdir();(source/'a.txt').write_text('calibration',encoding='utf-8')
            with patch('builtins.print'):main(['memory-init',str(root/'cli'),str(source),'--index-profile','compact-projection-v4'])
            cli=Memory(root/'cli');head=(cli.root/'HEAD.json').read_bytes();config=cli.root/'indexes/config.json';value=json.loads(config.read_bytes());value['replay_budget']=None;config.write_bytes(_json(value))
            with self.assertRaisesRegex(ValueError,'replay budget'):cli.add(source,label='invalid')
            self.assertEqual((cli.root/'HEAD.json').read_bytes(),head)
            from rkv1.memory_budget import DEFAULT_BUDGET
            value['replay_budget']=DEFAULT_BUDGET.copy();config.write_bytes(_json(value))
            with self.assertRaisesRegex(ValueError,'v3 base profile'):cli.enable_replay_budget()


if __name__=='__main__':unittest.main()

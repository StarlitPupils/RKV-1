import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from rkv1.memory import Memory
from scripts.writer_scope_fixture import ledger, source, verify


class MemoryDefaultWriterTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.library = self.root / 'memory'
        self.original = self.make_source(0)
        self.revision = self.make_source(1)

    def make_source(self, epoch):
        folder = self.root / f'source-{epoch}'
        folder.mkdir()
        (folder / 'corpus.jsonl').write_bytes(source(9, epoch))
        return folder

    def cli(self, command, *args):
        return subprocess.run(
            [sys.executable, '-m', 'rkv1', command, str(self.library), *map(str, args)],
            capture_output=True, text=True, encoding='utf-8', timeout=20,
        )

    def test_default_writes_and_real_cli_share_scope(self):
        initial = self.cli('memory-init', self.original, '--index-profile', 'compact-base-v3')
        self.assertEqual(initial.returncode, 0, initial.stderr)
        old_sid = json.loads(initial.stdout)['snapshot_id']
        memory = Memory(self.library)
        with memory.pin() as pinned, memory.writer() as scope:
            before = ledger(self.library, held=True)
            with self.assertRaises(BlockingIOError):
                Memory(self.library).add(self.revision)
            with self.assertRaises(BlockingIOError):
                memory.enable_replay_budget()
            for command, args in (('memory-add', (self.revision,)), ('memory-budget', ())):
                refused = self.cli(command, *args)
                self.assertEqual(refused.returncode, 2, refused.stderr)
                self.assertTrue(refused.stderr.strip())
                self.assertEqual(refused.stdout, '')
            existing = self.cli('memory-init', self.revision)
            self.assertEqual(existing.returncode, 2, existing.stderr)
            self.assertEqual(ledger(self.library, held=True), before)
            self.assertEqual(scope.enable_replay_budget()['snapshot_id'], old_sid)
            new_sid = scope.add(self.revision, label='scoped')['snapshot_id']
            self.assertNotEqual(old_sid, new_sid)
            verify(memory, pinned.search('RKV99PROBE'), source(9, 0), old_sid)

        budget = self.cli('memory-budget')
        self.assertEqual(budget.returncode, 0, budget.stderr)
        self.assertEqual(json.loads(budget.stdout)['snapshot_id'], new_sid)
        updated = self.cli('memory-add', self.revision, '--label', 'cli')
        self.assertEqual(updated.returncode, 0, updated.stderr)
        cli_sid = json.loads(updated.stdout)['snapshot_id']
        verify(memory, memory.search('RKV99PROBE'), source(9, 1), cli_sid)
        verify(memory, memory.search('RKV99PROBE', snapshot=old_sid), source(9, 0), old_sid)
        with self.assertRaisesRegex(ValueError, 'closed'):
            scope.enable_replay_budget()

    def test_failed_default_operations_release_lock(self):
        memory = Memory.create(self.library, index_profile='full-v1')
        sid = memory.add(self.original)['snapshot_id']
        before = ledger(self.library)
        with self.assertRaises((FileNotFoundError, ValueError)):
            memory.add(self.root / 'missing')
        with self.assertRaisesRegex(ValueError, 'v3 base profile'):
            memory.enable_replay_budget()
        self.assertEqual(ledger(self.library), before)
        with memory.writer():
            self.assertEqual(memory.current(), sid)

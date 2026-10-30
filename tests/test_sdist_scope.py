import hashlib
import io
from pathlib import Path
import tarfile
import tempfile
import unittest
from scripts.sdist_scope import audit_archive


class SdistScopeTests(unittest.TestCase):
    def audit(self, entries, expected=None):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'source.tar.gz'
            with tarfile.open(p,'w:gz') as out:
                for name,raw in entries:
                    member=tarfile.TarInfo(name);member.size=len(raw)
                    out.addfile(member,io.BytesIO(raw))
            return audit_archive(p,'0.93.0',expected or {'rkv1/a.py':hashlib.sha256(b'code').hexdigest()})

    def test_required_bytes_and_current_output_retained(self):
        expected={'rkv1/a.py':hashlib.sha256(b'code').hexdigest(),'results/v0.93.0/README.md':hashlib.sha256(b'current').hexdigest()}
        r=self.audit([('rkv1-0.93.0/'+n,b'code' if n.endswith('.py') else b'current') for n in expected],expected)
        self.assertEqual(r['required_files'],2)

    def test_old_results_private_unknown_wrongroot_and_traversal_refuse(self):
        for bad in ('results/v0.92.0/raw.json','.tools/key','unknown.bin','../outside'):
            with self.subTest(bad=bad),self.assertRaises(ValueError):
                self.audit([('rkv1-0.93.0/rkv1/a.py',b'code'),('rkv1-0.93.0/'+bad,b'x')])
        with self.assertRaises(ValueError):self.audit([('rkv1-0.92.0/rkv1/a.py',b'code')])

    def test_missing_changed_and_duplicate_members_refuse(self):
        for entries in ([],[('rkv1-0.93.0/rkv1/a.py',b'changed')],[('rkv1-0.93.0/rkv1/a.py',b'code')]*2):
            with self.assertRaises(ValueError):self.audit(entries)

    def test_manifest_requires_explicit_current_version(self):
        import re
        root=Path(__file__).resolve().parents[1]
        version=re.search(r'^version = "([^"]+)"', (root/'pyproject.toml').read_text('utf-8'),re.M)[1]
        lines=(root/'MANIFEST.in').read_text('utf-8').splitlines()
        self.assertIn('prune results',lines)
        self.assertIn('recursive-include results/v'+version+' *.json *.jsonl *.md *.png',lines)
        self.assertNotIn('recursive-include results *.json *.jsonl *.md *.png',lines)

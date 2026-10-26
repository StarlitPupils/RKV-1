import ctypes
import json
import os
from pathlib import Path
import tempfile
import unittest

from rkv1.memory import Memory, _head, _open_head


class HeadSharingTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)

    @unittest.skipUnless(os.name=='nt','Windows delete-sharing handle semantics')
    def test_live_reader_keeps_old_bytes_while_new_head_replaces_name(self):
        path=self.root/'HEAD.json';old={'version':1,'snapshot_id':'1'*64};new={'version':1,'snapshot_id':'2'*64}
        _head(path,old)
        with _open_head(path) as held:
            _head(path,new)
            with _open_head(path) as current:self.assertEqual(json.loads(current.read()),new)
            self.assertEqual(json.loads(held.read()),old)

    @unittest.skipUnless(os.name=='nt','Windows native handle ownership')
    def test_closing_reader_closes_underlying_native_handle(self):
        import msvcrt
        from ctypes import wintypes
        path=self.root/'HEAD.json';path.write_bytes(b'{}')
        stream=_open_head(path);self.assertFalse(os.get_inheritable(stream.fileno()))
        handle=msvcrt.get_osfhandle(stream.fileno());stream.close()
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        gettype=kernel.GetFileType;gettype.argtypes=(wintypes.HANDLE,);gettype.restype=wintypes.DWORD
        ctypes.set_last_error(0)
        self.assertEqual(gettype(handle),0);self.assertEqual(ctypes.get_last_error(),6)

    def test_missing_malformed_and_invalid_identity_are_not_hidden(self):
        memory=Memory.create(self.root/'memory');path=memory.root/'HEAD.json'
        with self.assertRaises(FileNotFoundError):memory.current()
        path.write_bytes(b'{')
        with self.assertRaises(json.JSONDecodeError):memory.current()
        path.write_text(json.dumps({'version':1,'snapshot_id':'bad'}),encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'Invalid memory HEAD'):memory.current()


if __name__=='__main__':unittest.main()

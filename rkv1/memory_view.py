"""A fixed-SID identity handle; no decoded blocks, DBs or result cache."""
from .core import valid_hash

class ReadView:
    __slots__ = ('_memory', '_snapshot_id')
    def __init__(self, memory, *, snapshot=None):
        from rkv1.memory import Memory
        if not isinstance(memory, Memory):
            raise TypeError('Memory instance required')
        if snapshot is not None and (type(snapshot) is not str or not valid_hash(snapshot)):
            raise ValueError('Explicit snapshot must be a SHA256 SID')
        sid = memory.current() if snapshot is None else snapshot
        memory._manifest(sid)
        self._snapshot_id, self._memory = sid, memory

    @property
    def snapshot_id(self):
        return self._snapshot_id

    @property
    def closed(self):
        return self._memory is None

    def _open(self):
        if self.closed:
            raise ValueError('Memory read view is closed')
        return self._memory

    def info(self):
        return {'snapshot_id': self._snapshot_id, 'closed': self.closed,
                'scope': 'fixed snapshot identity; every operation verifies source anew',
                'cached_results_or_decoded_source': False}

    def search(self, question, *, top_k=5):
        return self._open().search(question, top_k=top_k, snapshot=self._snapshot_id)

    def lookup(self, key):
        return self._open().lookup(key, snapshot=self._snapshot_id)

    def lookup_many(self, keys, *, max_source_bytes=1<<20):
        return self._open().lookup_many(keys, snapshot=self._snapshot_id,
                                        max_source_bytes=max_source_bytes)

    def close(self):
        self._memory = None

    def __enter__(self):
        self._open()
        return self

    def __exit__(self, *args):
        self.close()

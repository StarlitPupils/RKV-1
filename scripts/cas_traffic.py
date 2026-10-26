"""Single-threaded assessment scope; application CAS traffic, not physical I/O."""
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch
import rkv1.store as store_module


class _Reader:
    def __init__(self,stream,data):self.stream=stream;self.data=data
    def read(self,size=-1):
        raw=self.stream.read(size)
        self.data['read_calls']+=1;self.data['application_CAS_file_bytes']+=len(raw)
        return raw
    def __enter__(self):self.stream.__enter__();return self
    def __exit__(self,*args):return self.stream.__exit__(*args)
    def __getattr__(self,name):return getattr(self.stream,name)


class CASTraffic:
    def __init__(self,store):
        self.objects=(store.root/'objects').absolute()
        self.data={'object_opens':0,'read_calls':0,'application_CAS_file_bytes':0,'decode_attempts':0,
                   'decode_successes':0,'payload_input_bytes':0,'CAS_decoded_output_bytes':0,
                   'compressed_decode_output_bytes':0,'raw_codec_output_bytes':0}
        self.active=False

    def __enter__(self):
        if self.active:raise RuntimeError('CAS traffic scope already active')
        self.active=True;self.stack=ExitStack()
        original_open=Path.open;original_decode=store_module.decompress
        def opened(path,*args,**kwargs):
            stream=original_open(path,*args,**kwargs)
            mode=args[0] if args else kwargs.get('mode','r')
            if 'r' in mode and 'b' in mode and path.absolute().is_relative_to(self.objects):
                self.data['object_opens']+=1
                return _Reader(stream,self.data)
            return stream
        def decoded(*args,**kwargs):
            self.data['decode_attempts']+=1
            raw=original_decode(*args,**kwargs)
            self.data['decode_successes']+=1;self.data['payload_input_bytes']+=len(args[0])
            self.data['CAS_decoded_output_bytes']+=len(raw)
            field='raw_codec_output_bytes' if args[1]=='raw' else 'compressed_decode_output_bytes'
            self.data[field]+=len(raw)
            return raw
        self.stack.enter_context(patch.object(Path,'open',opened))
        self.stack.enter_context(patch.object(store_module,'decompress',decoded))
        return self

    def __exit__(self,*args):
        try:return self.stack.__exit__(*args)
        finally:self.active=False

    def result(self):
        return {**self.data,'physical_SSD_bytes':None,'all_system_file_bytes':None,
                'scope':'Trace-only application CAS object binary read returns and decoder outputs; excludes metadata/SQLite/audit/ingest'}

"""Cooperative, fail-fast OS-held writer scope. The lock file is never removed."""
import errno,os,stat,threading,weakref

def _regular_or_absent(path):
    if path.exists() or path.is_symlink():
        value=path.lstat()
        if (not stat.S_ISREG(value.st_mode) or stat.S_ISLNK(value.st_mode)
                or getattr(value,'st_file_attributes',0)&getattr(stat,'FILE_ATTRIBUTE_REPARSE_POINT',1024)):
            raise ValueError('Writer lock must be a nonlinked regular pathname')

def _acquire(path):
    _regular_or_absent(path)
    if os.name=='nt':
        import ctypes
        from ctypes import wintypes
        dll=ctypes.WinDLL('kernel32',use_last_error=True)
        create=dll.CreateFileW
        create.argtypes=(wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,wintypes.LPVOID,wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE)
        create.restype=wintypes.HANDLE
        close=dll.CloseHandle;close.argtypes=(wintypes.HANDLE,);close.restype=wintypes.BOOL
        get=dll.GetHandleInformation;get.argtypes=(wintypes.HANDLE,ctypes.POINTER(wintypes.DWORD));get.restype=wintypes.BOOL
        handle=create(str(path),0xC0000000,0,None,4,0x00200080,None)
        if handle==ctypes.c_void_p(-1).value:
            error=ctypes.get_last_error()
            if error in (32,33):raise BlockingIOError(errno.EWOULDBLOCK,'Another cooperative Memory writer holds this scope')
            raise ctypes.WinError(error)
        try:
            _regular_or_absent(path)
            flags=wintypes.DWORD()
            if not get(handle,ctypes.byref(flags)):raise ctypes.WinError(ctypes.get_last_error())
            if flags.value&1:raise ValueError('Writer handle unexpectedly inheritable')
        except BaseException:close(handle);raise
        return lambda:close(handle),'Windows CreateFileW sharing=0 noninheritable handle'
    import fcntl
    fd=os.open(path,os.O_RDWR|os.O_CREAT|getattr(os,'O_NOFOLLOW',0)|getattr(os,'O_CLOEXEC',0),0o600)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode) or os.fstat(fd).st_nlink!=1:raise ValueError('Writer lock must have one regular link')
        os.set_inheritable(fd,False)
        fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BaseException:os.close(fd);raise
    return lambda:os.close(fd),'POSIX flock LOCK_EX|LOCK_NB noninheritable descriptor'

class WriterScope:
    __slots__=('_memory','_pid','_thread','_release','_backend','_busy','_entered','__weakref__')
    def __init__(self,memory):
        from rkv1.memory import Memory
        if not isinstance(memory,Memory):raise TypeError('Memory instance required')
        release,backend=_acquire(memory.root/'.writer.lock')
        self._release=weakref.finalize(self,release)
        self._memory=memory;self._pid=os.getpid();self._thread=threading.get_ident()
        self._backend=backend;self._busy=False;self._entered=False

    @property
    def closed(self):return not self._release.alive

    def _owner(self):
        if self.closed:raise ValueError('Memory writer scope is closed')
        if os.getpid()!=self._pid or threading.get_ident()!=self._thread:raise ValueError('Writer scope belongs to its creating process and thread')

    def info(self):
        return {'closed':self.closed,'owner_pid':self._pid,'backend':self._backend,
                'handle_inheritable':False,'scope':'Cooperating Memory.writer callers only; direct Memory.add can bypass',
                'lock_file_persisted':True,'automatic_retry':False}

    def add(self,source,*,label='evidence',chunker_backend='python',native_library=None):
        self._owner()
        if self._busy:raise ValueError('Reentrant writer operation refused')
        self._busy=True
        try:return self._memory.add(source,label=label,chunker_backend=chunker_backend,native_library=native_library)
        finally:self._busy=False

    def close(self):
        if self.closed:return
        self._owner()
        if self._busy:raise ValueError('Cannot close an active writer operation')
        self._release();self._memory=None

    def __enter__(self):
        self._owner()
        if self._entered:raise ValueError('Nested writer context refused')
        self._entered=True
        return self

    def __exit__(self,*args):self.close()

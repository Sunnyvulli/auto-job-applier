"""Process-lifetime advisory lock; avoids concurrent browser/profile access."""
import os
from pathlib import Path

def acquire(folder):
    Path(folder).mkdir(parents=True,exist_ok=True)
    handle=open(Path(folder)/'instance.lock','a+b')
    handle.seek(0);handle.write(b'0');handle.flush();handle.seek(0)
    try:
        if os.name=='nt':
            import msvcrt
            msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
    except OSError:
        handle.close();raise RuntimeError('ApplyPilot is already running. Use the existing window.')
    return handle

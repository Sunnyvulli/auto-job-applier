"""Capability reporting and browser selection without extra services."""
import ctypes
import os
import platform
import shutil
import struct
import sys
from pathlib import Path

def memory_gb():
    try:
        if sys.platform=='win32':
            class Memory(ctypes.Structure):
                _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong)]+[(k,ctypes.c_ulonglong) for k in ('total','available','page_total','page_available','virtual_total','virtual_available','extended')]
            info=Memory();info.length=ctypes.sizeof(info);ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(info))
            return round(info.total/1024**3,1)
        return round(os.sysconf('SC_PAGE_SIZE')*os.sysconf('SC_PHYS_PAGES')/1024**3,1)
    except Exception:return None

def capabilities(folder):
    ram=memory_gb()
    return {'os':platform.platform(),'architecture':platform.machine(),'python_bits':struct.calcsize('P')*8,'ram_gb':ram,'free_disk_gb':round(shutil.disk_usage(folder).free/1024**3,1),'low_resource_recommended':ram is not None and ram<=4.5,'bundled_browser':Path(os.environ.get('PLAYWRIGHT_BROWSERS_PATH','')).is_dir() if os.environ.get('PLAYWRIGHT_BROWSERS_PATH') else not getattr(sys,'frozen',False),'support':'Windows 11 x64 is the supported laptop target. ARM emulation is checked separately; legacy 32-bit Windows is unsupported.'}

def browser_order(choice='auto'):
    if choice not in {'auto','bundled','msedge','chrome'}:raise ValueError('Unsupported browser option.')
    if choice!='auto':return [choice]
    frozen=getattr(sys,'frozen',False)
    bundled=Path(os.environ.get('PLAYWRIGHT_BROWSERS_PATH','')).is_dir() if frozen else True
    if bundled:return ['bundled','msedge','chrome'] if sys.platform=='win32' else ['bundled']
    return ['msedge','chrome','bundled']

def launch_context(engine,folder,choice='auto',headless=False):
    for candidate in browser_order(choice):
        options=dict(headless=headless,accept_downloads=False,chromium_sandbox=True,channel='chromium')
        if candidate!='bundled':options['channel']=candidate
        # Keep each engine's cookies/profile separate across upgrades and channel changes.
        name='browser-session' if candidate=='bundled' else 'browser-session-'+candidate
        try:return engine.launch_persistent_context(str(Path(folder)/name),**options)
        except Exception:continue
    raise ValueError('No compatible browser could start. Install the Full edition, choose an installed Edge/Chrome browser in Preferences, or check the Diagnostics page.')

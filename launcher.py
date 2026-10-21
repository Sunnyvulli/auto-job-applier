import os
import sys
from pathlib import Path
if getattr(sys,'frozen',False):
    # Bundled browser is installed at build time, not downloaded on first launch.
    os.environ['PLAYWRIGHT_BROWSERS_PATH']=str(Path(sys._MEIPASS)/'browsers')
from applypilot.desktop import main
if __name__=='__main__':main()

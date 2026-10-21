import os
import sys
from pathlib import Path
if getattr(sys,'frozen',False):
    os.environ['PLAYWRIGHT_BROWSERS_PATH']=str(Path(sys._MEIPASS)/'browsers')

def smoke_test(report):
    """Exercise the installed GUI, PDFs and bundled browser using synthetic data."""
    import json
    import tempfile
    import tkinter as tk
    from applypilot.desktop import App
    from applypilot.core import documents
    from playwright.sync_api import sync_playwright
    checks=[]
    root=None
    try:
        with tempfile.TemporaryDirectory() as folder:
            root=tk.Tk();app=App(root,folder);root.update();checks.append('desktop initialized')
            for key,value in [('name','Synthetic Test User'),('email','test@example.com')]:
                app.fields[key].delete('1.0','end');app.fields[key].insert('1.0',value)
            app.save_profile()
            jid=app.store.add(dict(url='https://jobs.lever.co/test/synthetic/apply',company='Synthetic',title='Test role'))
            app.refresh();assert len(app.tree.get_children())==1;checks.append('profile and dashboard')
            dest=documents(app.store,app.store.setting('profile'),app.store.job(jid));assert (dest/'resume.pdf').stat().st_size>500;checks.append('PDF generation')
            with sync_playwright() as p:
                browser=p.chromium.launch(headless=True,chromium_sandbox=True)
                page=browser.new_page();page.set_content('<h1>Bundled Chromium works</h1>');assert page.locator('h1').inner_text()=='Bundled Chromium works';browser.close()
            checks.append('bundled Chromium launch')
            from google_auth_oauthlib.flow import InstalledAppFlow
            checks.append('OAuth library import')
            from applypilot.accounts import save_account
            import keyring, secrets
            account='smoke-'+secrets.token_hex(8)+'@example.com'
            origin=save_account(app.store,'https://fixture.invalid',account)
            try:
                assert len(keyring.get_password('ApplyPilotPortal:'+origin,account))==24
                checks.append('Windows credential vault round trip')
            finally:
                keyring.delete_password('ApplyPilotPortal:'+origin,account)
            root.destroy();root=None
        Path(report).write_text(json.dumps({'ok':True,'checks':checks}),encoding='utf-8')
        return 0
    except Exception as e:
        if root:
            try:root.destroy()
            except Exception:pass
        Path(report).write_text(json.dumps({'ok':False,'checks':checks,'error':str(e)}),encoding='utf-8')
        return 1

if __name__=='__main__':
    if len(sys.argv)==3 and sys.argv[1]=='--smoke-test':
        sys.exit(smoke_test(sys.argv[2]))
    from applypilot.desktop import main
    main()

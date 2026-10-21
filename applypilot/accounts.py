"""Exact-origin credential helpers. Passwords never enter the database or log."""
import secrets
import string
from urllib.parse import urlsplit

def account_origin(url):
    p=urlsplit(url)
    if p.scheme!='https' or p.username or p.password or not p.hostname or p.port not in (None,443):
        raise ValueError('Account tools require a standard HTTPS origin.')
    if p.hostname in {'localhost','127.0.0.1','::1'}:raise ValueError('Use a public portal origin.')
    return 'https://'+p.hostname.lower()

def generate_password():
    alphabet=string.ascii_letters+string.digits+'!@#%_-'
    while True:
        value=''.join(secrets.choice(alphabet) for _ in range(24))
        if all(any(c in group for c in value) for group in (string.ascii_lowercase,string.ascii_uppercase,string.digits,'!@#%_-')):return value

def save_account(store,url,email,password=None):
    import keyring
    origin=account_origin(url)
    if '@' not in email:raise ValueError('Enter your account email.')
    if password is None:password=generate_password()
    if len(password)<8:raise ValueError('Use a password of at least eight characters.')
    keyring.set_password('ApplyPilotPortal:'+origin,email,password)
    configured=store.setting('accounts',{})
    configured[origin]=email;store.save_setting('accounts',configured)
    return origin

def fill_account(page,store):
    import keyring
    origin=account_origin(page.url)
    email=store.setting('accounts',{}).get(origin)
    if not email:raise ValueError('This exact portal origin has no saved account. Configure it in Account tools.')
    password=keyring.get_password('ApplyPilotPortal:'+origin,email)
    if not password:raise ValueError('No password is available in the operating-system vault.')
    count=0
    # Top frame only: third-party embedded frames must not receive credentials.
    for el in page.locator('input').all():
        if not el.is_visible() or not el.is_enabled():continue
        typ=(el.get_attribute('type') or '').lower()
        auto=(el.get_attribute('autocomplete') or '').lower()
        try:
            if typ=='password':el.fill(password);count+=1
            elif typ=='email' or auto=='username':el.fill(email);count+=1
        except Exception:
            raise ValueError('Account fields could not be filled. Complete this step manually.') from None
    return count

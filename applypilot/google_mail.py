"""User-configured Gmail desktop OAuth. No credentials are distributed with the app."""
import base64
import json
from . import mail

READ='https://www.googleapis.com/auth/gmail.readonly'
SEND='https://www.googleapis.com/auth/gmail.send'
SERVICE='ApplyPilotGoogle'

def import_client(path):
    import keyring
    from pathlib import Path
    cfg=json.loads(Path(path).read_text(encoding='utf-8'))
    installed=cfg.get('installed',{})
    if installed.get('auth_uri')!='https://accounts.google.com/o/oauth2/auth' or installed.get('token_uri')!='https://oauth2.googleapis.com/token' or not installed.get('client_id','').endswith('.apps.googleusercontent.com'):
        raise ValueError('Import an official Google OAuth Desktop app client JSON.')
    keyring.set_password(SERVICE,'client-config',json.dumps(cfg))

def connect(allow_send=False):
    import keyring
    from google_auth_oauthlib.flow import InstalledAppFlow
    raw=keyring.get_password(SERVICE,'client-config')
    if not raw:raise ValueError('Import your Google Desktop OAuth client JSON first. See Gmail setup instructions.')
    scopes=[READ]+([SEND] if allow_send else [])
    flow=InstalledAppFlow.from_client_config(json.loads(raw),scopes,autogenerate_code_verifier=True)
    creds=flow.run_local_server(host='127.0.0.1',port=0,open_browser=True,timeout_seconds=180,prompt='consent',access_type='offline',authorization_prompt_message='Complete Gmail consent in your browser.',success_message='ApplyPilot connected. You can close this page.')
    keyring.set_password(SERVICE,'token',creds.to_json())
    return 'Gmail OAuth connected. You can now Sync using Gmail OAuth.'

def session():
    import keyring
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request,AuthorizedSession
    raw=keyring.get_password(SERVICE,'token')
    if not raw:raise ValueError('Connect Gmail OAuth first.')
    creds=Credentials.from_authorized_user_info(json.loads(raw))
    if creds.expired and creds.refresh_token:
        creds.refresh(Request());keyring.set_password(SERVICE,'token',creds.to_json())
    return AuthorizedSession(creds)

def checked(response):
    if not response.ok:raise ValueError(f'Gmail API request failed ({response.status_code}); reconnect or check Gmail API setup.')
    return response.json()

def recent_raw(limit=100):
    with session() as client:
        data=checked(client.get('https://gmail.googleapis.com/gmail/v1/users/me/messages',params={'maxResults':limit,'labelIds':'INBOX'},timeout=25))
        for item in data.get('messages',[]):
            record=checked(client.get('https://gmail.googleapis.com/gmail/v1/users/me/messages/'+item['id'],params={'format':'raw'},timeout=25))
            encoded=record['raw'];yield base64.urlsafe_b64decode(encoded+'='*(-len(encoded)%4))

def sync(store):
    count=0
    for raw in recent_raw():mail.ingest(store,raw);count+=1
    return count

def send(to,subject,body):
    from email.message import EmailMessage
    from email.utils import parseaddr
    if any('\n' in s or '\r' in s for s in (to,subject)) or '@' not in parseaddr(to)[1]:raise ValueError('Invalid recipient or subject.')
    msg=EmailMessage();msg['To']=to;msg['Subject']=subject;msg.set_content(body)
    with session() as client:
        profile=checked(client.get('https://gmail.googleapis.com/gmail/v1/users/me/profile',timeout=25))
        msg['From']=profile['emailAddress']
        encoded=base64.urlsafe_b64encode(msg.as_bytes()).decode()
        checked(client.post('https://gmail.googleapis.com/gmail/v1/users/me/messages/send',json={'raw':encoded},timeout=25))

def disconnect():
    import keyring
    import requests
    raw=keyring.get_password(SERVICE,'token')
    if raw:
        data=json.loads(raw)
        # Remove local authorization even when remote revocation is temporarily unavailable.
        keyring.delete_password(SERVICE,'token')
        token=data.get('refresh_token') or data.get('token')
        if token:
            response=requests.post('https://oauth2.googleapis.com/revoke',data={'token':token},timeout=15)
            if response.status_code not in (200,400):raise ValueError('Disconnected locally. Remove access in your Google account to complete remote revocation.')
    return 'Gmail OAuth disconnected.'

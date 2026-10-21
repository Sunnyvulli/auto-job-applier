import hashlib
import json
import zipfile
import pytest
from applypilot.core import Store,documents
from applypilot.recovery import create_backup,read_backup,restore_backup,daily_backup


def workspace(folder):
    store=Store(folder)
    store.save_setting('profile',{'name':'Test User','email':'test@example.com','skills':'SQL','answers':{'Sponsorship':'Yes'}})
    store.save_setting('preferences',{'titles':'Engineer','min_skills':0,'queue_limit':10})
    jid=store.add(dict(url='https://example.com/test',company='Acme',title='Engineer'))
    store.state(jid,'submitted')
    with store.connect() as c:c.execute('INSERT INTO messages VALUES (?,?,?,?,?,?,?)',('msg1',jid,'hr@example.com','Interview','Private email text','interview','2026-01-01'))
    return store,jid


def rewrite(path,mutate):
    with zipfile.ZipFile(path) as z:files={n:z.read(n) for n in z.namelist()}
    data=json.loads(files['data.json']);mutate(data);files['data.json']=json.dumps(data).encode()
    manifest=json.loads(files['manifest.json']);manifest['files']['data.json']=hashlib.sha256(files['data.json']).hexdigest();files['manifest.json']=json.dumps(manifest).encode()
    with zipfile.ZipFile(path,'w') as z:
        for n,b in files.items():z.writestr(n,b)


def test_backup_restore_history_and_privacy(tmp_path):
    source,jid=workspace(tmp_path/'source')
    for key,value in [('accounts',{'https://portal.example':'user@example.com'}),('mail',{'address':'user@example.com'}),('auto_submit',True),('repeat_sources',True)]:source.save_setting(key,value)
    (source.folder/'browser-session').mkdir();(source.folder/'browser-session'/'cookie').write_text('secret-cookie')
    backup=create_backup(source,tmp_path/'data.applypilot')
    with zipfile.ZipFile(backup) as z:
        assert set(z.namelist())=={'manifest.json','data.json'}
        payload=z.read('data.json');assert b'secret-cookie' not in payload and b'accounts' not in payload and b'auto_submit' not in payload
    target=Store(tmp_path/'target');old=target.add(dict(url='https://example.com/old',company='Old',title='Old'))
    docs=target.folder/'documents';docs.mkdir();(docs/'receipt.json').write_text('old receipt')
    safety=restore_backup(target,backup)
    assert not docs.exists()
    assert (safety.parent/(safety.stem+'-documents')/'receipt.json').read_text()=='old receipt'
    assert target.job(jid)['status']=='submitted'
    with pytest.raises(ValueError):target.claim(jid)
    assert target.setting('profile')['name']=='Test User'
    assert target.setting('auto_submit') is False and target.setting('repeat_sources') is False
    with target.connect() as c:assert c.execute('SELECT body FROM messages').fetchone()[0]=='Private email text'
    assert read_backup(safety)[0]['jobs'][0]['id']==old
    assert target.setting('accounts') is None and target.setting('mail') is None


def test_original_resume_portable_and_interrupted_states(tmp_path):
    source,jid=workspace(tmp_path/'source');source.state(jid,'needs_attention')
    original=documents(source,source.setting('profile'),source.job(jid))/'resume.pdf'
    source.save_setting('resume_pdf',str(original));source.save_setting('planned_queue',[jid])
    backup=create_backup(source,tmp_path/'backup.applypilot');expected=original.read_bytes();original.unlink()
    target=Store(tmp_path/'target');restore_backup(target,backup)
    from pathlib import Path
    assert Path(target.setting('resume_pdf')).read_bytes()==expected
    assert target.job(jid)['status']=='uncertain'


def test_corrupt_hash_rejected_without_mutation(tmp_path):
    store,jid=workspace(tmp_path/'source');backup=create_backup(store,tmp_path/'backup.applypilot')
    with zipfile.ZipFile(backup) as z:manifest=z.read('manifest.json')
    with zipfile.ZipFile(backup,'w') as z:z.writestr('manifest.json',manifest);z.writestr('data.json','{}')
    with pytest.raises(ValueError,match='integrity'):restore_backup(store,backup)
    assert store.job(jid)['status']=='submitted'
    assert not (store.folder/'backups').exists()


@pytest.mark.parametrize('mutate',[
    lambda d:d['jobs'][0].update(url='http://localhost/private'),
    lambda d:d['settings'].update(accounts={'bad':'secret'}),
    lambda d:d['settings'].update(planned_queue=['unknown-job']),
    lambda d:d['jobs'][0].update(status='unknown'),
])
def test_invalid_data_rejected_even_with_valid_hash(tmp_path,mutate):
    store,jid=workspace(tmp_path/'source');backup=create_backup(store,tmp_path/'backup.applypilot');rewrite(backup,mutate)
    with pytest.raises(ValueError):restore_backup(store,backup)
    assert store.job(jid)['status']=='submitted'


def test_zip_traversal_and_duplicate_entries_rejected(tmp_path):
    path=tmp_path/'bad.applypilot'
    with zipfile.ZipFile(path,'w') as z:z.writestr('../outside','bad')
    with pytest.raises(ValueError):read_backup(path)
    with zipfile.ZipFile(path,'w') as z:
        z.writestr('manifest.json','{}');z.writestr('data.json','{}')
        with pytest.warns(UserWarning):z.writestr('data.json','{}')
    with pytest.raises(ValueError):read_backup(path)
    assert not (tmp_path/'outside').exists()


def test_daily_backup_rotation_and_same_day_noop(tmp_path):
    store,jid=workspace(tmp_path/'data');folder=store.folder/'backups';folder.mkdir()
    for day in range(1,8):(folder/f'daily-202001{day:02}.applypilot').write_bytes(b'old')
    assert daily_backup(store)
    assert len(list(folder.glob('daily-*')))==5
    assert daily_backup(store) is None
    assert len(list(folder.glob('daily-*')))==5


def test_restore_failure_rolls_back_data_and_documents(tmp_path,monkeypatch):
    import contextlib
    import sqlite3
    source,_=workspace(tmp_path/'source');backup=create_backup(source,tmp_path/'backup.applypilot')
    target=Store(tmp_path/'target');old=target.add(dict(url='https://example.com/old',company='Old',title='Old'))
    docs=target.folder/'documents';docs.mkdir();(docs/'keep.txt').write_text('keep')
    real_connect=target.connect
    class Connection:
        def __init__(self,c):self.c=c
        def execute(self,*args):return self.c.execute(*args)
        def executemany(self,sql,*args):
            if 'INTO messages' in sql:raise sqlite3.OperationalError('Simulated disk failure')
            return self.c.executemany(sql,*args)
    @contextlib.contextmanager
    def broken_connect():
        with real_connect() as c:yield Connection(c)
    monkeypatch.setattr(target,'connect',broken_connect)
    with pytest.raises(sqlite3.OperationalError):restore_backup(target,backup)
    assert target.job(old)['company']=='Old'
    assert (docs/'keep.txt').read_text()=='keep'


def test_backup_size_limit_before_reading_payload(tmp_path,monkeypatch):
    import applypilot.recovery as recovery
    store,_=workspace(tmp_path/'source');backup=create_backup(store,tmp_path/'backup.applypilot')
    monkeypatch.setattr(recovery,'MAX_DATA',10)
    with pytest.raises(ValueError,match='size limits'):read_backup(backup)

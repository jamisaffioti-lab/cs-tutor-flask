"""Check the AI, through the Flask app: submit -> saved attempt -> teacher view.

Runs offline: dummy Anthropic key, temp database, local executor.
"""
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault('ANTHROPIC_API_KEY', 'test')
_DB = tempfile.NamedTemporaryFile(suffix='.db', delete=False).name
os.environ['DB_PATH'] = _DB

import app as appmod  # noqa: E402
from slop_detector.harness.loader import load_task, load_submission  # noqa: E402


def _user(db_role, email):
    db = appmod.get_db()
    db.execute('INSERT INTO users (google_id, email, name, role) VALUES (?, ?, ?, ?)',
               (email, email, email.split('@')[0], db_role))
    db.commit()
    uid = db.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone()[0]
    db.close()
    return uid


def _client(uid, role):
    c = appmod.app.test_client()
    with c.session_transaction() as s:
        s['user_id'], s['role'], s['name'] = uid, role, 'x'
    return c


def test_student_attempt_is_saved_and_teacher_sees_evidence():
    sid = _user('student', 'stu@example.com')
    tid = _user('teacher', 'teach@example.com')
    stu = _client(sid, 'student')

    assert stu.get('/check').status_code == 200
    task = stu.get('/check/api/task/csp-slop-03').get_json()
    assert 'defects' not in task and 'hidden_tests' not in task  # answer key stays server-side

    sub = load_submission('sample_pass_03')
    sub['explanation'] = 'It started at 0, so all-negative lists were wrong.'
    r = stu.post('/check/api/submit', json=sub).get_json()
    assert r['passed'] is True and r['attempt_no'] == 1 and r['overall'] == {'passed': 1, 'total': 5}

    r2 = stu.post('/check/api/submit', json=load_submission('sample_fail_03')).get_json()
    assert r2['passed'] is False and r2['attempt_no'] == 2

    # students can't see the teacher view
    assert stu.get('/teacher').status_code == 302

    teach = _client(tid, 'teacher')
    roster = teach.get('/teacher').get_data(as_text=True)
    assert 'stu' in roster and '1/5' in roster
    page = teach.get(f'/teacher/student/{sid}').get_data(as_text=True)
    assert 'It started at 0, so all-negative lists were wrong.' in page
    assert 'Real mistake' in page and 'Flagged correct code' in page
    assert 'nums[0]' in page  # their submitted code


def test_bad_submissions_rejected():
    sid = _user('student', 'stu2@example.com')
    c = _client(sid, 'student')
    assert c.post('/check/api/submit', json={'task_id': 'nope'}).status_code == 404
    assert c.post('/check/api/submit', json={'task_id': 'csp-slop-01', 'edited_code': ''}).status_code == 400


def test_sandbox_down_saves_nothing(monkeypatch):
    sid = _user('student', 'stu3@example.com')
    c = _client(sid, 'student')
    from slop_detector.harness import executor

    def boom(*a, **k):
        raise executor.SandboxUnavailable('down')
    monkeypatch.setattr(appmod, 'score_slop', boom)
    r = c.post('/check/api/submit', json=load_submission('sample_pass'))
    assert r.status_code == 503
    db = appmod.get_db()
    assert db.execute('SELECT COUNT(*) FROM attempts WHERE user_id = ?', (sid,)).fetchone()[0] == 0


def test_gmail_dots_and_case_are_ignored():
    assert appmod._canon_email('Nova.Noros@gmail.com') == appmod._canon_email('novanoros@gmail.com')
    assert appmod._canon_email('a.b@school.org') == 'a.b@school.org'


def test_role_column_migrates_on_old_database():
    import sqlite3
    old = tempfile.NamedTemporaryFile(suffix='.db', delete=False).name
    con = sqlite3.connect(old)
    con.execute('CREATE TABLE users (id INTEGER PRIMARY KEY, google_id TEXT, email TEXT, name TEXT, picture TEXT, created_at TIMESTAMP)')
    con.commit(); con.close()
    prev, appmod.DB_PATH = appmod.DB_PATH, old
    try:
        appmod.init_db()
        cols = [r[1] for r in sqlite3.connect(old).execute('PRAGMA table_info(users)')]
        assert 'role' in cols
    finally:
        appmod.DB_PATH = prev

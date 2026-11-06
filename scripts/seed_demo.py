"""Load demo students and scored attempts, so the teacher view has something
to show in a demo. Fake people only: no real student data, ever.

The tasks themselves are versioned JSON in slop_detector/tasks/ (they ship
with the code), so there is nothing to seed for them.

  python scripts/seed_demo.py           # add (or refresh) the demo students
  python scripts/seed_demo.py --clear   # remove them and their attempts

Uses the same DB_PATH as the app. On Render, run it once from the Shell tab.
Demo accounts can't sign in (they have no Google account); they exist only
so the roster has rows.
"""
import json
import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from slop_detector.harness.loader import load_task, load_submission  # noqa: E402
from slop_detector.harness.scorer import score  # noqa: E402
from slop_detector.harness.executor import LocalExecutor  # noqa: E402

DB_PATH = os.environ.get('DB_PATH', str(ROOT / 'tutorbot.db'))
DEMO_DOMAIN = 'demo.invalid'  # .invalid can never be a real address

# name -> list of sample submissions, in the order they "attempted" them
DEMO_STUDENTS = {
    'Demo Student A': ['sample_pass', 'sample_fail_02', 'sample_pass_02', 'sample_pass_03',
                       'sample_pass_04', 'sample_pass_05'],
    'Demo Student B': ['sample_fail', 'sample_pass', 'sample_fail_03', 'sample_fail_04'],
    'Demo Student C': ['sample_fail_05'],
}

EXPLANATIONS = {
    'sample_pass': 'The loop started at 1 so it skipped the first score, an empty passing list '
                   'divided by zero, and ROUND_HALF_UP is not something round() accepts. I tested '
                   'a list where only the first score passes.',
    'sample_fail': 'I think the <= 100 check is unnecessary.',
}


def clear(db):
    ids = [r[0] for r in db.execute('SELECT id FROM users WHERE email LIKE ?', (f'%@{DEMO_DOMAIN}',))]
    for uid in ids:
        db.execute('DELETE FROM attempts WHERE user_id = ?', (uid,))
        db.execute('DELETE FROM users WHERE id = ?', (uid,))
    db.commit()
    return len(ids)


def main():
    # Import the app once so its tables exist (init_db runs on import).
    os.environ.setdefault('ANTHROPIC_API_KEY', 'unused-for-seeding')
    os.environ['DB_PATH'] = DB_PATH
    import app  # noqa: F401

    db = sqlite3.connect(DB_PATH)
    removed = clear(db)
    if '--clear' in sys.argv:
        print(f'Removed {removed} demo students from {DB_PATH}')
        return

    ex = LocalExecutor()  # our own sample code, not student code: no sandbox needed
    for name, subs in DEMO_STUDENTS.items():
        slug = name.lower().replace(' ', '-')
        db.execute("INSERT INTO users (google_id, email, name, role) VALUES (?, ?, ?, 'student')",
                   (f'demo-{slug}', f'{slug}@{DEMO_DOMAIN}', name))
        uid = db.execute('SELECT id FROM users WHERE google_id = ?', (f'demo-{slug}',)).fetchone()[0]
        counts = {}
        for sub_name in subs:
            sub = load_submission(sub_name)
            task = load_task(sub['task_id'])
            res = score(task, sub, executor=ex)
            counts[task['task_id']] = counts.get(task['task_id'], 0) + 1
            db.execute(
                '''INSERT INTO attempts (user_id, task_id, attempt_no, flags_selected, submitted_code,
                   explanation_text, test_results, dimensions, score, passed, evidence, started_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)''',
                (uid, task['task_id'], counts[task['task_id']], json.dumps(sub.get('flags', [])),
                 sub['edited_code'], EXPLANATIONS.get(sub_name, ''),
                 json.dumps(res.evidence['tests']), json.dumps(res.dimensions),
                 sum(res.dimensions.values()), int(res.passed), json.dumps(res.evidence)))
    db.commit()
    print(f'Seeded {len(DEMO_STUDENTS)} demo students into {DB_PATH}')


if __name__ == '__main__':
    main()

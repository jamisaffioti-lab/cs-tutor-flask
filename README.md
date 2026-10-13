# Ascent Scholars - AI Tutor for AP CS

Flask app with Google sign-in (private beta allowlist in `app.py`).

- **Tutor** (`/chat/<subject>`): Socratic Claude tutor per subject.
- **Python lab** (`/lab`): AI Architect Week 1 lab. Code runs in the student's
  browser with Pyodide, so nothing runs on the server.
- **Check the AI** (`/check?task=csp-slop-01`): slop-detector tasks scored by
  `slop_detector/harness`. Run its tests with `python slop_detector/tests/test_scoring.py`.

## Environment variables (Render)

| Name | Purpose |
|---|---|
| `ANTHROPIC_API_KEY` | Claude API key (required) |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | Google sign-in |
| `SECRET_KEY` | Flask session key; set it so logins survive restarts |
| `TUTOR_MODEL` | Optional; defaults to `claude-sonnet-5-5` |
| `DB_PATH` | Optional; point at a Render persistent disk (e.g. `/var/data/tutorbot.db`) so conversations survive deploys |
| `EXECUTOR` | Optional; `local` (default) runs Check-the-AI tests on the server with resource limits. Not a sandbox: switch to Judge0 before real students use it. |

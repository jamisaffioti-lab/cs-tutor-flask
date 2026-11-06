# Ascent Scholars - AI Tutor for AP CS

Flask app with Google sign-in (private beta allowlist in `app.py`).
Styling matches noros.life: pages load `https://noros.life/tokens.css`, then
`static/css/ascent.css` (shared bar, buttons, cards).

- **Tutor** (`/chat/<subject>`): Socratic Claude tutor per subject.
- **Python lab** (`/lab`): The AI Architect, 12 lessons over 4 weeks. Lesson text
  and starter/solution code live in `labs/ai_architect.py`; check them with
  `python tests/test_lab_code.py`. Code runs in the student's browser (Pyodide),
  and each student's work is saved in their own browser.
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

## Check the AI (credential v1, AP CSP)

`/check` is the scored instrument for the "working with AI" credential. A student
gets AI-written Python with planted mistakes, clicks the lines that are wrong,
fixes the code, and writes a short explanation. Scoring is deterministic: no AI
grades anything.

**Tasks** (versioned JSON in `slop_detector/tasks/`, order set in `SLOP_TASK_ORDER`
in `app.py`):

| # | Task | Mistakes planted | Trap (correct code that looks wrong) |
|---|---|---|---|
| 1 | Class average | starts at index 1, divides by zero when none pass, made-up `ROUND_HALF_UP` | `<= 100` |
| 2 | Warmer days | compares to day 0 instead of the day before, divides by zero | `range(1, ...)` |
| 3 | Largest number | starts at 0, wrong for all-negative lists | strict `>` |
| 4 | Palindrome | comment says it lowercases; it doesn't | `word[::-1]` |
| 5 | Count vowels | counter reset inside the loop | `ch in "aeiou"` |

**How a task is scored.** Five dimensions, each level 1–4 (`slop_detector/harness/scorer.py`):

- **Detection:** share of the real mistakes flagged, minus flags on clean lines.
- **Diagnosis:** did they name the right kind of mistake for each line they caught.
- **Correction:** share of the hidden tests their fixed code passes.
- **Verification:** the tests the AI's code failed now pass, and nothing that passed broke.
- **Judgment (calibration):** they didn't flag the trap, and kept it in their fix.

A task is **passed** when all five are level 3 or higher. Score = the five levels
added up (out of 20). Overall result = tasks passed out of 5, counting any attempt.
The student's written explanation is saved as evidence for the teacher but not graded.

**Evidence.** Every submission is saved in the `attempts` table: lines flagged with
their type and reasoning, the code, every hidden test result, the explanation, the
five levels, attempt number, when the task was opened and when it was submitted.
Teachers see it at `/teacher` (roster) and `/teacher/student/<id>` (every attempt).

**Running student code.** Locally it runs in a capped subprocess (`EXECUTOR=local`,
the default; not a sandbox). On Render set `EXECUTOR=judge0` so it runs in a Judge0
sandbox. The Judge0 key stays on the server. If Judge0 is down, the student sees
"try again" and nothing is saved.

### Environment variables for Check the AI

| Variable | Value |
|---|---|
| `DB_PATH` | `/var/data/tutorbot.db` (on the Render disk, so data survives redeploys) |
| `SECRET_KEY` | a long random string (keeps people signed in across restarts) |
| `TEACHER_EMAILS` | comma-separated; e.g. `jami.saffioti@gmail.com` |
| `ALLOWED_EMAILS` | comma-separated student/demo Google accounts; e.g. `novanoros@gmail.com` |
| `EXECUTOR` | `judge0` |
| `JUDGE0_URL` | `https://judge0-ce.p.rapidapi.com` (or your own Judge0 server) |
| `JUDGE0_KEY` | your RapidAPI key (or your server's auth token) |
| `JUDGE0_HOST` | `judge0-ce.p.rapidapi.com` (leave unset for your own server) |
| `TIMEZONE` | optional; default `America/New_York` |

Gmail addresses match with or without dots, and in any case.

### Deploy steps (Render)

1. **Disk:** service → Disks → Add disk, mount path `/var/data`, 1 GB. (Disks need a
   paid instance type.) Then set `DB_PATH=/var/data/tutorbot.db`.
2. **Judge0:** subscribe to Judge0 CE on RapidAPI, copy the key, set the four
   `EXECUTOR`/`JUDGE0_*` variables.
3. Set `SECRET_KEY`, `TEACHER_EMAILS`, `ALLOWED_EMAILS`.
4. Deploy. The new tables are created on start; existing users and chats are kept.
5. Optional, for demos: in the Render Shell run `python scripts/seed_demo.py` to add
   three fake students with scored attempts (`--clear` removes them).
6. Check: sign in as a student, finish a task, then sign in as the teacher and open
   the student. Redeploy once and confirm the attempt is still there.

### Tests

```bash
python -m pytest tests slop_detector/tests
```

Covers the scorer on every task (strong and weak submissions, traps), the Judge0
path against a fake Judge0 server, and the app loop (submit → saved → teacher view).

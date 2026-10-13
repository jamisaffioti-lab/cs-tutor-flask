# Slop-Detector — C2 scoring harness (build kickoff)

The MVP slice of the AP CSP Applied Competency Credential: **Competency 2,
Critical Code & Output Analysis.** A student is shown AI-generated code with
planted defects, flags and fixes them, and this harness scores the submission
against the five-dimension C2 rubric — deterministically, no LLM in the
critical path.

This is the runnable seed. It works offline today; you extend it, you don't
start from a blank repo.

## Run it

### 1. The scorer alone (no install, standard library only)

```bash
python tests/test_scoring.py      # end-to-end proof: prints a scorecard, exits green
python score.py sample_pass       # score one submission -> JSON
python score.py sample_fail
```

Expected: `sample_pass` scores L4 on all five dimensions and passes;
`sample_fail` fails (flagged the trap, missed the edge case).

### 2. The full student loop in a browser (localhost — no hosting)

```bash
pip install flask
python app.py
# open http://127.0.0.1:5000
```

You'll see the buggy code in a Monaco editor. Flag defects on the right (line
number + type + why), edit the code to fix it, and hit **Run & score** — the
scorecard comes back from the same harness. This is the whole product running
on your machine; deploy comes later and changes nothing about this loop.

The browser only ever receives a student-safe view of the task (prompt + buggy
code). Defect locations, expected outputs, and the reference solution stay
server-side in `app.py` — students can't read the answer key from the page.

## What's here

```
tasks/csp-slop-01.json      task 01: functional bug, edge case, hallucination, + trap
tasks/csp-slop-02.json      task 02: intent gap (runs clean, wrong problem) + a "correct code" trap
submissions/                example submissions (a strong + a weak one per task)
harness/executor.py         execute(code,...) behind one interface; Local default, Judge0 stub
harness/loader.py           load tasks/submissions; map flagged lines -> defects
harness/scorer.py           the five C2 dimensions -> levels 1-4; pass = >=3 on all five
app.py                      local Flask app: serves the front end + /api/task + /api/submit
web/index.html              the Monaco student page (flag, fix, submit, see the scorecard)
score.py                    CLI: score a submission
tests/test_scoring.py       runnable proof of the whole loop
docs/                       the source spec: Task 01 + the harness contract
```

## The loop

```
task JSON -> (Monaco shows buggy_code) -> student flags + edits fix
   -> executor runs the fix against hidden tests -> scorer applies the rubric -> score JSON
```

`executor.py` is the only file that knows about the execution backend. It ships
with `LocalExecutor` (a subprocess — fine for authoring and tests, NOT a
security sandbox). Set `EXECUTOR=judge0` and implement `Judge0Executor` before
running untrusted student code at scale; nothing else changes.

## The five dimensions (scorer.py)

| Dimension | How it's scored | LLM needed? |
|---|---|---|
| Detection | flagged lines vs real-defect lines, minus false positives | no |
| Diagnosis | claimed_type vs defect.type on matched flags | label: no · explanation: later |
| Correction | fraction of hidden tests the fix passes | no |
| Verification | originally-failing tests now pass, no regressions | no |
| Calibration | trap left unflagged AND its clause preserved | no |

Only Diagnosis's *explanation* quality wants an LLM grader — a documented hook
in `scorer.py`, deliberately outside the core loop.

## What to build next

1. ~~**The front end**~~ — done: `app.py` + `web/index.html`. Polish the flag UX
   (e.g. click a line in Monaco to start a flag) when you want.
2. ~~**Task 02**~~ — done: the *intent gap* type (`csp-slop-02.json`), with a
   trap that's *correct* code even though the same construct was a bug in Task 01.
   Keep growing the bank the same way — drop a JSON in `tasks/` and it works.
3. **Diagnosis LLM grader** — score `flag.explanation` against the answer key;
   blend into `_diagnosis()`.
4. **Judge0 backend** — implement `Judge0Executor` for sandboxed execution.
5. **Persistence** — store submissions and scores keyed by (task_id, student_id).
6. **Deploy** — GitHub -> Render (the bc-course pattern) + a Judge0 service.

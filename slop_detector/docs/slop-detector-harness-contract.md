# Slop-Detector — Harness Contract (v1)

The blueprint for step 4 (scoring) of the C2 loop. Defines how a task is stored, what a student submits, how code runs, and how a submission becomes a rubric score. Grounded in `csp-slop-01` (Task 01).

---

## The loop, as data

```
task JSON ──► render buggy_code in Monaco
                     │
        student flags defects + edits fix
                     │
          submission JSON ──► execute(edited_code) via Judge0 ──► test results
                     │                                                │
                     └──────────────► score() ◄───────────────────────┘
                                          │
                                    score JSON (5 dims + pass/fail)
```

---

## 1. Task schema

```json
{
  "task_id": "csp-slop-01",
  "competency": "C2",
  "language": "python",
  "entrypoint": "class_average",
  "prompt": "Return the average of passing scores (>= 60) in a 0–100 list, rounded to 1 decimal; return 0 if none pass.",
  "buggy_code": "def class_average(scores):\n    passing = []\n    for i in range(1, len(scores)):\n        if scores[i] >= 60 and scores[i] <= 100:\n            passing.append(scores[i])\n    average = sum(passing) / len(passing)\n    return round(average, 1, ROUND_HALF_UP)\n",
  "defects": [
    {"id":"d1","type":"functional_bug","locator":"range(1, len(scores))","is_trap":false},
    {"id":"d2","type":"edge_case","locator":"sum(passing) / len(passing)","is_trap":false},
    {"id":"d3","type":"hallucination","locator":"round(average, 1, ROUND_HALF_UP)","is_trap":false},
    {"id":"d4","type":"trap_correct","locator":"and scores[i] <= 100","is_trap":true}
  ],
  "hidden_tests": [
    {"input":[[90,80,55,40]],"expected":85.0,"catches":["d1"]},
    {"input":[[60,70,100]],"expected":76.7,"catches":["d1"]},
    {"input":[[50,40,30]],"expected":0,"catches":["d2"]},
    {"input":[[100]],"expected":100.0,"catches":["d1","d2"]},
    {"input":[[]],"expected":0,"catches":["d2"]}
  ],
  "reference_solution": "def class_average(scores):\n    passing = [s for s in scores if s >= 60 and s <= 100]\n    if not passing:\n        return 0\n    return round(sum(passing)/len(passing), 1)\n",
  "rubric_id": "c2-slop-detector-v1"
}
```

Tasks are static, versioned JSON. `defect.type` is an enum: `functional_bug | edge_case | hallucination | intent_gap | trap_correct`. Exactly one defect per task should be `is_trap:true`.

## 2. Submission schema

```json
{
  "task_id": "csp-slop-01",
  "student_id": "stu_123",
  "flags": [
    {"line": 3, "claimed_type": "functional_bug", "explanation": "skips the first score"},
    {"line": 6, "claimed_type": "hallucination", "explanation": "round has no 3rd arg"}
  ],
  "edited_code": "def class_average(scores): ...",
  "submitted_at": "2026-09-21T18:00:00Z"
}
```

The harness maps each `flag.line` to the defect whose `locator` sits on that line (or to `none` — a flag on a clean line is a false positive, which matters for calibration).

## 3. Execution contract

Compose `edited_code + RUNNER`, send to the executor, parse the tagged JSON line from stdout. Runner is templated per language; entrypoint comes from the task.

```python
# RUNNER (python) — TESTS and ENTRYPOINT injected by the harness
import json
results = []
for t in TESTS:
    try:
        got = ENTRYPOINT(*t["input"])
        results.append({"expected": t["expected"], "got": got, "pass": got == t["expected"]})
    except Exception as e:
        results.append({"expected": t["expected"], "error": repr(e), "pass": False})
print("RESULT_JSON:" + json.dumps(results))
```

Isolate the executor behind one interface — `execute(code, language) -> [test_result]` — so Judge0 is the only thing that knows about Judge0. Swapping to a self-hosted Judge0 (or another sandbox) later becomes a config change, not a rewrite.

## 4. Scoring contract

| Dimension | Signal | Rule | Grader |
|---|---|---|---|
| Detection | flagged lines vs non-trap defect locators | coverage of real defects, minus false positives | **auto** (line match) + assisted (explanation) |
| Diagnosis | `claimed_type` vs `defect.type` on correctly-located flags | exact-match ratio; depth of explanation | auto (label) + **LLM-assisted** (explanation) |
| Correction | `edited_code` vs `hidden_tests` | fraction of tests passing | **auto / deterministic** |
| Verification | the tests the *buggy* code failed, re-run on the fix | do the originally-failing (edge) tests now pass, no regressions | **auto / deterministic** |
| Calibration | trap handling | trap line NOT flagged as a defect AND its clause still present in `edited_code` | **auto** (flag + presence check) |

Each signal maps to a level 1–4 via thresholds; **pass = level ≥ 3 on all five.** Store per-dimension level, the raw signals, and the executor output for review/appeal.

## 5. Score output schema

```json
{
  "task_id": "csp-slop-01",
  "student_id": "stu_123",
  "dimensions": {"detection":4,"diagnosis":3,"correction":4,"verification":3,"calibration":4},
  "passed": true,
  "evidence": {"tests": [ ... ], "flags_matched": ["d1","d3"], "trap_flagged": false}
}
```

---

## Build notes

- **Why C2 is the right MVP:** Correction, Verification, and Calibration are fully deterministic, and Detection is mostly line-matching — so the flagship auto-scores with no LLM in the critical path. Only the *explanation* quality (Diagnosis) needs an LLM grader, and that can be a plug-in scored against the answer key, added after the core loop works.
- **LLM grader (later):** for C1 and C3 (design log, impact analysis) the artifact is prose, so scoring is LLM-assisted-or-human against the rubric. Same `score()` output shape; different grader behind it. Build C2's deterministic path first; keep `grader` swappable per dimension.
- **Storage:** tasks = versioned JSON files; `rubric_id` points at the rubric; submissions and scores are rows keyed by (task_id, student_id).

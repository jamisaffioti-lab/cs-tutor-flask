# Slop-Detector — Task 01 (AP CSP, Python)

Competency 2: Critical Code & Output Analysis. First task instance — build the MVP harness against this.

---

## A. What the student sees

> An AI assistant was asked to write `class_average(scores)`:
>
> Given a list of integer test scores (each 0–100), return the **average of the passing scores** (60 or above), rounded to **one decimal place**. If no scores are passing, return **0**.
>
> Below is the AI's output. Find and fix what's wrong — and be careful not to "fix" what isn't. For each issue you find: say what type it is, why it fails, and correct it.

```python
def class_average(scores):
    passing = []
    for i in range(1, len(scores)):
        if scores[i] >= 60 and scores[i] <= 100:
            passing.append(scores[i])
    average = sum(passing) / len(passing)
    return round(average, 1, ROUND_HALF_UP)
```

---

## B. Answer key — planted defects (do not show the student)

| # | Line | Type | Why it fails | Fix |
|---|---|---|---|---|
| 1 | `for i in range(1, len(scores))` | **Functional bug** (off-by-one) | Starts at index 1, silently skips the first score | `range(0, len(scores))`, or iterate directly: `for s in scores` |
| 2 | `average = sum(passing) / len(passing)` | **Silent edge-case failure** | `ZeroDivisionError` when no scores pass; spec says return `0` | Guard first: `if not passing: return 0` |
| 3 | `round(average, 1, ROUND_HALF_UP)` | **Hallucination** | `round()` takes no 3rd argument and `ROUND_HALF_UP` isn't defined/imported — invented API. This is a hard error, so the code won't even run until it's fixed | `round(average, 1)` |
| 4 | `and scores[i] <= 100` | **TRAP — correct, not a defect** | Redundant given scores are 0–100, but harmless and defensible. It is **not** a bug | Leave it (noting it's redundant is fine). "Fixing"/removing it as if it were a defect = a calibration miss |

Defect #3 is a fatal error, so the student must clear it before the code runs; the hidden tests below then expose #1 and #2. (Task 02 should rotate in the fifth type — an *intent gap*: code that runs cleanly but solves a subtly different problem.)

---

## C. Hidden test cases (Judge0 runs the student's fix against these)

| Input | Expected | Catches |
|---|---|---|
| `[90, 80, 55, 40]` | `85.0` | off-by-one (buggy skips 90 → 80.0) |
| `[60, 70, 100]` | `76.7` | off-by-one (buggy skips 60 → 85.0) + rounding |
| `[50, 40, 30]` | `0` | edge case (buggy raises ZeroDivisionError) |
| `[100]` | `100.0` | off-by-one on single element (buggy → empty → crash) |
| `[]` | `0` | empty input |

All five must pass for the correction to count.

---

## D. Reference solution

```python
def class_average(scores):
    passing = [s for s in scores if s >= 60 and s <= 100]
    if not passing:
        return 0
    return round(sum(passing) / len(passing), 1)
```

---

## E. How a submission maps to the C2 rubric

- **Detection** — found #1, #2, #3, and did *not* flag #4.
- **Diagnosis** — correctly named each type (bug / edge case / hallucination) and explained the failure.
- **Correction** — fixes make all hidden tests pass.
- **Verification** — ran the empty-list / no-passing case that originally broke, and confirmed no regression.
- **Judgment calibration** — left the trap (#4) intact. Removing it or calling it a bug caps this dimension.

Proficient across all five = the task is passed.

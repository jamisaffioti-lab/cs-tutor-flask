# Slop-Detector — Task 02 (AP CSP, Python)

Competency 2: Critical Code & Output Analysis. Flagship defect: the **intent gap** — code that runs cleanly but solves a subtly different problem. This is the fifth defect type, the one Task 01 deliberately left out.

---

## A. What the student sees

> An AI assistant was asked to write `warmer_avg(temps)`:
>
> Given a list of integer daily temperatures, return the **average of the temperatures on days that were warmer than the day BEFORE**, rounded to one decimal. The first day never qualifies. If no day qualifies, return **0**.
>
> Below is the AI's output. Find and fix what's wrong — and be careful not to "fix" what isn't.

```python
def warmer_avg(temps):
    warmer = []
    for i in range(1, len(temps)):
        if temps[i] > temps[0]:
            warmer.append(temps[i])
    return round(sum(warmer) / len(warmer), 1)
```

---

## B. Answer key — planted defects (do not show the student)

| # | Line | Type | Why it fails | Fix |
|---|---|---|---|---|
| 1 | `if temps[i] > temps[0]` | **Intent gap** | Runs perfectly and looks right, but compares each day to `temps[0]` (the *first* day) instead of `temps[i-1]` (the day *before*). It solves a different problem than the spec asked for — no error, wrong answer. | `if temps[i] > temps[i-1]` |
| 2 | `sum(warmer) / len(warmer)` | **Silent edge-case failure** | `ZeroDivisionError` when no day qualifies; spec says return `0` | Guard first: `if not warmer: return 0` |
| 3 | `for i in range(1, len(temps))` | **TRAP — correct, not a defect** | Starting at index 1 is *right here*: the first day can never be "warmer than the day before," so it must be skipped. **Note the cross-task lesson:** in Task 01 a `range(1, …)` was an off-by-one *bug*; here the identical-looking construct is *correct*. Understanding beats pattern-matching. | Leave it. Changing it to `range(0, …)` is a calibration miss. |

The intent gap is the point of this task: because the buggy code runs without error, the only way to catch it is to reason about *intent* and test boundary cases — you can't wait for a crash.

---

## C. Hidden test cases

| Input | Expected | Catches |
|---|---|---|
| `[50, 60, 55, 70]` | `65.0` | intent gap (buggy → 61.7) |
| `[40, 50, 45, 48]` | `49.0` | intent gap (buggy → 47.7) |
| `[30, 40, 50, 60]` | `50.0` | control — monotonic case both get right; guards against regression |
| `[80, 70, 60]` | `0` | edge case (buggy raises ZeroDivisionError) |
| `[]` | `0` | edge case / empty |
| `[45]` | `0` | edge case / single day |

---

## D. Reference solution

```python
def warmer_avg(temps):
    warmer = [temps[i] for i in range(1, len(temps)) if temps[i] > temps[i-1]]
    if not warmer:
        return 0
    return round(sum(warmer) / len(warmer), 1)
```

---

## E. Why this task matters

Task 01's defects all announced themselves eventually (a crash, a wrong number a test catches). The intent gap is more dangerous: the program is *confidently, plausibly wrong*. Certifying that a student catches it — and doesn't panic-"fix" the correct `range(1, …)` — is exactly the calibrated judgment the credential attests.

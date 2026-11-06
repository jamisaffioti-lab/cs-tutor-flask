"""End-to-end proof of the C2 deterministic scoring path against Task 01.

Runs two ways:
  python tests/test_scoring.py     -> prints a readable scorecard, exits non-zero on failure
  pytest                           -> the test_* functions below
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from harness.loader import load_task, load_submission          # noqa: E402
from harness.scorer import score                               # noqa: E402


def test_correct_submission_passes():
    task = load_task("csp-slop-01")
    result = score(task, load_submission("sample_pass"))
    assert result.dimensions == {
        "detection": 4, "diagnosis": 4, "correction": 4,
        "verification": 4, "calibration": 4,
    }, result.dimensions
    assert result.passed is True


def test_weak_submission_fails():
    task = load_task("csp-slop-01")
    result = score(task, load_submission("sample_fail"))
    # missed the edge case, flagged the trap, removed the trap clause
    assert result.passed is False
    assert result.dimensions["calibration"] == 1
    assert result.dimensions["correction"] < 3


def test_intent_gap_correct_submission_passes():
    task = load_task("csp-slop-02")
    result = score(task, load_submission("sample_pass_02"))
    assert result.passed is True
    assert all(v == 4 for v in result.dimensions.values()), result.dimensions


def test_intent_gap_trap_is_correct_code():
    # Task 02's trap is a range(1, ...) that is CORRECT here, even though the
    # same construct was a bug in Task 01. "Fixing" it must cap calibration.
    task = load_task("csp-slop-02")
    result = score(task, load_submission("sample_fail_02"))
    assert result.passed is False
    assert result.dimensions["calibration"] == 1
    assert result.dimensions["detection"] < 3   # missed the intent gap


# --- tasks 03-05 (from the v1 task bank, each with a trap) -----------------

def _run(name):
    submission = load_submission(name)
    return score(load_task(submission["task_id"]), submission)


def test_bank_tasks_reference_solutions_pass():
    for name in ("sample_pass_03", "sample_pass_04", "sample_pass_04b", "sample_pass_05"):
        result = _run(name)
        assert result.passed is True, (name, result.dimensions)
        assert all(v == 4 for v in result.dimensions.values()), (name, result.dimensions)


def test_bank_tasks_weak_submissions_fail():
    for name in ("sample_fail_03", "sample_fail_04", "sample_fail_05"):
        result = _run(name)
        assert result.passed is False, (name, result.dimensions)


def test_trap_flagged_caps_calibration():
    # 03: "fixing" the correct > into >= ; 04: calling [::-1] made-up and removing it
    assert _run("sample_fail_03").dimensions["calibration"] == 1
    assert _run("sample_fail_04").dimensions["calibration"] == 1


def test_every_task_buggy_code_fails_and_reference_passes():
    from harness.executor import get_executor
    ex = get_executor()
    for tid in ("csp-slop-01", "csp-slop-02", "csp-slop-03", "csp-slop-04", "csp-slop-05"):
        t = load_task(tid)
        buggy = ex.execute(t["buggy_code"], t["language"], t["entrypoint"], t["hidden_tests"])
        ref = ex.execute(t["reference_solution"], t["language"], t["entrypoint"], t["hidden_tests"])
        assert not all(r.passed for r in buggy), tid
        assert all(r.passed for r in ref), (tid, [r.as_dict() for r in ref])


def _scorecard(name: str, result) -> None:
    verdict = "PASS" if result.passed else "FAIL"
    print(f"\n  {name}  ->  {verdict}")
    for dim, lvl in result.dimensions.items():
        mark = "ok " if lvl >= 3 else "LOW"
        print(f"    {mark} {dim:<12} L{lvl}")
    print(f"    tests: {result.evidence['tests_passed']}  "
          f"trap_flagged={result.evidence['trap_flagged']}  "
          f"regressions={result.evidence['regressions']}")


if __name__ == "__main__":
    ok = True
    # (submission name, should it pass)
    cases = [
        ("sample_pass", True), ("sample_fail", False),
        ("sample_pass_02", True), ("sample_fail_02", False),
        ("sample_pass_03", True), ("sample_fail_03", False),
        ("sample_pass_04", True), ("sample_fail_04", False),
        ("sample_pass_05", True), ("sample_fail_05", False),
    ]
    for name, expect_pass in cases:
        submission = load_submission(name)
        result = score(load_task(submission["task_id"]), submission)
        _scorecard(name, result)
        if result.passed != expect_pass:
            ok = False
            print(f"    !! expected passed={expect_pass}, got {result.passed}")
    print("\n" + ("GREEN — scoring loop works end to end." if ok else "RED — see above."))
    sys.exit(0 if ok else 1)

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

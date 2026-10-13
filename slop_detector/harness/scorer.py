"""Score a submission against a task on the five C2 rubric dimensions.

Deterministic path only (the reason C2 is the MVP): Detection, Correction,
Verification and Calibration need no LLM. Diagnosis is scored here on the
label (claimed_type vs defect.type); the *explanation* quality is the one
LLM-assisted piece and is left as a documented hook, not in the critical path.

Every dimension returns a level 1-4. pass = level >= 3 on all five.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .executor import Executor, get_executor
from .loader import defect_line_map


def _norm(s: str) -> str:
    return s.replace(" ", "")


@dataclass
class Score:
    task_id: str
    student_id: str
    dimensions: dict[str, int] = field(default_factory=dict)
    passed: bool = False
    evidence: dict[str, Any] = field(default_factory=dict)


def score(task: dict, submission: dict, executor: Executor | None = None) -> Score:
    executor = executor or get_executor()
    line_map = defect_line_map(task)
    real_defects = [d for d in task["defects"] if not d["is_trap"]]
    trap = next((d for d in task["defects"] if d["is_trap"]), None)
    n_real = len(real_defects)

    # --- classify each flag against the defect on its line -------------------
    matched: dict[str, dict] = {}   # defect_id -> the flag that matched it
    false_positives = 0             # flag on a clean line
    trap_flagged = False
    for flag in submission.get("flags", []):
        defect = line_map.get(flag.get("line"))
        if defect is None:
            false_positives += 1
        elif defect["is_trap"]:
            trap_flagged = True     # student called the correct code a defect
        else:
            matched[defect["id"]] = flag

    matched_real = len(matched)
    coverage = matched_real / n_real if n_real else 1.0

    # --- run the fix once; reuse results across dimensions -------------------
    fixed = executor.execute(
        submission["edited_code"], task["language"],
        task["entrypoint"], task["hidden_tests"])
    buggy = executor.execute(
        task["buggy_code"], task["language"],
        task["entrypoint"], task["hidden_tests"])

    n_tests = len(task["hidden_tests"])
    passed_fixed = sum(1 for r in fixed if r.passed)
    pass_ratio = passed_fixed / n_tests if n_tests else 0.0

    # verification: the tests the buggy code failed should now pass; nothing
    # that passed before should regress.
    originally_failing = [i for i, r in enumerate(buggy) if not r.passed]
    now_fixed = sum(1 for i in originally_failing if fixed[i].passed)
    regressions = sum(1 for i, r in enumerate(buggy) if r.passed and not fixed[i].passed)
    fixed_ratio = now_fixed / len(originally_failing) if originally_failing else 1.0

    # calibration: trap left unflagged AND its clause preserved in the fix
    sig = trap.get("signature", trap["locator"]) if trap else ""
    trap_present = _norm(sig) in _norm(submission["edited_code"]) if trap else True

    # --- levels --------------------------------------------------------------
    dims = {
        "detection": _detection(coverage, false_positives),
        "diagnosis": _diagnosis(task, matched),
        "correction": _correction(pass_ratio),
        "verification": _verification(fixed_ratio, regressions),
        "calibration": _calibration(trap_flagged, trap_present),
    }
    result = Score(
        task_id=task["task_id"],
        student_id=submission.get("student_id", "unknown"),
        dimensions=dims,
        passed=all(v >= 3 for v in dims.values()),
        evidence={
            "flags_matched": sorted(matched),
            "false_positives": false_positives,
            "trap_flagged": trap_flagged,
            "trap_present": trap_present,
            "tests_passed": f"{passed_fixed}/{n_tests}",
            "regressions": regressions,
            "tests": [r.as_dict() for r in fixed],
        },
    )
    return result


def _detection(coverage: float, false_positives: int) -> int:
    if coverage >= 1.0 and false_positives == 0:
        return 4
    if coverage >= 2 / 3 and false_positives <= 1:
        return 3
    if coverage >= 1 / 3:
        return 2
    return 1


def _diagnosis(task: dict, matched: dict[str, dict]) -> int:
    if not matched:
        return 1
    by_id = {d["id"]: d for d in task["defects"]}
    correct = sum(1 for did, flag in matched.items()
                  if flag.get("claimed_type") == by_id[did]["type"])
    ratio = correct / len(matched)
    n_real = sum(1 for d in task["defects"] if not d["is_trap"])
    if ratio == 1.0 and len(matched) >= n_real:
        return 4
    if ratio == 1.0 and len(matched) >= 2:
        return 3
    if ratio >= 0.5:
        return 2
    return 1
    # HOOK: explanation quality (flag.explanation vs answer key) is the
    # LLM-assisted signal; blend it in here once the core loop is trusted.


def _correction(pass_ratio: float) -> int:
    if pass_ratio >= 1.0:
        return 4
    if pass_ratio >= 0.8:
        return 3
    if pass_ratio >= 0.5:
        return 2
    return 1


def _verification(fixed_ratio: float, regressions: int) -> int:
    if regressions > 0:
        return 2
    if fixed_ratio >= 1.0:
        return 4
    if fixed_ratio >= 0.5:
        return 3
    return 2


def _calibration(trap_flagged: bool, trap_present: bool) -> int:
    # A single trap is binary: get it fully right or you cap out below passing,
    # by design ("removing it or calling it a bug caps this dimension").
    if not trap_flagged and trap_present:
        return 4
    if trap_flagged and not trap_present:
        return 1
    return 2

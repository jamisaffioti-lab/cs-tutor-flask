"""Score any submission against its task. Usage:

    python score.py sample_pass
    python score.py sample_fail

Reads tasks/<task_id>.json (from the submission) and submissions/<name>.json.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from harness.loader import load_task, load_submission
from harness.scorer import score


def main(name: str) -> None:
    submission = load_submission(name)
    task = load_task(submission["task_id"])
    result = score(task, submission)
    print(json.dumps({
        "task_id": result.task_id,
        "student_id": result.student_id,
        "dimensions": result.dimensions,
        "passed": result.passed,
        "evidence": {k: v for k, v in result.evidence.items() if k != "tests"},
    }, indent=2))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: python score.py <submission-name>")
        sys.exit(2)
    main(sys.argv[1])

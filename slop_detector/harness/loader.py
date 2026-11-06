"""Load tasks and submissions from versioned JSON."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TASKS_DIR = ROOT / "tasks"
SUBMISSIONS_DIR = ROOT / "submissions"


def load_task(task_id: str) -> dict:
    return json.loads((TASKS_DIR / f"{task_id}.json").read_text())


def load_submission(name: str) -> dict:
    return json.loads((SUBMISSIONS_DIR / f"{name}.json").read_text())


def buggy_lines(task: dict) -> dict[int, str]:
    """1-indexed line number -> line text for the task's buggy_code."""
    return {i: line for i, line in enumerate(task["buggy_code"].splitlines(), start=1)}


def defect_line_map(task: dict) -> dict[int, dict]:
    """1-indexed line number -> the defect whose locator sits on that line."""
    lines = buggy_lines(task)
    out: dict[int, dict] = {}
    for defect in task["defects"]:
        # A defect can live on more than one line (e.g. a comment that lies AND
        # the line that should have done the work). `locator` is the main line;
        # optional `also_on` lists other lines that count as the same defect.
        for loc in [defect["locator"], *defect.get("also_on", [])]:
            needle = loc.replace(" ", "")
            for n, text in lines.items():
                if needle in text.replace(" ", ""):
                    out[n] = defect
                    break
    return out

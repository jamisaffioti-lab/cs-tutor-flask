"""Code execution — isolated behind one interface.

`execute(code, language, entrypoint, tests) -> list[TestResult]`

Judge0 (or any sandbox) is the only thing that should ever know about Judge0.
Everything else calls `get_executor()` and depends on the interface, not the
backend. Swapping to a self-hosted Judge0 later is a config change (the
EXECUTOR env var), not a rewrite.

Default backend is LocalExecutor (stdlib subprocess) so the whole loop runs
green offline with no API key. That is fine for authoring and unit tests; move
to Judge0Executor before running untrusted student code at scale, because a
local subprocess is NOT a security sandbox.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass, asdict
from typing import Any


@dataclass
class TestResult:
    input: Any
    expected: Any
    got: Any = None
    passed: bool = False
    error: str | None = None

    def as_dict(self) -> dict:
        return asdict(self)


# The runner is composed with the student's code and executed. It prints one
# tagged JSON line the harness parses. Templated per language; Python here.
_PY_RUNNER = """

import json as __json
__TESTS = {tests_json}
__results = []
for __t in __TESTS:
    try:
        __got = {entrypoint}(*__t["input"])
        __results.append({{"input": __t["input"], "expected": __t["expected"],
                           "got": __got, "pass": __got == __t["expected"]}})
    except Exception as __e:
        __results.append({{"input": __t["input"], "expected": __t["expected"],
                           "got": None, "error": repr(__e), "pass": False}})
print("RESULT_JSON:" + __json.dumps(__results))
"""


class Executor:
    """Interface every backend implements."""

    def execute(self, code: str, language: str, entrypoint: str,
                tests: list[dict]) -> list[TestResult]:
        raise NotImplementedError


def _limit_child():  # pragma: no cover - runs in the child process
    """Best-effort caps for student code run on the server (Linux only).

    NOT a sandbox: it blocks runaway CPU, memory, file writes and fork bombs,
    but student code can still read files the app can read. Fine for a
    sign-in-gated pilot; switch to Judge0 before opening it to students.
    """
    try:
        import resource
        resource.setrlimit(resource.RLIMIT_CPU, (5, 5))
        resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024,) * 2)
        resource.setrlimit(resource.RLIMIT_FSIZE, (1024 * 1024,) * 2)
        resource.setrlimit(resource.RLIMIT_NPROC, (64, 64))
    except Exception:
        pass


class LocalExecutor(Executor):
    """Runs the composed program in a local subprocess. Default backend."""

    def __init__(self, timeout_s: float = 5.0):
        self.timeout_s = timeout_s

    def execute(self, code: str, language: str, entrypoint: str,
                tests: list[dict]) -> list[TestResult]:
        if language != "python":
            raise ValueError(f"LocalExecutor only handles python, got {language!r}")
        program = code + _PY_RUNNER.format(
            tests_json=json.dumps(tests), entrypoint=entrypoint
        )
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as fh:
            fh.write(program)
            path = fh.name
        try:
            proc = subprocess.run(
                [sys.executable, path],
                capture_output=True, text=True, timeout=self.timeout_s,
                preexec_fn=_limit_child if os.name == "posix" else None,
                env={"PATH": os.environ.get("PATH", ""), "PYTHONIOENCODING": "utf-8"},
                cwd=tempfile.gettempdir(),
            )
        except subprocess.TimeoutExpired:
            return [TestResult(t["input"], t["expected"], error="timeout") for t in tests]
        finally:
            os.unlink(path)

        for line in proc.stdout.splitlines():
            if line.startswith("RESULT_JSON:"):
                raw = json.loads(line[len("RESULT_JSON:"):])
                return [
                    TestResult(r["input"], r["expected"], r.get("got"),
                               r.get("pass", False), r.get("error"))
                    for r in raw
                ]
        # No tagged line => the program failed to run at all (e.g. a
        # hallucinated API that raises at import/parse). Every test fails.
        err = (proc.stderr.strip().splitlines() or ["did not run"])[-1]
        return [TestResult(t["input"], t["expected"], error=err) for t in tests]


class Judge0Executor(Executor):
    """Sandboxed backend. Stub — wire to a Judge0 instance before scaled use.

    Set EXECUTOR=judge0 and JUDGE0_URL/JUDGE0_KEY, then implement submit here.
    Kept behind the same interface so nothing else changes when it lands.
    """

    def __init__(self):
        self.url = os.environ.get("JUDGE0_URL")
        self.key = os.environ.get("JUDGE0_KEY")

    def execute(self, code: str, language: str, entrypoint: str,
                tests: list[dict]) -> list[TestResult]:
        raise NotImplementedError(
            "Judge0Executor is a stub. Implement the submit/poll calls against "
            "JUDGE0_URL, or run with EXECUTOR=local (the default) for now."
        )


def get_executor() -> Executor:
    """Pick the backend from the EXECUTOR env var. Defaults to local."""
    choice = os.environ.get("EXECUTOR", "local").lower()
    if choice == "judge0":
        return Judge0Executor()
    return LocalExecutor()

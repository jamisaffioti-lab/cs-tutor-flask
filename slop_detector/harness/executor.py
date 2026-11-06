"""Code execution — isolated behind one interface.

`execute(code, language, entrypoint, tests) -> list[TestResult]`

Judge0 (or any sandbox) is the only thing that should ever know about Judge0.
Everything else calls `get_executor()` and depends on the interface, not the
backend. Swapping to a self-hosted Judge0 later is a config change (the
EXECUTOR env var), not a rewrite.

Default backend is LocalExecutor (stdlib subprocess) so the whole loop runs
green offline with no API key. That is fine for authoring and unit tests. On the
live site set EXECUTOR=judge0: a local subprocess is NOT a security sandbox.
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
__TESTS = __json.loads({tests_json})
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


def _compose(code: str, entrypoint: str, tests: list[dict]) -> str:
    return code + _PY_RUNNER.format(
        tests_json=repr(json.dumps(tests)), entrypoint=entrypoint)


def _parse(stdout: str, stderr: str, tests: list[dict]) -> list[TestResult]:
    for line in (stdout or "").splitlines():
        if line.startswith("RESULT_JSON:"):
            raw = json.loads(line[len("RESULT_JSON:"):])
            return [
                TestResult(r["input"], r["expected"], r.get("got"),
                           r.get("pass", False), r.get("error"))
                for r in raw
            ]
    # No tagged line => the program failed to run at all (e.g. a
    # hallucinated API that raises at import/parse). Every test fails.
    err = ((stderr or "").strip().splitlines() or ["did not run"])[-1]
    return [TestResult(t["input"], t["expected"], error=err) for t in tests]


class LocalExecutor(Executor):
    """Runs the composed program in a local subprocess. Default backend."""

    def __init__(self, timeout_s: float = 5.0):
        self.timeout_s = timeout_s

    def execute(self, code: str, language: str, entrypoint: str,
                tests: list[dict]) -> list[TestResult]:
        if language != "python":
            raise ValueError(f"LocalExecutor only handles python, got {language!r}")
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as fh:
            fh.write(_compose(code, entrypoint, tests))
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
        return _parse(proc.stdout, proc.stderr, tests)


class SandboxUnavailable(RuntimeError):
    """Judge0 couldn't be reached or answered badly. Not the student's fault,
    so it is raised (and shown as "try again"), never scored as a failure."""


class Judge0Executor(Executor):
    """Runs student code in a Judge0 sandbox (hosted on RapidAPI, or your own).

    Env:
      JUDGE0_URL        e.g. https://judge0-ce.p.rapidapi.com  (or your server)
      JUDGE0_KEY        the API key
      JUDGE0_HOST       set for RapidAPI (e.g. judge0-ce.p.rapidapi.com); when
                        set, RapidAPI headers are used, otherwise X-Auth-Token
      JUDGE0_PYTHON_ID  Judge0 language id for Python 3 (default 71)

    One Judge0 submission runs all of a task's tests (the runner loops them),
    so a student's attempt costs one call. The key never reaches the browser.
    """

    # Judge0 status ids: 1 In Queue, 2 Processing, 3 Accepted, 5 Time Limit
    # Exceeded, 6 Compilation Error, 7-12 runtime errors, 13 Internal, 14 Exec format
    _DONE_AFTER = 2

    def __init__(self, poll_s: float = 0.5, max_wait_s: float = 20.0):
        self.url = (os.environ.get("JUDGE0_URL") or "").rstrip("/")
        self.key = os.environ.get("JUDGE0_KEY", "")
        self.host = os.environ.get("JUDGE0_HOST", "")
        self.language_id = int(os.environ.get("JUDGE0_PYTHON_ID", "71"))
        self.poll_s, self.max_wait_s = poll_s, max_wait_s
        if not self.url:
            raise SandboxUnavailable("EXECUTOR=judge0 but JUDGE0_URL is not set")

    def _headers(self) -> dict:
        h = {"Content-Type": "application/json"}
        if self.host:
            h["X-RapidAPI-Key"] = self.key
            h["X-RapidAPI-Host"] = self.host
        elif self.key:
            h["X-Auth-Token"] = self.key
        return h

    def _call(self, method: str, path: str, body: dict | None = None) -> dict:
        import urllib.request
        import urllib.error
        req = urllib.request.Request(
            self.url + path, method=method, headers=self._headers(),
            data=json.dumps(body).encode() if body is not None else None)
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode())
        except (urllib.error.URLError, TimeoutError, ValueError) as e:
            raise SandboxUnavailable(f"Judge0 {method} {path}: {e}") from e

    def execute(self, code: str, language: str, entrypoint: str,
                tests: list[dict]) -> list[TestResult]:
        import base64
        import time
        if language != "python":
            raise ValueError(f"Judge0Executor only wired for python, got {language!r}")
        b64 = lambda t: base64.b64encode(t.encode()).decode()  # noqa: E731
        sub = self._call("POST", "/submissions?base64_encoded=true&wait=false", {
            "language_id": self.language_id,
            "source_code": b64(_compose(code, entrypoint, tests)),
            "cpu_time_limit": 5, "wall_time_limit": 10,
            "memory_limit": 128000, "enable_network": False,
        })
        token = sub.get("token")
        if not token:
            raise SandboxUnavailable(f"Judge0 gave no token: {sub}")
        deadline = time.monotonic() + self.max_wait_s
        while True:
            res = self._call("GET", f"/submissions/{token}?base64_encoded=true"
                             "&fields=stdout,stderr,compile_output,status")
            status = (res.get("status") or {}).get("id", 0)
            if status > self._DONE_AFTER:
                break
            if time.monotonic() > deadline:
                raise SandboxUnavailable("Judge0 took too long to answer")
            time.sleep(self.poll_s)
        if status in (13, 14):
            raise SandboxUnavailable(f"Judge0 internal error (status {status})")
        dec = lambda v: base64.b64decode(v).decode("utf-8", "replace") if v else ""  # noqa: E731
        if status == 5:
            return [TestResult(t["input"], t["expected"], error="timeout") for t in tests]
        return _parse(dec(res.get("stdout")),
                      dec(res.get("stderr")) or dec(res.get("compile_output")), tests)


def get_executor() -> Executor:
    """Pick the backend from the EXECUTOR env var. Defaults to local."""
    choice = os.environ.get("EXECUTOR", "local").lower()
    if choice == "judge0":
        return Judge0Executor()
    return LocalExecutor()

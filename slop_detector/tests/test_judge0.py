"""Judge0Executor against a tiny fake Judge0 server (no network, no key).

The fake runs the submitted program with the local interpreter and answers in
Judge0's shape (base64 fields, a token, then a poll), so this proves the
request/poll/decode path end to end.
"""
import base64
import json
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from harness.executor import Judge0Executor           # noqa: E402
from harness.loader import load_task, load_submission  # noqa: E402
from harness.scorer import score                       # noqa: E402

_RESULTS = {}
_SEEN_HEADERS = []


class _FakeJudge0(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, body):
        data = json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        _SEEN_HEADERS.append(dict(self.headers))
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        src = base64.b64decode(body["source_code"]).decode()
        proc = subprocess.run([sys.executable, "-c", src], capture_output=True, text=True)
        token = f"t{len(_RESULTS)}"
        _RESULTS[token] = {
            "stdout": base64.b64encode(proc.stdout.encode()).decode(),
            "stderr": base64.b64encode(proc.stderr.encode()).decode() if proc.stderr else None,
            "compile_output": None,
            "status": {"id": 3 if proc.returncode == 0 else 11},
            "_polls": 0,
        }
        self._send({"token": token})

    def do_GET(self):
        token = self.path.split("/submissions/")[1].split("?")[0]
        r = _RESULTS[token]
        r["_polls"] += 1
        if r["_polls"] == 1:  # first poll: still processing
            return self._send({"status": {"id": 2}})
        self._send({k: v for k, v in r.items() if not k.startswith("_")})


def _serve():
    srv = HTTPServer(("127.0.0.1", 0), _FakeJudge0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def test_judge0_scores_like_local(monkeypatch):
    srv = _serve()
    monkeypatch.setenv("JUDGE0_URL", f"http://127.0.0.1:{srv.server_port}")
    monkeypatch.setenv("JUDGE0_KEY", "test-key")
    monkeypatch.setenv("JUDGE0_HOST", "judge0-ce.p.rapidapi.com")
    ex = Judge0Executor(poll_s=0.01)
    for name, expect in [("sample_pass", True), ("sample_fail_02", False), ("sample_pass_04", True)]:
        sub = load_submission(name)
        assert score(load_task(sub["task_id"]), sub, executor=ex).passed is expect, name
    assert {k.lower(): v for k, v in _SEEN_HEADERS[0].items()}["x-rapidapi-key"] == "test-key"
    srv.shutdown()


def test_hallucinated_api_fails_every_test_in_judge0(monkeypatch):
    srv = _serve()
    monkeypatch.setenv("JUDGE0_URL", f"http://127.0.0.1:{srv.server_port}")
    monkeypatch.delenv("JUDGE0_HOST", raising=False)
    t = load_task("csp-slop-01")  # buggy code calls round(..., ROUND_HALF_UP)
    res = Judge0Executor(poll_s=0.01).execute(t["buggy_code"], "python", t["entrypoint"], t["hidden_tests"])
    assert not any(r.passed for r in res)
    srv.shutdown()

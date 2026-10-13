"""Every lab starter and solution must run without errors.

    python tests/test_lab_code.py
"""
import contextlib
import io
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from labs.ai_architect import CURRICULUM  # noqa: E402


def run(code):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        exec(compile(code, '<lab>', 'exec'), {'__name__': '__main__'})
    return out.getvalue()


def main():
    failures = 0
    ids = [item['id'] for item in CURRICULUM]
    assert len(ids) == len(set(ids)), 'duplicate lesson ids'
    for item in CURRICULUM:
        for part in ('starter', 'solution'):
            code = item.get(part)
            if not code:
                continue
            try:
                output = run(code)
                print(f"ok    {item['id']:<12} {part:<8} {output.strip().splitlines()[-1][:60] if output.strip() else ''}")
            except ModuleNotFoundError as e:
                # numpy loads automatically in the browser; skip if it isn't installed here
                print(f"skip  {item['id']:<12} {part:<8} needs {e.name} (pip install {e.name} to test)")
            except Exception as e:  # noqa: BLE001
                failures += 1
                print(f"FAIL  {item['id']:<12} {part:<8} {e!r}")
    print('GREEN' if not failures else f'{failures} FAILED')
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())

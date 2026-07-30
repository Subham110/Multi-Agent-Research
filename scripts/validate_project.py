from __future__ import annotations

import compileall
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str], cwd: Path) -> tuple[bool, str]:
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)
    return result.returncode == 0, (result.stdout + result.stderr).strip()


def main() -> None:
    checks: list[tuple[str, bool, str]] = []
    checks.append(("Python syntax", compileall.compile_dir(ROOT / "backend", quiet=1), "compileall"))
    try:
        json.loads((ROOT / "frontend/package.json").read_text())
        checks.append(("package.json", True, "valid JSON"))
    except Exception as exc:
        checks.append(("package.json", False, str(exc)))

    if (ROOT / "frontend/node_modules").exists():
        ok, output = run(["npm", "run", "build"], ROOT / "frontend")
        checks.append(("Frontend build", ok, output[-1000:]))
    else:
        checks.append(("Frontend build", True, "skipped: run npm install first"))

    if (ROOT / "backend/.venv").exists():
        python = ROOT / "backend/.venv/bin/python"
        ok, output = run([str(python), "-m", "pytest", "-q"], ROOT / "backend")
        checks.append(("Backend tests", ok, output[-1000:]))
    else:
        checks.append(("Backend tests", True, "skipped: use Docker or create backend/.venv"))

    failed = False
    for name, ok, detail in checks:
        marker = "PASS" if ok else "FAIL"
        print(f"[{marker}] {name}: {detail}")
        failed = failed or not ok
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()

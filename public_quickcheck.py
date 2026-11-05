#!/usr/bin/env python3
"""Run public derived-only H2 checks without original measurements.

This convenience entrypoint invokes the existing frozen verifier, guard tests,
and derived-only audit. It never substitutes source data or changes results.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def run_step(label: str, *args: str) -> None:
    print(f"\n=== {label} ===", flush=True)
    subprocess.run([sys.executable, *args], cwd=ROOT, check=True)


def main() -> int:
    if sys.flags.optimize:
        print("Do not run with Python -O: scientific assertions must remain enabled.", file=sys.stderr)
        return 2
    try:
        restore = ROOT / "tools" / "restore_payload.py"
        if restore.is_file():
            run_step("Restore and verify source-derived transport files", "tools/restore_payload.py")
        run_step("Verify immutable scientific manifest", "verify_release.py")
        run_step("Test input admission and failure paths", "tests/test_guards.py")
        with tempfile.TemporaryDirectory(prefix="h2-derived-check-") as tmp:
            output_dir = str(Path(tmp) / "results")
            run_step("Reproduce saved-score audit (not raw-source replay)",
                     "reproduce.py", "--mode", "derived", "--out", output_dir)
    except subprocess.CalledProcessError as exc:
        print(f"PUBLIC_DERIVED_CHECK_FAIL (exit {exc.returncode})", file=sys.stderr)
        return exc.returncode if exc.returncode > 0 else 1
    print("\nPUBLIC_DERIVED_CHECK_PASS — derived-only, not independent laboratory raw replay")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

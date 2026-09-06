"""run_tests.py — Test runner script to execute unit tests, capture logs, and export reports."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

# Paths
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
TESTS_DIR = BACKEND_DIR / "tests"
RESULTS_DIR = ROOT_DIR / "test_results"


def main() -> int:
    """Run pytest with coverage and save test artifacts to test_results/."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("Running DocQ&A Backend Unit Test Suite with Pytest & Coverage")
    print(f"Working Directory: {BACKEND_DIR}")
    print(f"Results Directory: {RESULTS_DIR}")
    print("=" * 70)

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        str(TESTS_DIR),
        "-v",
        "--cov=.",
        "--cov-report=term-missing",
    ]

    result = subprocess.run(
        cmd,
        cwd=str(BACKEND_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    output = result.stdout
    print(output)

    # Save complete test execution log
    log_file = RESULTS_DIR / "test_execution_log.txt"
    log_file.write_text(output, encoding="utf-8")
    print(f"[OK] Saved execution log to: {log_file}")

    # Extract and save coverage table
    cov_file = RESULTS_DIR / "coverage_summary.txt"
    if "tests coverage" in output:
        cov_part = output.split("tests coverage")[1].strip()
        cov_file.write_text(cov_part, encoding="utf-8")
        print(f"[OK] Saved coverage summary to: {cov_file}")

    print("=" * 70)
    if result.returncode == 0:
        print("ALL TESTS PASSED SUCCESSFULLY! (Return code: 0)")
    else:
        print(f"TEST RUN FAILED with return code: {result.returncode}")
    print("=" * 70)

    return result.returncode


if __name__ == "__main__":
    sys.exit(main())

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_hardware_bom_and_work_plan_are_consistent() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/validate_hardware_docs.py"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "covering 47 STL assets" in result.stdout


def test_split_hardware_bom_views_are_current() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/generate_hardware_bom_views.py", "--check"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "print_bom.csv" in result.stdout
    assert "purchase_bom.csv" in result.stdout
    assert "reference_bom.csv" in result.stdout

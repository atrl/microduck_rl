from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_robot_asset_manifest_covers_current_models() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/organize_robot_assets.py", "--check"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "Validated 47 STL assets" in result.stdout

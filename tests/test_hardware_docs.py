from __future__ import annotations

import hashlib
import subprocess
import sys
import zipfile
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
    assert "16 imu board BOM rows" in result.stdout


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


def test_imu_bench_manufacturing_exports_are_frozen() -> None:
    manufacturing_dir = REPO_ROOT / "docs" / "hardware" / "manufacturing"
    expected_hashes = {
        "imu_to_dxl_v0_1_bom_jlceda.xlsx": (
            "33c39e54cb25dc6e912cd03eeb405813d8fc6825139a09b2733d8e8aefad1bc7"
        ),
        "imu_to_dxl_v0_1_cpl_jlceda.xlsx": (
            "58a26889deb36d4438ff79711d618a2cb0b8be750c618c561e1a1fe5a2d8500f"
        ),
        "imu_to_dxl_v0_1_gerber.zip": (
            "8fee6a12faf76bbeaf4d83d3b3e80c6f33418128ce2b5a7c9f4a1a8782e4b619"
        ),
    }

    for filename, expected_hash in expected_hashes.items():
        payload = (manufacturing_dir / filename).read_bytes()
        assert hashlib.sha256(payload).hexdigest() == expected_hash

    with zipfile.ZipFile(manufacturing_dir / "imu_to_dxl_v0_1_gerber.zip") as archive:
        names = set(archive.namelist())
    assert "Gerber_BoardOutlineLayer.GKO" in names
    assert "Drill_PTH_Through.DRL" in names
    assert "Gerber_TopLayer.GTL" in names
    assert "Gerber_BottomLayer.GBL" in names

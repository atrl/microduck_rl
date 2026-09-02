from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
XLSX_NAMESPACE = {
    "x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
}


def _read_xlsx_rows(path: Path) -> list[list[str]]:
    with zipfile.ZipFile(path) as archive:
        shared_root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
        shared = [
            "".join(node.text or "" for node in item.findall(".//x:t", XLSX_NAMESPACE))
            for item in shared_root.findall("x:si", XLSX_NAMESPACE)
        ]
        sheet_root = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))

    rows: list[list[str]] = []
    for row in sheet_root.findall(".//x:row", XLSX_NAMESPACE):
        values: list[str] = []
        for cell in row.findall("x:c", XLSX_NAMESPACE):
            value = cell.find("x:v", XLSX_NAMESPACE)
            raw = "" if value is None or value.text is None else value.text
            values.append(shared[int(raw)] if cell.get("t") == "s" else raw)
        rows.append(values)
    return rows


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
    assert "13 imu board BOM rows" in result.stdout


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
        "imu_to_dxl_v0_2_bom_jlceda.xlsx": (
            "f97b23ee7591972f90a40496acf245c9bd82b9956d7d0b4db393def2ceedb60f"
        ),
        "imu_to_dxl_v0_2_cpl_jlceda.xlsx": (
            "de717a241c9407b4b0932f892467e573b482d1936aee77b8de7e62025f64f090"
        ),
        "imu_to_dxl_v0_2_gerber.zip": (
            "76a9de183a998e3e5e8aa8490abc283e733a0f624145d37fb3a87c1ff9495d00"
        ),
    }

    for filename, expected_hash in expected_hashes.items():
        payload = (manufacturing_dir / filename).read_bytes()
        assert hashlib.sha256(payload).hexdigest() == expected_hash

    with zipfile.ZipFile(manufacturing_dir / "imu_to_dxl_v0_2_gerber.zip") as archive:
        names = set(archive.namelist())
        top_copper = archive.read("Gerber_TopLayer.GTL")
        bottom_copper = archive.read("Gerber_BottomLayer.GBL")
    assert "Gerber_BoardOutlineLayer.GKO" in names
    assert "Drill_PTH_Through.DRL" in names
    assert "Gerber_TopLayer.GTL" in names
    assert "Gerber_BottomLayer.GBL" in names
    assert b"G04 Copper Areas: 38*" in top_copper
    assert b"G04 Copper Areas: 4*" in bottom_copper

    bom_rows = _read_xlsx_rows(
        manufacturing_dir / "imu_to_dxl_v0_2_bom_jlceda.xlsx"
    )
    assert bom_rows[0][3] == "Designator"
    assert len([row for row in bom_rows[1:] if row and row[0]]) == 12
    bom_designators = ",".join(row[3] for row in bom_rows[1:] if len(row) > 3)
    assert not {"D1", "D2", "J2"} & set(bom_designators.split(","))
    assert {"C529329", "C5267406", "C2676069", "C95414"} <= {
        row[8] for row in bom_rows[1:] if len(row) > 8
    }

    cpl_rows = _read_xlsx_rows(
        manufacturing_dir / "imu_to_dxl_v0_2_cpl_jlceda.xlsx"
    )
    assert cpl_rows[0][0] == "Designator"
    placements = [row for row in cpl_rows[1:] if row and row[0]]
    assert len(placements) == 22
    assert not {"D1", "D2", "J2"} & {row[0] for row in placements}
    j1 = next(row for row in placements if row[0] == "J1")
    assert j1[12] == "No"
    assert sum(row[12] == "Yes" for row in placements) == 21


def test_imu_dynamixel_protocol_core() -> None:
    compiler = shutil.which("cc")
    assert compiler is not None, "a C compiler is required for protocol-core tests"
    firmware_dir = REPO_ROOT / "firmware" / "imu_to_dxl_v0_2"

    with tempfile.TemporaryDirectory() as output_dir:
        executable = Path(output_dir) / "test_dxl2_slave"
        compile_result = subprocess.run(
            [
                compiler,
                "-std=c11",
                "-Wall",
                "-Wextra",
                "-Werror",
                "-pedantic",
                f"-I{firmware_dir / 'include'}",
                str(firmware_dir / "src" / "dxl2_slave.c"),
                str(firmware_dir / "tests" / "test_dxl2_slave.c"),
                "-o",
                str(executable),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        assert compile_result.returncode == 0, compile_result.stderr
        test_result = subprocess.run(
            [str(executable)], check=False, capture_output=True, text=True
        )

    assert test_result.returncode == 0, test_result.stderr
    assert "dxl2_slave_core: all tests passed" in test_result.stdout

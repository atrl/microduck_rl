#!/usr/bin/env python3
"""Validate and package Microduck STL assets by physical role.

The source meshes stay beside the MJCF files because MuJoCo references them
there.  This script creates a separate, human-friendly copy for inspection or
slicer import without changing the simulation asset paths.
"""

from __future__ import annotations

import argparse
import csv
import shutil
import sys
from pathlib import Path
from xml.etree import ElementTree

REPO_ROOT = Path(__file__).resolve().parents[1]
ROBOT_DIR = REPO_ROOT / "src/mjlab_microduck/robot/microduck"
ASSET_DIR = ROBOT_DIR / "assets"
MANIFEST_PATH = ROBOT_DIR / "asset_manifest.csv"
MODEL_PATHS = {
    "base_qty": ROBOT_DIR / "robot_allcollisions.xml",
    "roller_qty": ROBOT_DIR / "robot_allcollisions_rollers.xml",
}
CATEGORY_DIRS = {
    "print_candidate_rigid": Path("01_print_candidates/rigid"),
    "print_candidate_flexible": Path("01_print_candidates/flexible"),
    "purchased_reference": Path("02_purchased_reference"),
    "legacy_unreferenced": Path("90_legacy_unreferenced"),
}
REQUIRED_FIELDS = (
    "file",
    "category",
    "subsystem",
    "base_qty",
    "roller_qty",
    "role",
    "notes",
)


def _load_manifest() -> list[dict[str, str]]:
    with MANIFEST_PATH.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != REQUIRED_FIELDS:
            raise ValueError(
                f"Unexpected manifest columns: {reader.fieldnames}; "
                f"expected {list(REQUIRED_FIELDS)}"
            )
        rows = list(reader)
    return rows


def _declared_stls(model_path: Path) -> set[str]:
    root = ElementTree.parse(model_path).getroot()
    asset = root.find("asset")
    if asset is None:
        raise ValueError(f"No <asset> block in {model_path}")
    return {
        mesh.attrib["file"]
        for mesh in asset.findall("mesh")
        if mesh.attrib.get("file", "").endswith(".stl")
    }


def validate(rows: list[dict[str, str]]) -> None:
    errors: list[str] = []
    files = [row["file"] for row in rows]
    duplicates = sorted({name for name in files if files.count(name) > 1})
    if duplicates:
        errors.append(f"duplicate manifest entries: {duplicates}")

    disk_files = {path.name for path in ASSET_DIR.glob("*.stl")}
    manifest_files = set(files)
    if disk_files - manifest_files:
        errors.append(f"unclassified STL files: {sorted(disk_files - manifest_files)}")
    if manifest_files - disk_files:
        errors.append(
            f"manifest files missing on disk: {sorted(manifest_files - disk_files)}"
        )

    refs = {quantity: _declared_stls(path) for quantity, path in MODEL_PATHS.items()}
    for row in rows:
        name = row["file"]
        category = row["category"]
        if category not in CATEGORY_DIRS:
            errors.append(f"{name}: unknown category {category!r}")
            continue
        for quantity_field, referenced in refs.items():
            try:
                quantity = int(row[quantity_field])
            except ValueError:
                errors.append(f"{name}: {quantity_field} is not an integer")
                continue
            if quantity < 0:
                errors.append(f"{name}: {quantity_field} must be non-negative")
            if (name in referenced) != (quantity > 0):
                errors.append(
                    f"{name}: {quantity_field}={quantity} disagrees with "
                    f"{MODEL_PATHS[quantity_field].name}"
                )
        if category == "legacy_unreferenced" and (
            row["base_qty"] != "0" or row["roller_qty"] != "0"
        ):
            errors.append(f"{name}: legacy asset must have zero quantities")

    for quantity_field, referenced in refs.items():
        missing = referenced - manifest_files
        if missing:
            errors.append(
                f"{MODEL_PATHS[quantity_field].name}: assets missing from manifest: "
                f"{sorted(missing)}"
            )

    if errors:
        raise ValueError("Asset manifest validation failed:\n- " + "\n- ".join(errors))


def _write_bundle_readme(output: Path) -> None:
    text = """# Microduck robot asset bundle

This directory is generated from `asset_manifest.csv`.

- `01_print_candidates/rigid`: structural and cosmetic meshes that appear to be
  rigid printed parts.
- `01_print_candidates/flexible`: soles, mouth skins, and tires that appear to
  require a flexible material.
- `02_purchased_reference`: collision/visual envelopes for motors, bearings,
  electronics, battery, camera lens, and speaker. Do not print these as
  replacements for the purchased components.
- `90_legacy_unreferenced`: exports not referenced by either current assembly.

`base_qty` is the quantity in the walking/all-collisions assembly;
`roller_qty` is the quantity in the roller assembly.

Important: these STL files were exported for simulation with STL simplification
enabled. They have not been certified as manufacturing-ready meshes. Confirm
material, tolerances, orientation, fasteners, and the current revision in the
linked Onshape assembly before ordering or printing physical parts.

The source README licenses 3D model files under CC BY-SA-NC.
"""
    (output / "README.md").write_text(text, encoding="utf-8")


def package(rows: list[dict[str, str]], output: Path) -> None:
    output = output.resolve()
    if output.exists():
        raise FileExistsError(
            f"Output already exists: {output}. Choose a new --output path."
        )
    output.mkdir(parents=True)
    for row in rows:
        relative_dir = CATEGORY_DIRS[row["category"]] / row["subsystem"]
        destination = output / relative_dir
        destination.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ASSET_DIR / row["file"], destination / row["file"])
    shutil.copy2(MANIFEST_PATH, output / "MANIFEST.csv")
    _write_bundle_readme(output)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate the manifest without creating a bundle",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "build/microduck_robot_assets",
        help="new directory to create (default: build/microduck_robot_assets)",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    try:
        rows = _load_manifest()
        validate(rows)
        if not args.check:
            package(rows, args.output)
    except (FileExistsError, OSError, ValueError) as exc:
        print(exc, file=sys.stderr)
        return 1

    print(f"Validated {len(rows)} STL assets against both current assemblies.")
    if not args.check:
        print(f"Created organized bundle: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Validate the hardware BOM and work-plan contracts."""

from __future__ import annotations

import csv
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
HARDWARE_DIR = REPO_ROOT / "docs/hardware"
BOM_PATH = HARDWARE_DIR / "microduck_bom.csv"
PLAN_PATH = HARDWARE_DIR / "work_plan.csv"
PRINT_BOM_PATH = HARDWARE_DIR / "print_bom.csv"
PURCHASE_BOM_PATH = HARDWARE_DIR / "purchase_bom.csv"
REFERENCE_BOM_PATH = HARDWARE_DIR / "reference_bom.csv"
IMU_BOARD_BOM_PATH = HARDWARE_DIR / "imu_to_dxl_v0_bom.csv"
ASSET_MANIFEST_PATH = (
    REPO_ROOT / "src/mjlab_microduck/robot/microduck/asset_manifest.csv"
)

BOM_FIELDS = (
    "item_id",
    "variant",
    "subsystem",
    "item_name",
    "specification",
    "source_asset",
    "base_qty",
    "roller_qty",
    "purchase_qty",
    "unit",
    "procurement_class",
    "status",
    "confidence",
    "verification_gate",
    "source_url",
    "notes",
    "buy_status",
    "preferred_url",
    "alternate_url",
    "link_type",
    "link_checked_on",
    "next_action",
    "purchase_notes",
)
PLAN_FIELDS = (
    "task_id",
    "phase",
    "task",
    "depends_on",
    "status",
    "priority",
    "deliverable",
    "exit_criteria",
    "evidence_required",
    "notes",
)
IMU_BOARD_BOM_FIELDS = (
    "refdes",
    "quantity",
    "function",
    "manufacturer_part",
    "manufacturer",
    "package",
    "lcsc_id",
    "jlc_device_uuid",
    "jlc_library_uuid",
    "assembly_status",
    "evidence_status",
    "source_url",
    "verification_gate",
    "notes",
)
BOM_STATUSES = {
    "confirmed_model",
    "confirmed_runtime",
    "inferred",
    "design_choice",
    "needs_confirmation",
    "reference_only",
    "legacy",
}
PROCUREMENT_CLASSES = {
    "print_rigid",
    "print_flexible",
    "purchase",
    "custom_board",
    "fabricate",
    "consumable",
    "tooling",
    "reference_only",
    "legacy",
}
CONFIDENCE_LEVELS = {"high", "medium", "low"}
PLAN_STATUSES = {"pending", "in_progress", "blocked", "complete"}
PRIORITIES = {"P0", "P1", "P2"}
PRINT_CLASSES = {"print_rigid", "print_flexible"}
PURCHASE_CLASSES = {"purchase", "custom_board", "fabricate", "consumable", "tooling"}
REFERENCE_CLASSES = {"reference_only", "legacy"}
BUY_STATUSES = {
    "ready_to_buy",
    "verify_before_buy",
    "inventory_included_first",
    "design_first",
    "do_not_buy",
    "choose_local",
}
IMU_BOARD_ASSEMBLY_STATUSES = {
    "populate",
    "populate_0R_then_tune",
    "populate_then_measure",
    "prototype_only",
    "dnp_until_review",
    "dnp_until_measurement",
    "fabricate",
}


def _read_csv(path: Path, expected_fields: tuple[str, ...]) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != expected_fields:
            raise ValueError(
                f"{path}: unexpected columns {reader.fieldnames}; "
                f"expected {list(expected_fields)}"
            )
        return list(reader)


def _duplicates(values: list[str]) -> list[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return sorted(duplicates)


def _validate_quantity(
    row_name: str, field: str, value: str, errors: list[str]
) -> None:
    if value == "":
        return
    try:
        quantity = int(value)
    except ValueError:
        errors.append(f"{row_name}: {field}={value!r} is not an integer or blank")
        return
    if quantity < 0:
        errors.append(f"{row_name}: {field} must be non-negative")


def validate_bom() -> tuple[int, int, dict[str, int]]:
    rows = _read_csv(BOM_PATH, BOM_FIELDS)
    asset_rows = _read_csv(
        ASSET_MANIFEST_PATH,
        (
            "file",
            "category",
            "subsystem",
            "base_qty",
            "roller_qty",
            "role",
            "notes",
        ),
    )
    errors: list[str] = []

    item_ids = [row["item_id"] for row in rows]
    if duplicates := _duplicates(item_ids):
        errors.append(f"duplicate BOM item ids: {duplicates}")

    source_assets = [row["source_asset"] for row in rows if row["source_asset"]]
    if duplicates := _duplicates(source_assets):
        errors.append(f"source assets assigned more than once: {duplicates}")

    expected_assets = {row["file"] for row in asset_rows}
    covered_assets = set(source_assets)
    if missing := expected_assets - covered_assets:
        errors.append(f"BOM does not cover source assets: {sorted(missing)}")
    if unknown := covered_assets - expected_assets:
        errors.append(f"BOM references unknown source assets: {sorted(unknown)}")

    asset_by_name = {row["file"]: row for row in asset_rows}
    for row in rows:
        item_id = row["item_id"]
        if not item_id:
            errors.append("BOM row has empty item_id")
            continue
        if row["status"] not in BOM_STATUSES:
            errors.append(f"{item_id}: unknown status {row['status']!r}")
        if row["procurement_class"] not in PROCUREMENT_CLASSES:
            errors.append(
                f"{item_id}: unknown procurement_class {row['procurement_class']!r}"
            )
        if row["confidence"] not in CONFIDENCE_LEVELS:
            errors.append(f"{item_id}: unknown confidence {row['confidence']!r}")
        for field in ("base_qty", "roller_qty", "purchase_qty"):
            _validate_quantity(item_id, field, row[field], errors)
        if not row["item_name"] or not row["verification_gate"]:
            errors.append(f"{item_id}: item_name and verification_gate are required")
        if row["source_url"] and not row["source_url"].startswith("https://"):
            errors.append(f"{item_id}: source_url must be an https URL")
        if (
            row["status"] in {"confirmed_model", "confirmed_runtime", "inferred"}
            and not row["source_url"]
        ):
            errors.append(f"{item_id}: evidence-backed status requires source_url")

        source_asset = row["source_asset"]
        if source_asset and row["procurement_class"] in {
            "print_rigid",
            "print_flexible",
            "legacy",
        }:
            asset = asset_by_name[source_asset]
            if row["base_qty"] != asset["base_qty"]:
                errors.append(
                    f"{item_id}: base_qty disagrees with asset manifest for {source_asset}"
                )
            if row["roller_qty"] != asset["roller_qty"]:
                errors.append(
                    f"{item_id}: roller_qty disagrees with asset manifest for "
                    f"{source_asset}"
                )

    expected_purchase_ids = {
        row["item_id"] for row in rows if row["procurement_class"] in PURCHASE_CLASSES
    }
    purchasing_fields = (
        "buy_status",
        "preferred_url",
        "alternate_url",
        "link_type",
        "link_checked_on",
        "next_action",
        "purchase_notes",
    )
    for row in rows:
        item_id = row["item_id"]
        if item_id not in expected_purchase_ids:
            populated = [field for field in purchasing_fields if row[field]]
            if populated:
                errors.append(
                    f"{item_id}: non-purchase item has purchasing fields {populated}"
                )
            continue
        buy_status = row["buy_status"]
        if buy_status not in BUY_STATUSES:
            errors.append(f"{item_id}: unknown buy_status {buy_status!r}")
        for field in ("preferred_url", "alternate_url"):
            if row[field] and not row[field].startswith("https://"):
                errors.append(f"{item_id}: {field} must be an https URL")
        if (
            buy_status
            in {
                "ready_to_buy",
                "verify_before_buy",
                "inventory_included_first",
            }
            and not row["preferred_url"]
        ):
            errors.append(f"{item_id}: {buy_status} requires preferred_url")
        if buy_status in {"design_first", "do_not_buy"} and row["preferred_url"]:
            errors.append(f"{item_id}: {buy_status} must not include a purchase URL")
        if not row["purchase_notes"] or not row["next_action"]:
            errors.append(f"{item_id}: purchase_notes and next_action are required")
        try:
            date.fromisoformat(row["link_checked_on"])
        except ValueError:
            errors.append(f"{item_id}: link_checked_on must be an ISO date")

    view_paths = {
        "print": PRINT_BOM_PATH,
        "purchase": PURCHASE_BOM_PATH,
        "reference": REFERENCE_BOM_PATH,
    }
    view_ids: dict[str, set[str]] = {}
    for name, path in view_paths.items():
        with path.open(newline="", encoding="utf-8") as handle:
            view_ids[name] = {row["item_id"] for row in csv.DictReader(handle)}
    expected_view_ids = {
        "print": {
            row["item_id"] for row in rows if row["procurement_class"] in PRINT_CLASSES
        },
        "purchase": expected_purchase_ids,
        "reference": {
            row["item_id"]
            for row in rows
            if row["procurement_class"] in REFERENCE_CLASSES
        },
    }
    for name, expected in expected_view_ids.items():
        if view_ids[name] != expected:
            errors.append(
                f"{name} BOM view ids disagree with master: "
                f"missing={sorted(expected - view_ids[name])} "
                f"extra={sorted(view_ids[name] - expected)}"
            )
    combined = set().union(*view_ids.values())
    if combined != set(item_ids):
        errors.append("split BOM views do not cover every master BOM item")
    names = list(view_ids)
    for index, left in enumerate(names):
        for right in names[index + 1 :]:
            if overlap := view_ids[left] & view_ids[right]:
                errors.append(
                    f"split BOM views {left} and {right} overlap: {sorted(overlap)}"
                )

    if errors:
        raise ValueError("Hardware BOM validation failed:\n- " + "\n- ".join(errors))
    return (
        len(rows),
        len(expected_assets),
        {name: len(ids) for name, ids in view_ids.items()},
    )


def validate_plan() -> int:
    rows = _read_csv(PLAN_PATH, PLAN_FIELDS)
    errors: list[str] = []
    task_ids = [row["task_id"] for row in rows]
    task_id_set = set(task_ids)
    if duplicates := _duplicates(task_ids):
        errors.append(f"duplicate work-plan task ids: {duplicates}")

    dependencies_by_task: dict[str, list[str]] = {}
    for row in rows:
        task_id = row["task_id"]
        if row["status"] not in PLAN_STATUSES:
            errors.append(f"{task_id}: unknown status {row['status']!r}")
        if row["priority"] not in PRIORITIES:
            errors.append(f"{task_id}: unknown priority {row['priority']!r}")
        for field in (
            "phase",
            "task",
            "deliverable",
            "exit_criteria",
            "evidence_required",
        ):
            if not row[field]:
                errors.append(f"{task_id}: {field} is required")
        dependencies = [value for value in row["depends_on"].split("|") if value]
        dependencies_by_task[task_id] = dependencies
        if task_id in dependencies:
            errors.append(f"{task_id}: task cannot depend on itself")
        if unknown := sorted(set(dependencies) - task_id_set):
            errors.append(f"{task_id}: unknown dependencies {unknown}")
        if row["status"] == "blocked" and not row["notes"]:
            errors.append(f"{task_id}: blocked task must name the blocker in notes")

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(task_id: str, path: list[str]) -> None:
        if task_id in visiting:
            cycle_start = path.index(task_id) if task_id in path else 0
            errors.append(
                "work-plan dependency cycle: "
                + " -> ".join(path[cycle_start:] + [task_id])
            )
            return
        if task_id in visited:
            return
        visiting.add(task_id)
        for dependency in dependencies_by_task.get(task_id, []):
            if dependency in task_id_set:
                visit(dependency, path + [task_id])
        visiting.remove(task_id)
        visited.add(task_id)

    for task_id in task_ids:
        visit(task_id, [])

    if errors:
        raise ValueError(
            "Hardware work-plan validation failed:\n- " + "\n- ".join(errors)
        )
    return len(rows)


def validate_imu_board_bom() -> int:
    rows = _read_csv(IMU_BOARD_BOM_PATH, IMU_BOARD_BOM_FIELDS)
    errors: list[str] = []
    refdes_values = [row["refdes"] for row in rows]
    if duplicates := _duplicates(refdes_values):
        errors.append(f"duplicate imu board BOM refdes groups: {duplicates}")

    for row in rows:
        refdes = row["refdes"] or "<empty>"
        try:
            quantity = int(row["quantity"])
            if quantity <= 0:
                errors.append(f"{refdes}: quantity must be positive")
        except ValueError:
            errors.append(f"{refdes}: quantity={row['quantity']!r} is not an integer")

        for field in (
            "refdes",
            "function",
            "manufacturer_part",
            "package",
            "assembly_status",
            "evidence_status",
            "verification_gate",
        ):
            if not row[field]:
                errors.append(f"{refdes}: {field} is required")
        if row["assembly_status"] not in IMU_BOARD_ASSEMBLY_STATUSES:
            errors.append(
                f"{refdes}: unknown assembly_status {row['assembly_status']!r}"
            )
        if row["evidence_status"] not in BOM_STATUSES:
            errors.append(
                f"{refdes}: unknown evidence_status {row['evidence_status']!r}"
            )
        if row["source_url"] and not row["source_url"].startswith("https://"):
            errors.append(f"{refdes}: source_url must be an https URL")

        jlc_fields = (
            row["lcsc_id"],
            row["jlc_device_uuid"],
            row["jlc_library_uuid"],
        )
        if any(jlc_fields) and not all(jlc_fields):
            errors.append(
                f"{refdes}: LCSC id and both JLC UUID fields must be populated together"
            )

    if errors:
        raise ValueError(
            "IMU board BOM validation failed:\n- " + "\n- ".join(errors)
        )
    return len(rows)


def main() -> int:
    try:
        bom_rows, asset_count, view_counts = validate_bom()
        plan_rows = validate_plan()
        imu_board_bom_rows = validate_imu_board_bom()
    except (OSError, ValueError) as exc:
        print(exc, file=sys.stderr)
        return 1
    print(
        f"Validated {bom_rows} BOM rows covering {asset_count} STL assets and "
        f"{plan_rows} work-plan tasks plus {imu_board_bom_rows} imu board BOM rows; "
        f"split views={view_counts}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

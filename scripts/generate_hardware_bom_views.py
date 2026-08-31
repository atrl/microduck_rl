#!/usr/bin/env python3
"""Generate mutually exclusive print, purchase, and reference BOM views."""

from __future__ import annotations

import argparse
import csv
import io
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
HARDWARE_DIR = REPO_ROOT / "docs/hardware"
MASTER_PATH = HARDWARE_DIR / "microduck_bom.csv"
LINKS_PATH = HARDWARE_DIR / "purchase_links.csv"

PRINT_PATH = HARDWARE_DIR / "print_bom.csv"
PURCHASE_PATH = HARDWARE_DIR / "purchase_bom.csv"
REFERENCE_PATH = HARDWARE_DIR / "reference_bom.csv"

PRINT_CLASSES = {"print_rigid", "print_flexible"}
PURCHASE_CLASSES = {"purchase", "custom_board", "fabricate", "consumable", "tooling"}
REFERENCE_CLASSES = {"reference_only", "legacy"}

PRINT_FIELDS = (
    "item_id",
    "variant",
    "subsystem",
    "item_name",
    "specification",
    "source_asset",
    "local_asset_path",
    "base_qty",
    "roller_qty",
    "unit",
    "procurement_class",
    "status",
    "confidence",
    "verification_gate",
    "source_url",
    "notes",
)
PURCHASE_FIELDS = (
    "item_id",
    "variant",
    "subsystem",
    "item_name",
    "specification",
    "base_qty",
    "roller_qty",
    "purchase_qty",
    "unit",
    "procurement_class",
    "status",
    "confidence",
    "buy_status",
    "preferred_url",
    "alternate_url",
    "link_type",
    "link_checked_on",
    "verification_gate",
    "source_url",
    "purchase_notes",
    "notes",
)
REFERENCE_FIELDS = (
    "item_id",
    "variant",
    "subsystem",
    "item_name",
    "specification",
    "source_asset",
    "procurement_class",
    "status",
    "confidence",
    "verification_gate",
    "source_url",
    "notes",
)


def _read(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _render(rows: list[dict[str, str]], fields: tuple[str, ...]) -> str:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({field: row.get(field, "") for field in fields})
    return buffer.getvalue()


def generate() -> dict[Path, str]:
    master = _read(MASTER_PATH)
    links = {row["item_id"]: row for row in _read(LINKS_PATH)}
    print_rows: list[dict[str, str]] = []
    purchase_rows: list[dict[str, str]] = []
    reference_rows: list[dict[str, str]] = []

    for row in master:
        procurement_class = row["procurement_class"]
        if procurement_class in PRINT_CLASSES:
            printable = dict(row)
            printable["local_asset_path"] = (
                "src/mjlab_microduck/robot/microduck/assets/" + row["source_asset"]
            )
            print_rows.append(printable)
        elif procurement_class in PURCHASE_CLASSES:
            merged = dict(row)
            merged.update(links.get(row["item_id"], {}))
            purchase_rows.append(merged)
        elif procurement_class in REFERENCE_CLASSES:
            reference_rows.append(row)
        else:
            raise ValueError(
                f"{row['item_id']}: procurement class {procurement_class!r} "
                "is not assigned to a BOM view"
            )

    return {
        PRINT_PATH: _render(print_rows, PRINT_FIELDS),
        PURCHASE_PATH: _render(purchase_rows, PURCHASE_FIELDS),
        REFERENCE_PATH: _render(reference_rows, REFERENCE_FIELDS),
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail if committed BOM views are not current",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    try:
        outputs = generate()
        if args.check:
            stale = [
                path
                for path, expected in outputs.items()
                if not path.exists() or path.read_text(encoding="utf-8") != expected
            ]
            if stale:
                raise ValueError(
                    "stale generated BOM views: "
                    + ", ".join(str(path.relative_to(REPO_ROOT)) for path in stale)
                )
        else:
            for path, text in outputs.items():
                path.write_text(text, encoding="utf-8")
    except (OSError, ValueError) as exc:
        print(exc, file=sys.stderr)
        return 1

    counts = {path.name: text.count("\n") - 1 for path, text in outputs.items()}
    action = "Validated" if args.check else "Generated"
    print(f"{action} BOM views: {counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

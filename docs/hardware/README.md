# Microduck hardware reconstruction

This directory tracks a **safe functional replica**, not an undocumented claim
about the production Microduck hardware. The official repositories publish the
runtime, simulation meshes, and policy-training stack, but not a complete
manufacturing BOM, board schematics, harness drawing, horn-zero drawing, or
assembly manual.

The reconstruction therefore keeps four evidence classes separate:

- `confirmed_model`: present in the checked-in MJCF/STL assembly.
- `confirmed_runtime`: required by the current official runtime source.
- `inferred`: derived from mesh holes or third-party reconstruction work.
- `design_choice`: added here to make the replica testable and electrically
  safer; it is not a claim about the official product.

`needs_confirmation` means the item or exact specification cannot be purchased
or fabricated safely without a measurement or prototype test.

## Files

- [`microduck_bom.csv`](microduck_bom.csv): printable parts, purchased parts,
  boards, harness, fasteners, materials, tools, quantities, confidence, sources,
  and verification gates. This remains the canonical master.
- [`print_bom.csv`](print_bom.csv): only rigid and flexible print candidates,
  including direct local paths to each STL.
- [`purchase_bom.csv`](purchase_bom.csv): purchased, fabricated, board,
  consumable, and tooling items with buy status and product/search links.
- [`reference_bom.csv`](reference_bom.csv): reference-only and legacy meshes
  that should not enter a print or purchase order.
- [`assembly_and_wiring.md`](assembly_and_wiring.md): provisional assembly and
  wiring sequence with hard stop conditions.
- [`build_plan.md`](build_plan.md): phase gates and execution rules.
- [`work_plan.csv`](work_plan.csv): task-level dependency and evidence tracker.
- [`imu_to_dxl_v0_design.md`](imu_to_dxl_v0_design.md): source-backed ID200
  replacement-board contract, schematic decisions, and verification gates.
- [`imu_to_dxl_v0_bom.csv`](imu_to_dxl_v0_bom.csv): board-level prototype BOM
  with JLC/LCSC identifiers and DNP decisions.
- [`imu_to_dxl_v0_bringup.md`](imu_to_dxl_v0_bringup.md): PCB, firmware,
  inspection, power, one-servo, and full-bus completion gates.
- [`../robot_assets.md`](../robot_assets.md): original simulation-asset package.

## Design target

`safe-replica-v0` uses the simulation-derived mechanical envelope and the
current runtime's Radxa Zero 3W / 15-servo / ID200 IMU contract. It does **not**
copy the unresolved prototype power path. Retail XL330-M288-T servos are rated
for 3.7–6.0 V, while the runtime describes a 2S pack as 6.6–8.2 V under load.
Until the official power board is documented, the replica uses separate
regulated logic and servo rails and requires actuator recalibration plus policy
retraining.

## Current readiness

- Mechanical topology: evidence available; manufacturing tolerances pending.
- Fasteners: stock estimate available; installed schedule pending dry fit.
- Servo bus protocol and IDs: confirmed by official runtime.
- Power distribution: design required; **do not connect a 2S pack directly to
  retail XL330 servos from this documentation**.
- Robot HAT and `imu_to_dxl`: interface contracts available; official schematic
  and firmware unavailable; replacements must be designed and tested.
- Full assembly: blocked until the P0 gates in `build_plan.md` pass.

## Primary sources

- Official training and simulation repository:
  <https://github.com/pollen-robotics/microduck_rl>
- Official runtime bus and robot model:
  <https://github.com/pollen-robotics/microduck/tree/main/duck-control/src>
- ROBOTIS XL330 manual:
  <https://emanual.robotis.com/docs/en/dxl/x/xl330-m288/>
- Radxa Zero 3 documentation:
  <https://docs.radxa.com/en/zero/zero3>

The third-party fastener and exploded-view reconstruction is useful secondary
evidence but is not endorsed by Pollen Robotics:
<https://github.com/fanhao375/microduck-replica>.

## Purchase status

The purchase view is intentionally not a one-click cart:

- `ready_to_buy`: exact part or product family is fixed; still verify regional
  stock and delivery.
- `verify_before_buy`: a useful link exists but a fit, revision, or interface
  measurement must pass first.
- `inventory_included_first`: first count parts bundled with another purchase.
- `design_first`: electrical or mechanical design work must finish before a
  part can be selected.
- `do_not_buy`: the item is unavailable, obsolete, or too underspecified.
- `choose_local`: generic commodity or tool; select a reputable local source.

Rows without a purchase URL are retained rather than guessed. Their
`next_action` says how to close the gap: finish design and measurements first,
confirm an alternative, count bundled inventory, or freeze acceptance criteria
for local sourcing. Purchase metadata lives directly in the master BOM; there
is no separate link sidecar to keep synchronized.

As of 2026-09-01 the purchase view has 63 rows: 5 `ready_to_buy`, 23
`verify_before_buy`, 5 `inventory_included_first`, 20 `design_first`, 3
`do_not_buy`, and 7 `choose_local`. Thirty-three rows include a preferred link.

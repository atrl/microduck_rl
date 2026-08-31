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
  and verification gates.
- [`assembly_and_wiring.md`](assembly_and_wiring.md): provisional assembly and
  wiring sequence with hard stop conditions.
- [`build_plan.md`](build_plan.md): phase gates and execution rules.
- [`work_plan.csv`](work_plan.csv): task-level dependency and evidence tracker.
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

# Safe replica build plan

The authoritative task tracker is [`work_plan.csv`](work_plan.csv). The master
BOM is split into [`print_bom.csv`](print_bom.csv),
[`purchase_bom.csv`](purchase_bom.csv), and
[`reference_bom.csv`](reference_bom.csv) for execution. This page defines the
phase gates and rules used to decide whether those tasks may advance.

## Outcome

Produce one reproducible Microduck-compatible hardware revision with:

- dimensioned and test-printed mechanical parts;
- an installed fastener and harness schedule;
- protected split logic and retail-servo power rails;
- an open replacement HAT and `imu_to_dxl` board;
- verified 16-device Dynamixel traffic at 50 Hz;
- a policy calibrated and trained for the measured replica hardware;
- photo-based assembly, bring-up, safety, calibration, and release evidence.

This outcome does not require reproducing undocumented production electronics.

## Gate model

| Gate | Required evidence | Unlocks |
|---|---|---|
| G0 scope | target variant inventory and risk register | CAD and architecture work |
| G1 mechanical | coupons interface dimensions zero jig and clearance review | final printing |
| G2 power | measured loads reviewed protection design and combined load test | installed power hardware |
| G3 bus | one-device then 15-device tests with scope captures | IMU integration |
| G4 boards | reviewed HAT and IMU designs plus prototype bring-up | full assembly |
| G5 unpowered assembly | fastener reconciliation harness continuity and motion audit | motor power |
| G6 powered no-torque | all 16 IDs voltage temperature and IMU freshness | suspended torque-on |
| G7 suspended motion | directions home offsets init relax and hard disconnect | supported stand |
| G8 supported stand | bounded current temperature tilt and no brownouts | floor testing |
| G9 trained policy | smoke test evaluation export and CPU rehearsal | tethered walking |
| G10 sim2real | aligned traces safety limits and accepted walking evaluation | release |

No downstream success may waive a failed upstream gate. For example a policy
that walks briefly does not waive an over-temperature or bus-error failure.

## Phase summary

### 0–1. Scope and evidence

Freeze `safe-replica-v0`, inventory actual parts, retain source revision and
license provenance, and replace inferred dimensions whenever a physical or
official measurement becomes available.

### 2. Mechanical engineering

Convert simplified simulation meshes into separately versioned manufacturing
candidates. Validate printer- and material-specific holes, bearings, inserts,
wall thickness, horn zero, cable strain relief, and full-range collision before
final printing.

### 3–7. Power, bus, IMU, HAT, and vision

Measure before selecting power components. Prototype the Dynamixel electrical
layer with one device before a full chain. Treat the replacement HAT and ID200
IMU board as ordinary hardware products: requirements, schematic review, ERC,
DRC, fabrication, serialized bring-up, and evidence retention.

### 8–9. Assembly and software bring-up

Build and test legs, head, and trunk as independent subassemblies. Complete a
signed continuity matrix before inserting a battery. Bring up logic, one servo,
one leg, fifteen servos, and then the ID200 board. Torque-on is a separate gate
performed only on a stand.

### 10–11. Retraining and sim2real

Measure the selected safe voltage rail and actuator response. Update BAM without
breaking non-accumulating randomization or the 61D observation contract. Run the
mandatory smoke test before training. Export only through the normalizer-aware
exporter. Progress from suspended motion to supported stand and tethered walking
using synchronized current, temperature, joint, IMU, and video evidence.

### 12. Release

Replace stock estimates with installed counts. Publish complete editable source
for boards, firmware, calibration, fixtures, and manufacturing derivatives.
Release only one immutable hardware/software identity with hashes and a fresh
reproduction record.

## Work rules

- `P0` tasks block all dependent physical work.
- `blocked` means a named external input is absent; it never means a guessed
  value may be substituted.
- A quantity with low confidence is procurement stock only until dry-fit turns
  it into an installed count.
- Keep model evidence, runtime evidence, third-party inference, and design
  choices distinct in the BOM.
- Do not overwrite simulation STL assets with manufacturing edits.
- Any voltage, current, temperature, or impact limit must have a source or a
  measured acceptance test.
- Use two-person sign-off for first battery connection and first torque-on.
- Preserve raw logs and photos; summaries alone are not release evidence.

## Definition of done

The project is complete only when every `P0` task is complete, all release tasks
are complete, no unresolved `blocked` task affects the built configuration, and
a second builder can reproduce the robot from the tagged sources without oral
instructions.

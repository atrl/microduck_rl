# `imu_to_dxl` bench prototype v0.1 manufacturing package

This directory contains the dated files exported from the private JLCEDA
project `Microduck-imu_to_dxl-prototype` on 2026-09-01. It is an order package
for a bench/end-node prototype, not evidence that the board fits the final
robot enclosure.

## Order inputs

- `imu_to_dxl_v0_1_gerber.zip`: copper, solder mask, silkscreen, outline and
  drill files; upload this for bare-PCB fabrication.
- `imu_to_dxl_v0_1_bom_jlceda.xlsx`: unmodified JLCEDA BOM export. It includes
  D1, D2 and J2 for traceability even though all three are DNP for v0.1.
- `imu_to_dxl_v0_1_cpl_jlceda.xlsx`: unmodified JLCEDA pick-and-place export.

## Mandatory order settings

- FR-4, 2 layers, 1.6 mm, 1 oz outer copper, green solder mask, white
  silkscreen, 45.0 x 25.0 mm, quantity 5.
- J1 is the only populated bus connector and is hand-soldered after SMT.
- Do not populate D1, D2 or J2. In the SMT component-confirmation page, mark
  all three designators `DNP` before accepting the placement preview.
- J2 is not a servo-power pass-through. The board is an end node and only
  draws its own approximately 25 mA from J1.
- R4 and R5 start at 0 ohm. Do not substitute active parts without a schematic
  review.

## Verified checks and remaining warnings

- JLCEDA PCB DRC: 0 errors, 124 checks, 2026-09-01 22:39:30.
- JLC online DFM task: `DFMP2609010916`; Gerber parsed as 2 layers,
  4.5 x 2.5 cm, minimum line width 0.24 mm, minimum clearance 0.20 mm,
  minimum drill 0.30 mm and minimum annular ring 0.15 mm.
- Online DFM reports two 1.85 mm through-hole-to-SMD clearance red items around
  the connector region. J1 is hand-soldered and J2 is DNP; inspect this region
  after assembly.
- Online DFM reports one 0.05 mm solder-mask-opening-to-trace red item near J3.
  Require production-file review and AOI/microscope inspection; quarantine a
  board if solder or exposed copper bridges adjacent J3 nets.
- Silkscreen proximity/width findings may be clipped by fabrication and are
  not electrical acceptance evidence.

The JLC web quote observed on 2026-09-01 was CNY 40 for five bare boards in the
web order flow (the DFM estimator showed CNY 20) and CNY 211.81 for SMT before
DNP reconciliation. Prices, stock and lead time are snapshots and must be
rechecked at checkout.

## File integrity

Run `shasum -a 256 imu_to_dxl_v0_1_*` in this directory before uploading. The
2026-09-01 export hashes are:

```text
33c39e54cb25dc6e912cd03eeb405813d8fc6825139a09b2733d8e8aefad1bc7  imu_to_dxl_v0_1_bom_jlceda.xlsx
58a26889deb36d4438ff79711d618a2cb0b8be750c618c561e1a1fe5a2d8500f  imu_to_dxl_v0_1_cpl_jlceda.xlsx
8fee6a12faf76bbeaf4d83d3b3e80c6f33418128ce2b5a7c9f4a1a8782e4b619  imu_to_dxl_v0_1_gerber.zip
```

Do not upload a locally edited BOM/CPL under the original export names.

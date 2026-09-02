# `imu_to_dxl` bench prototype v0.2 manufacturing package

This directory contains the production files exported from the private JLCEDA
project `Microduck-imu_to_dxl-prototype` on 2026-09-02. The v0.2 package is
ready for a five-board bench/end-node prototype order. It is not evidence that
the board fits the final robot enclosure.

## Current order inputs

- `imu_to_dxl_v0_2_gerber.zip`: upload this for bare-PCB fabrication.
- `imu_to_dxl_v0_2_bom_jlceda.xlsx`: upload this for SMT assembly.
- `imu_to_dxl_v0_2_cpl_jlceda.xlsx`: upload this as the component placement
  file.

The v0.2 BOM has 12 production groups and the CPL has 22 component rows. D1,
D2 and J2 were removed from the schematic, PCB, BOM and CPL; there is no manual
DNP reconciliation. J1 is the one through-hole row (`SMD=No`), leaving 21 SMT
placements. Confirm that J1 is not machine-placed and solder it after SMT.

The `imu_to_dxl_v0_1_*` files are retained only as a superseded audit record.
Do not upload them for a new order.

## Order settings

- FR-4, 2 layers, 1.6 mm, 1 oz outer copper, green solder mask, white
  silkscreen, 45.0 x 25.0 mm, quantity 5.
- J1 is the only bus connector. This board is an end node; do not route servo
  power through it or add a downstream connector without a new layout review.
- R4 and R5 are 0 ohm in this revision. Do not substitute them without a
  one-servo oscilloscope capture and schematic review.
- Select SMT assembly for the 21 `SMD=Yes` placements. J1 must be excluded from
  machine placement and hand-soldered afterward.
- A stencil is not required for the assembled-board order unless separate
  manual rework is planned.
- Use manual production-file confirmation. Two confirmation passes are
  preferred for this first electrical prototype, although the second pass is
  a paid checkout option.
- Review the default finish and quality-indemnity options before payment. A
  lead-free finish is preferred for handling, but price and process choices
  remain checkout decisions.

## Verification evidence

- JLCEDA schematic check: 0 fatal, 0 error, 0 warning, 18 informational empty
  `Value` notices; 2026-09-02 12:55:20.
- JLCEDA PCB DRC: `All (0)`, 124 checks; 2026-09-02 12:54:10.
- The Gerber contains 38 top-layer and 4 bottom-layer copper areas. Ground
  pours are therefore present in the production export, not merely in the
  editor view.
- JLC online DFM task `DFMP2609020362` parsed the board as 2 layers,
  4.5 x 2.5 cm, minimum line width 0.24 mm, minimum spacing 0.10 mm, minimum
  drill 0.30 mm and minimum annular ring 0.15 mm.
- Critical DFM red counts are zero for trace spacing, pad-on-hole,
  trace-to-edge, dangling traces, PTH-to-line, annular ring, PTH-to-SMD,
  via-to-pad and exposed copper near solder-mask openings.
- The remaining red findings are silkscreen-to-pad/hole clearance and three
  silkscreen-width items. Fabrication may clip that reference silkscreen; it is
  not copper, mask, drill or connectivity acceptance evidence.
- The JLC order checker accepted the v0.2 Gerber and populated the board
  dimensions and layer stack without a file error.

The 2026-09-02 estimator snapshot was CNY 20 for PCB and CNY 211.47 for SMT,
with estimated one-day PCB and two-day SMT production. The order page also
showed optional fees. Prices, stock, shipping and lead time must be rechecked
at checkout.

## File integrity

Run `shasum -a 256 imu_to_dxl_v0_2_*` in this directory before uploading. The
current export hashes are:

```text
f97b23ee7591972f90a40496acf245c9bd82b9956d7d0b4db393def2ceedb60f  imu_to_dxl_v0_2_bom_jlceda.xlsx
de717a241c9407b4b0932f892467e573b482d1936aee77b8de7e62025f64f090  imu_to_dxl_v0_2_cpl_jlceda.xlsx
76a9de183a998e3e5e8aa8490abc283e733a0f624145d37fb3a87c1ff9495d00  imu_to_dxl_v0_2_gerber.zip
```

Do not modify a BOM/CPL while keeping these filenames and hashes. Any design
or placement change requires a new revision and a fresh DRC/DFM run.

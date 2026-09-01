# `imu_to_dxl` v0 completion and bring-up guide

This guide starts from the reviewed JLCEDA P1 schematic and ends at the full
sixteen-device timing gate. It does not authorize fabrication or robot power by
itself. Every STOP below requires the named evidence.

## 1. Close the design inputs

Before converting the schematic to PCB:

1. Measure the available trunk volume and the exact board mounting points.
2. Record the desired JST cable-entry directions and service-loop clearance.
3. Hold an actual XL330 cable against a printed connector/board coupon and
   confirm JST pin 1/2/3 orientation.
4. Fix the board coordinate frame and write the required LSM6DSV16X X/Y/Z
   orientation on a mounting drawing. The runtime expects
   `trunk = [+raw_z, +raw_y, -raw_x]` with its current default mount.
5. Independently compare every active part's symbol pin numbers and footprint
   pads with its manufacturer datasheet.
6. Resolve the two JLC library audit items recorded in
   [`imu_to_dxl_v0_design.md`](imu_to_dxl_v0_design.md): Y1 pin naming and U4
   enable labeling.

**STOP I-01:** no PCB conversion until the dimensioned mounting drawing and
signed pin/footprint checklist exist.

## 2. PCB layout rules

Use a two-layer prototype first. Four layers are not justified until measured
signal or EMI evidence requires them.

1. Place J1/J2 first at the measured cable edges; keep pins and silk polarity
   identical on both connectors.
2. Place D1/D2 at the connector entry but mark both DNP in assembly data.
3. Place U3 between the connector data node and U1. Keep DXL_DATA compact and
   keep R4/R5 accessible for rework.
4. Place U4 and its input/output capacitors as a tight local loop. DXL_VDD is a
   branch supply for this board only and must not carry servo current through a
   narrow trace.
5. Place U2 on a rigid area away from connectors, board edges, the LDO and the
   crystal. Match the recorded sensor-axis orientation and print an axis triad
   on silkscreen.
6. Place U2's two 100 nF capacitors at pins 5 and 8. Use a continuous ground
   return under the IMU; do not route the 1 Mbps bus or crystal beneath it.
7. Place Y1 and C1/C2 next to U1 PF0/PF1 with short symmetric traces and no
   test-pad stubs.
8. Keep the SWD header and reset node reachable after assembly. Provide test
   points for 3V3, GND, DXL_DATA, MCU_TX, MCU_RX and TX_ENABLE.
9. Use a ground pour on both layers with frequent stitching. Keep the bus trace
   away from crystal and IMU SPI clocks where practical.
10. Add fabrication notes: D1/D2 DNP, R4/R5 initially 0 Ω, do not substitute
    active parts without schematic re-review.

Run PCB DRC with the actual manufacturer's clearance rules and inspect the 3D
view against the measured trunk envelope.

**STOP I-02:** fabrication requires zero unexplained schematic/PCB DRC errors,
the independent review, and exported source plus Gerber/drill/placement/BOM
files saved with hashes.

## 3. Prototype order

Order three boards after STOP I-02:

- board A: normal bring-up;
- board B: destructive/protection and hot-plug testing;
- board C: untouched comparison/spare.

Do not populate D1 or D2 on the first assembly. Populate R4/R5 with 0 Ω. Use the
exact active-part revisions in [`imu_to_dxl_v0_bom.csv`](imu_to_dxl_v0_bom.csv)
unless a reviewed change record approves a substitute.

Archive the JLC order configuration, manufacturing warnings, assembled-board
photos and component lot markings. An accepted order is not proof of electrical
correctness.

## 4. Firmware milestones

Create a separately versioned firmware project for STM32G030C8T6. Start from ST
CMSIS/LL or HAL plus the official `lsm6dsv16x-pid` driver; keep third-party
licenses and commit SHAs.

### F0: board minimum

- 8 MHz HSE startup with clock-failure handling;
- SWD flash/debug and NRST;
- watchdog;
- a bounded fault status retained for debugger inspection;
- 3V3 and current measurements at idle.

### F1: IMU

- WHO_AM_I check and software reset;
- SPI mode 0 or 3 at ≤10 MHz;
- ±500 dps gyro, ±4 g accelerometer;
- gyro/accelerometer/SFLP 120 Hz;
- FIFO parsing using ST's sensor-fusion example;
- latest complete gyro plus quaternion snapshot copied atomically;
- quaternion remains all-zero until a valid SFLP frame is received.

### F2: Dynamixel slave

- Protocol 2.0 framing, byte stuffing and CRC;
- ID 200 and 1 Mbps fixed for v0;
- Ping and Read response;
- Sync Read response for address 124 length 12;
- reject unsupported address/length without reading past the register table;
- TX_ENABLE defaults low and is asserted only for the response interval;
- bus idle and collision timeouts always return U3 to receive mode.

### F3: diagnostics

Keep registers 136–143 reserved until their public contract is available. Put
development counters behind a separate debug build or SWD; do not silently
invent a runtime-visible layout.

Unit tests must cover CRC vectors, stuffing boundaries, malformed length,
broadcast/sync-read parsing, little-endian gyro packing, fp16 edge cases,
all-zero startup and atomic-snapshot concurrency.

## 5. Unpowered inspection

For each serialized board:

1. Photograph both sides at sufficient resolution to read markings.
2. Inspect LGA/LQFP bridges, polarity and connector pin order.
3. Measure resistance from DXL_VDD to GND and 3V3 to GND before power.
4. Verify continuity for every net in the reviewed schematic.
5. Verify D1/D2 are not populated and R4/R5 are 0 Ω.
6. Verify J1 and J2 are pin-for-pin parallel.

**STOP I-03:** any unexpected short, open, swapped connector pin or unreviewed
substitution quarantines the board.

## 6. Power bring-up

Use a current-limited bench supply; do not use the robot battery.

1. Begin at 3.7 V with a conservative current limit and no Dynamixel cable.
2. Confirm 3V3 before connecting the debugger or enabling firmware.
3. Record input current, 3V3 ripple, U4 temperature and reset behavior.
4. Repeat at 5.0 V and 6.0 V.
5. Sweep load/temperature sufficiently to confirm U4 remains in regulation.
6. Test controlled power cycling and brownout. Use board B for any hot-plug or
   protection experiment.

Stop on overcurrent, oscillation, reset loops, rail overshoot or unexpected
heating.

## 7. Sensor validation

With no Dynamixel bus attached:

1. Verify WHO_AM_I and configuration readback.
2. Confirm SFLP produces fresh frames at the selected rate.
3. Hold each board face up/down and rotate about each marked axis.
4. Compare raw gyro scale with a reference motion fixture.
5. Confirm packed fp16 X/Y/Z reconstructs a unit quaternion within the runtime
   tolerance and matches the documented trunk transform.
6. Freeze the sensor stream deliberately and verify stale detection inputs.

Archive raw SPI/FIFO logs and the conversion script; a video alone is not the
acceptance record.

## 8. One-servo bus gate

Connect J1 to a U2D2 or reviewed host interface and J2 to one XL330. Power the
board and servo from the regulated rated-voltage rail with torque disabled.

1. Verify only the servo ID and ID200 answer Ping.
2. Send Read and Sync Read for ID200 address 124 length 12.
3. Capture DXL_DATA, MCU_TX, MCU_RX and TX_ENABLE around a complete transaction.
4. Check response delay, stop-bit release, idle level, overshoot and ringing.
5. Count errors over a long run at 1 Mbps.
6. Try R4/R5 = 33 Ω only if the captured waveform justifies it; record the
   before/after evidence.

**STOP I-04:** do not attach the full servo chain until there are no collisions
and the packet-error target is reviewed.

## 9. Full runtime gate

After the fifteen-servo bus has independently passed its own gate:

1. Attach ID200 as the sixteenth node with all servo torque disabled.
2. Run the official runtime on `/dev/ttyS2` at 1 Mbps.
3. Confirm every 50 Hz combined Sync Read returns 16 blocks and ID200 returns
   exactly 12 bytes.
4. Confirm gyro scale, orientation, ready state and stale counters are plausible.
5. Record loop timing, packet errors, 3V3 ripple and board temperature.
6. Repeat with representative cable motion and servo electrical noise while
   keeping torque and mechanical risk bounded.

Only after this gate may `I1-06` and `I1-07` in `work_plan.csv` be completed.
Robot installation still requires the global power, harness, unpowered assembly
and suspended-motion gates.

## Evidence package

Keep the following under an immutable hardware revision:

- editable JLCEDA source and exports;
- board BOM with supplier/manufacturer identities;
- schematic DRC and netlist review;
- PCB DRC, Gerbers, drill, placement and assembly drawings;
- firmware source, toolchain lock, unit-test logs and binary hashes;
- board serial numbers and photos;
- power, oscilloscope, sensor-motion and full-bus raw logs;
- reviewer checklist and resolved actions.


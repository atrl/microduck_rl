# Provisional assembly and wiring guide

This is a gated reconstruction guide for `safe-replica-v0`. It is intentionally
not a production assembly manual: the public project does not contain official
board schematics, harness dimensions, horn-zero drawings, or manufacturing
tolerances. Any step marked **STOP** must be closed by the evidence named below
before physical work continues.

## Safety boundaries

- Retail XL330-M288-T input is rated 3.7–6.0 V. Do not connect a fully charged
  2S pack directly to the servo rail using this guide.
- Configure one factory servo at a time. Multiple factory-default servos on one
  bus share an ID and cannot be identified safely.
- Never connect, disconnect, or crimp the three-wire bus while energized.
- Keep torque disabled until polarity, continuity, IDs, home offsets, and joint
  directions have all been checked.
- First torque-on must happen on a stable suspended stand with a reachable hard
  disconnect.
- Original STL files are simplified simulation meshes. Print fit coupons before
  committing to load-bearing parts.

## 1. Mechanical chain and actuator identity

The current runtime uses fifteen actuators. Fourteen appear in the policy action
vector; the mouth actuator is controlled separately.

```text
trunk_base
├─ left leg
│  └─ 20 left_hip_yaw
│     └─ 21 left_hip_roll
│        └─ 22 left_hip_pitch
│           └─ 23 left_knee
│              └─ 24 left_ankle
├─ neck and head
│  └─ 30 neck_pitch
│     └─ 31 head_pitch
│        └─ 32 head_yaw
│           └─ 33 head_roll
│              └─ 34 mouth
└─ right leg
   └─ 10 right_hip_yaw
      └─ 11 right_hip_roll
         └─ 12 right_hip_pitch
            └─ 13 right_knee
               └─ 14 right_ankle
```

The `imu_to_dxl` board is bus ID `200`. The runtime's authoritative constants
are in:
<https://github.com/pollen-robotics/microduck/blob/main/duck-control/src/model.rs>.

## 2. Prepare before printing

1. Import the current STL and MJCF transforms into editable CAD.
2. Preserve the checked-in simulation assets; create manufacturing derivatives
   in a separate directory and retain CC BY-SA-NC attribution.
3. Dimension servo faces, horn interfaces, bearing seats, shell joints, PCB
   mounting holes, and every inferred fastener stack.
4. Print coupons for M2 clearance holes, M2 heat-set inserts, 16 x 22 x 4 mm
   bearings, and approximately 10 x 15 x 3 mm bearings in every final material
   and print orientation.
5. Record measured compensation rather than scaling whole parts.

**STOP M-01:** do not print final load-bearing parts until coupon dimensions,
insert pull-out strength, and bearing fits are recorded.

## 3. Configure and label actuators

Use a current-limited supply at a voltage within the XL330 rating and a U2D2 or
equivalent interface.

For each servo separately:

1. Connect `GND`, rated `VDD`, and `DATA` with power off.
2. Power it and confirm the factory device is the only responder.
3. Set Dynamixel Protocol 2.0 and baud rate to 1 Mbps.
4. Assign its target ID from the mechanical chain above.
5. Set and verify `return_delay_time=0`. The runtime also checks this at startup.
6. Move at low current to the documented zero fixture position.
7. Disable torque; label the servo body and both cable ends with ID and joint.
8. Save a scan log and repeat for the next servo.

**STOP M-02:** the public project does not contain an official horn-spline zero
drawing. A repeatable zero fixture and home-offset record must exist before the
servo horns are tightened.

## 4. Assemble mechanical subassemblies

Route cables while each chain is open. Do not rely on feeding connectors through
closed joints later.

### 4.1 Left and right legs

For each side:

1. Assemble hip yaw bracket and its opposite-side bearing support.
2. Add hip roll structure and verify the bearing and servo axes are coaxial.
3. Add the side-specific upper leg and rigidity plate around the hip-pitch
   servo.
4. Add the lower leg around the knee servo.
5. Add the ankle servo and normal foot or roller chassis.
6. Move every joint manually through its intended range with the harness
   installed but torque disabled.
7. Verify no cable carries tension at either limit and connectors cannot touch
   moving horns.

The normal walking build uses `ankle_left/right`, `foot_left/right`, and
`sole_left/right`. The roller build replaces those interfaces with
`ankle_l/r_v1`, two `roller_blade` parts, four rims, and four tires. Wheel axle,
spacer, and retention details remain `needs_confirmation` in the BOM.

### 4.2 Neck head and mouth

1. Assemble the two neck side structures around ID30.
2. Install the head-pitch structure and ID31 with its opposing bearing.
3. Install the yaw-roll linkage and ID32.
4. Install the head-roll structure and ID33.
5. Fit ID34 and the mouth linkage without the flexible mouth skins.
6. Exercise the mouth manually from the runtime range of -5 degrees closed to
   +30 degrees open.
7. Route the camera ribbon, ToF cable, audio wiring, and motor bus before fitting
   the top and bottom shells.
8. Fit flexible mouth parts only after hard-part travel is clear.

The current MJCF contains the fifteenth servo's visual geometry but not a
controlled mouth joint, so mouth linkage geometry needs physical or official-CAD
confirmation.

### 4.3 Trunk

1. Install the two hip subassemblies and neck base into `trunk_base`.
2. Install the power support, safe power prototype, Radxa, replacement HAT, and
   service disconnect.
3. Keep battery and servo power disconnected while completing the harness.
4. Verify the battery is mechanically retained in every robot orientation.
5. Close left and right shells only after the continuity matrix and full bus scan
   pass.

## 5. Electrical topology

```text
protected 2S battery input
├─ fuse + reverse-polarity + inrush protection + hard disconnect
├─ regulated 5 V logic rail
│  └─ Radxa Zero 3W
│     ├─ MIPI CSI ─────────────── IMX219 camera
│     ├─ I2C3 pin 3/5 ────────── VL53L8CX and selected audio control
│     ├─ I2S ─────────────────── codec or output-only amplifier
│     └─ UART2 /dev/ttyS2
│        └─ automatic half-duplex 3.3 V TTL interface
│           └─ DATA
└─ regulated servo rail no greater than 6 V for retail XL330
   ├─ VDD and common GND ─────── 15 x XL330
   └─ VDD and common GND ─────── replacement imu_to_dxl ID200
```

Every Dynamixel node is on the same multidrop bus. The physical cable order does
not define joint order; unique IDs do. The runtime opens `/dev/ttyS2` at 1 Mbps
and expects sixteen responders.

### XL330 connector

| Pin | Signal |
|---:|---|
| 1 | GND |
| 2 | VDD |
| 3 | DATA |

Connector reference:
<https://emanual.robotis.com/docs/en/dxl/x/xl330-m288/#connector-information>.
The host UART must pass through a half-duplex circuit. Do not tie TX and RX to
DATA without a reviewed interface.

### Peripheral wiring contracts

- Camera: IMX219-class module over MIPI CSI; cable length and contact orientation
  must be confirmed against the chosen Radxa and camera modules.
- ToF: VL53L8CX-class module on I2C address `0x29`; use the replacement HAT's
  keyed four-wire connector.
- Audio: original source targets TLV320AIC3104. A safe replica may use an
  output-only I2S amplifier when microphone capture is not required.
- IMU: LSM6DSV16X is not wired directly to the host. The replacement board must
  act as a Dynamixel Protocol 2.0 slave at ID200 and serve the runtime's register
  block.

The reviewed v0.2 replacement-board contract and board-level BOM are in
[`imu_to_dxl_v0_design.md`](imu_to_dxl_v0_design.md) and
[`imu_to_dxl_v0_bom.csv`](imu_to_dxl_v0_bom.csv). The 45 x 25 mm no-hole
end-node bench board may be ordered from the hashed package in
[`manufacturing/`](manufacturing/). D1, D2 and J2 are absent from v0.2, and J1
is hand-soldered after SMT. Use a passive splitter/Y harness for the one-servo
test because this board is not a servo-power pass-through. It
must not be installed in the robot until the measured outline, mounting holes,
sensor-axis orientation, independent review, and one-servo power/bus gates in
that document pass.

## 6. Harness audit before power

Create a continuity matrix containing every connector and both endpoints. With
no battery installed:

1. Confirm no short exists from either power rail to ground.
2. Confirm every connector's pin 1/2/3 maps to GND/VDD/DATA.
3. Confirm logic and servo grounds are common at the designed point.
4. Confirm the 5 V and servo rails are not shorted together.
5. Pull-test every crimp and inspect that no terminal can back out.
6. Move all joints manually and repeat continuity tests at the motion limits.
7. Confirm the hard disconnect opens the battery path.

**STOP E-01:** two-person sign-off is required on polarity and rail separation
before the battery or bench supply is connected.

## 7. Staged electrical bring-up

1. Power the logic rail from a current-limited bench supply with motor power off.
2. Boot Radxa and confirm the configured UART appears as `/dev/ttyS2`.
3. Power one servo through the regulated servo rail and verify packets on an
   oscilloscope.
4. Add one leg and repeat the load and bus tests.
5. Add all fifteen servos with torque disabled and scan IDs.
6. Add the ID200 IMU board; require fresh samples and a complete sixteen-device
   read at 50 Hz.
7. Run `robotctl health` and archive the JSON output.
8. Compare the reported voltage with an independent meter before trusting it.

Do not continue if the bus shows duplicate IDs, missing blocks, reversed joint
labels, unexpected heating, brownouts, or voltage outside a component's rating.

## 8. First motion

1. Mount the completed robot on the suspended stand.
2. Keep a person at the hard disconnect.
3. With torque off, verify all joint angles and home offsets in telemetry.
4. Enable only the initialization ramp:

   ```bash
   sudo robotctl robot init
   ```

5. Stop immediately if any joint moves in the wrong direction or current rises
   unexpectedly:

   ```bash
   sudo robotctl robot relax --yes
   ```

6. Test software relax and the physical disconnect independently.
7. Do not place the robot on the floor until suspended motion and supported-stand
   gates in `work_plan.csv` pass.

## 9. Policy compatibility

The current policies and BAM calibration were built around a different voltage
contract. A regulated retail-servo build must identify its actuator response,
update BAM and non-accumulating domain randomization, run the mandatory 64-env
five-iteration smoke test, train, export through `scripts/export.py`, and rehearse
the ONNX with `scripts/infer_policy.py` before real walking.

## Reference drawings

Third-party exploded drawings derived from the official MJCF are useful for
orientation but are not manufacturing authority:

- <https://github.com/fanhao375/microduck-replica/tree/master/assembly-drawings>
- <https://github.com/fanhao375/microduck-replica/blob/master/docs/%E7%B4%A7%E5%9B%BA%E4%BB%B6%E5%8F%8D%E6%8E%A8.md>

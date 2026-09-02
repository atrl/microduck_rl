# `imu_to_dxl` safe-replica v0.2 design

Status: **bench prototype order package ready / final robot fit not approved**

This document freezes a reproducible replacement for the unpublished
`imu_to_dxl` v2 board used by the current Microduck runtime. It does not claim
to reproduce Pollen Robotics' PCB. The design is intentionally limited to the
IMU bus node; the Radxa host half-duplex interface and the robot power board are
separate designs.

## Verified external contract

The current `pollen-robotics/microduck` runtime establishes the following wire
contract:

- Dynamixel Protocol 2.0 slave ID `200`, TTL half-duplex, `1,000,000` baud.
- The board is first in a 16-device Sync Read with fifteen XL330 servos.
- Read address `124`, length `12`, at a 50 Hz control-loop cadence.
- Bytes `0..5`: signed little-endian gyro X/Y/Z at ±500 dps,
  `17.5 mdps/LSB`.
- Bytes `6..11`: SFLP game-rotation quaternion X/Y/Z as IEEE-754 binary16;
  the host reconstructs positive `w = sqrt(max(0, 1-x²-y²-z²))`.
- All-zero quaternion bytes mean SFLP is not ready. The host retains the last
  valid quaternion and requires 25 live quaternion reads before declaring the
  IMU ready.
- Twenty-five consecutive identical IMU blocks trigger a stale-data warning.

The public runtime mentions a 20-byte diagnostic block but does not publish the
remaining eight-byte layout. Addresses `136..143` are therefore reserved and
must not be assigned a guessed meaning in v0.

## Selected architecture

```text
J1 JST EH bus input; v0.2 is a single-connector end node
  pin 1 GND ─────────────────────────────────────────────── GND
  pin 2 DXL_VDD (3.7–6.0 V; 5.0 V recommended) ── U4 ─── 3V3
  pin 3 DXL_DATA ── U3 ROBOTIS-reference half duplex ───── USART1
                                                     └──── TX_ENABLE

3V3 ── U1 STM32G030C8T6
         ├─ SPI1 ── U2 LSM6DSV16XTR
         ├─ INT1 ── U2 INT1
         ├─ USART1 TX/RX + GPIO direction ── U3
         ├─ HSI16 internal clock + USART automatic baud detection
         └─ SWD header + reset/test points
```

### Active parts

| Ref | Selected part | Reason | JLC/LCSC evidence |
|---|---|---|---|
| U1 | STM32G030C8T6 | 64 MHz Cortex-M0+, 64 KB flash, SPI, USART, SWD, 2.0–3.6 V; LQFP-48 exposes HSE pins | `C529329`, JLC device UUID `f75337b6c21843b4a0cd684dc6f1d936` |
| U2 | LSM6DSV16XTR | exact runtime sensor; SFLP quaternion; SPI modes 0/3; VDD 1.71–3.6 V | `C5267406`, UUID `df91102e0558458ea6697768cf7c49bb` |
| U3 | SN74LVC2G241DCTR | exact topology class in the ROBOTIS 3.3 V TTL reference circuit; complementary enables provide receive/transmit steering | `C2676069`, UUID `fd706ee9f5e94b91833cadb369e166b1` |
| U4 | LP2985-33DBVR | 3.3 V, 150 mA LDO, 2.5–16 V input and low dropout; preserves margin at the XL330 minimum rail | `C95414`, UUID `fbb1d5eb191a4646aa282b0c9bd9afc6` |
| J1 | JST B3B-EH-A(LF)(SN) | exact XL330 mating-family PCB header, pins GND/VDD/DATA; hand-solder after SMT | `C160259`, UUID `c8e6f5be2cdb4d1fb379fcd625589b0c` |
| J3 | HCTL PZ127-2-05-S | orderable 2x5 1.27 mm SMT SWD header | `C3975188`, UUID `72524cb4eb6742dc93f30d3f1de759b8` |

Stock observations are a dated sourcing snapshot, not a purchase order. On
2026-09-01 the LCSC/JLC pages showed stock for U1–U4, J1 and J3. Stock and exact
revision must be rechecked immediately before ordering.

## Schematic rules

### Bus and transceiver

Use the ROBOTIS XL330 reference topology around U3:

- `DXL_DATA -> U3.1A`, `U3.1Y -> MCU_RX`.
- `MCU_TX -> U3.2A`, `U3.2Y -> DXL_DATA`.
- Tie active-low `1OE` and active-high `2OE` to `TX_ENABLE`.
- `TX_ENABLE` has a 10 kΩ pull-down so reset defaults to receive mode.
- `MCU_RX` and `DXL_DATA` each have 10 kΩ pull-ups to 3V3, matching the
  ROBOTIS reference.
- Place 33 Ω series resistors at the U3 bus-facing pins as tuning footprints;
  begin with 0 Ω/33 Ω only after one-servo scope captures.
- v0.2 intentionally has no unvalidated data-ESD or rail-TVS footprint. Add
  protection only in a later revision after leakage, clamping, hot-plug and
  1 Mbps waveform measurements select exact parts.

The MCU controls direction in firmware. This is allowed for the ID200 board;
the separate host HAT remains constrained by the current runtime, which exposes
no direction GPIO.

### Power

- Bench v0.2 is an end node with J1 only. D1, D2 and J2 do not exist in its
  schematic, PCB, BOM or CPL. Do not use the board to pass servo current to a
  downstream device.
- The board operating input is the retail XL330 rail, 3.7–6.0 V, with 5.0 V
  recommended by ROBOTIS. It must not be connected to an unregulated 2S pack.
- U4 input: 1 µF X7R plus 10 µF local bulk; output: 4.7 µF X7R plus 100 nF.
- Tie U4 `ON/OFF` to DXL_VDD. A future power TVS must not be added until rail
  transient measurements select its standoff and clamp energy.
- Target board current is below 25 mA. Verify at 3.7 V and 6.0 V across cold,
  room and warm conditions; 3V3 must remain in both MCU and IMU limits.
- U1 follows ST's one 100 nF plus one 4.7 µF supply scheme; VREF+ receives
  100 nF. U2 VDD and VDD_IO each receive 100 nF at the pins.

### MCU pin assignment

| U1 signal | Pin/function | Net |
|---|---|---|
| PF0 / PF1 | unused | NC; configure as analog inputs |
| PA4 | SPI1_NSS | IMU_CS |
| PA5 | SPI1_SCK | IMU_SCK |
| PA6 | SPI1_MISO | IMU_MISO |
| PA7 | SPI1_MOSI | IMU_MOSI |
| PA0 | GPIO input | IMU_INT1 |
| PA9 | USART1_TX | MCU_TX |
| PA10 | USART1_RX | MCU_RX |
| PB0 | GPIO output | TX_ENABLE |
| PA13 / PA14 | SWDIO / SWCLK | J3 SWD |
| NRST | reset | 10 kΩ pull-up, 100 nF to GND, SWD reset |

All unused GPIOs remain unconnected in the schematic and are configured as
analog inputs in firmware. VBAT is tied to 3V3 because v0 has no backup supply.
Bench v0.2 uses the STM32 HSI16 oscillator and USART1 automatic baud-rate
detection. Configure `ABRMOD=00` so the first start bit in the Dynamixel
`0xFF 0xFF 0xFD 0x00` header updates BRR before any reply. Firmware must fail
closed on `ABRE`, missing `ABRF`, framing error or timeout; it must never
transmit with an unvalidated BRR. Scope verification across 3.7/5.0/6.0 V and
the intended temperature range remains a hardware acceptance gate.

### IMU mode and mounting

- Use primary 4-wire SPI, mode 0 or 3, at no more than 10 MHz.
- Tie U2 VDD and VDD_IO to 3V3. Place separate 100 nF capacitors directly at
  pins 8 and 5.
- In mode 1, pins 2 and 3 are tied to GND because analog hub/Qvar are disabled.
- Pins 10 and 11 are soldered but electrically unconnected as instructed by ST.
- Route INT1 to the MCU. Leave INT2 on a test pad.
- The PCB silkscreen must label the sensor X/Y/Z axes. Final PCB rotation is
  blocked until the trunk mounting orientation is measured; the runtime's
  default transform expects `trunk = [+raw_z, +raw_y, -raw_x]`.

## Firmware acceptance contract

1. Configure U2 gyro ±500 dps and accelerometer ±4 g.
2. Configure gyro, accelerometer and SFLP at 120 Hz; use the official ST driver
   and sensor-fusion example as the initialization baseline.
3. Build one atomic 12-byte snapshot whenever fresh gyro and SFLP quaternion
   data are available. Never expose a partially updated block.
4. Implement Dynamixel Protocol 2.0 Ping, Read and Sync Read response behavior,
   byte stuffing and CRC. Hard-code v0 to ID 200 and 1 Mbps until a tested
   configuration mechanism exists.
5. Turn U3 transmit on only for the status-packet interval; disable it before
   the final stop bit can collide with the next bus owner. Verify with a scope.
6. Keep quaternion bytes zero until SFLP output is valid. Increment a private
   sample counter for diagnostics, but do not publish guessed registers.
7. Unit-test packet CRC, malformed packets, address/length bounds, fp16 packing,
   gyro endianness and timeout behavior before hardware bring-up.

The portable Protocol 2.0 and Sync Read core is in
[`../../firmware/imu_to_dxl_v0_2/`](../../firmware/imu_to_dxl_v0_2/). Its host
tests cover CRC, malformed and wrong-range packets, ID selection, later-slot
timing and Status Packet stuffing. STM32 startup/DMA glue and IMU acquisition
remain hardware-dependent work.

## Verification gates

Fabrication is split into two scopes so missing robot measurements do not block
electrical learning:

- **Bench prototype v0.2:** may be ordered using the current manufacturing
  package. It has no mounting holes, is not a servo-power pass-through and is
  not approved for installation in the robot.
- **Robot-fit release:** remains blocked until the trunk envelope, mounting
  points, cable exits and required IMU axes are physically measured and the
  resulting PCB receives an independent mechanical/electrical review.

After fabrication, the prototype must still pass the following gates before it
can touch the full robot bus:

1. Independent pin-number and footprint audit against every manufacturer
   datasheet and the JLC library objects.
2. Unpowered continuity, shorts and component-orientation inspection.
3. One-servo bus test at 1 Mbps with TX-enable timing, idle voltage, overshoot,
   ringing, measured UART bit timing and packet-error captures.
4. 3.7 V / 5.0 V / 6.0 V input tests, brownout and hot-plug tests using a
   current-limited supply; no direct unregulated 2S connection.
5. Reference-motion test for gyro scale, quaternion axes, startup validity and
   stale-sample behavior.
6. Full sixteen-device 50 Hz timing test before installation in the robot.

## Current JLCEDA artifact and review result

The private JLCEDA project `Microduck-imu_to_dxl-prototype` contains schematic
page `c54e91c5cd2c5ac7` and PCB `7dfe558c7d961755` in project
`643d2ed0f25f403394217692a93e032c`. The v0.2 PCB is 45.009 x 24.994 mm,
2-layer, 1.6 mm FR-4 with 1 oz copper and no mounting holes. A fresh PCB DRC
completed 124 checks with zero issues at 2026-09-02 12:54:10; the schematic
check had zero fatal/error/warning items at 2026-09-02 12:55:20. The captured
schematic is available as
[`imu_to_dxl_v0_schematic.png`](imu_to_dxl_v0_schematic.png).

The dated Gerber, JLCEDA BOM and CPL exports are archived in
[`manufacturing/`](manufacturing/). JLC online DFM task `DFMP2609020362`
parsed the board as 2 layers and 4.5 x 2.5 cm, with 0.24 mm minimum line width,
0.10 mm minimum spacing, 0.30 mm minimum drill and 0.15 mm minimum annular
ring. Critical copper, solder-mask-opening, drill, annular-ring and PTH-to-SMD
red findings are zero. The remaining red findings concern reference
silkscreen clearance/width and may be clipped by fabrication; they do not waive
electrical inspection. The exported Gerber contains 38 top and 4 bottom copper
areas, confirming that both ground pours are in the manufacturing artifact.

The JLC web order checker accepts the Gerber and shows a five-board quote. On
2026-09-02 the DFM estimator showed CNY 20 for PCB and CNY 211.47 for SMT.
Prices and stock are volatile. Final submission/payment remains a user action
after checking shipping, tax, finish, optional fees and the generated
production preview.

U4's JLC symbol displays pin 3 as `ON/OFF#`, but the TI LP2985 datasheet defines
pin 3 as an active-high enable and explicitly instructs tying it to VIN when
shutdown is not used. The v0.2 connection from pin 3 to DXL_VDD therefore
matches the manufacturer requirement; the trailing `#` is treated as a library
label defect, not an unresolved electrical inversion.

## Primary sources

- Runtime contract: <https://github.com/pollen-robotics/microduck/blob/main/duck-control/src/imu.rs>
- Combined bus transaction: <https://github.com/pollen-robotics/microduck/blob/main/duck-control/src/bus.rs>
- IDs and baud rate: <https://github.com/pollen-robotics/microduck/blob/main/duck-control/src/model.rs>
- XL330 electrical and communication reference: <https://emanual.robotis.com/docs/en/dxl/x/xl330-m288/>
- LSM6DSV16X product and datasheet: <https://www.st.com/en/mems-and-sensors/lsm6dsv16x.html>
- ST sensor-fusion example: <https://github.com/STMicroelectronics/STMems_Standard_C_drivers/blob/master/lsm6dsv16x_STdC/examples/lsm6dsv16x_sensor_fusion.c>
- STM32G030 datasheet: <https://www.st.com/resource/en/datasheet/stm32g030c6.pdf>
- STM32 USART automatic baud-rate detection: <https://www.st.com/resource/en/application_note/an4908-getting-started-with-usart-automatic-baud-rater-detection-for-stm32-mcus-stmicroelectronics.pdf>
- SN74LVC2G241 datasheet: <https://www.ti.com/lit/ds/symlink/sn74lvc2g241.pdf>
- LP2985 datasheet: <https://www.ti.com/lit/ds/symlink/lp2985.pdf>

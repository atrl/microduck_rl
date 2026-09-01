# `imu_to_dxl` safe-replica v0 design

Status: **prototype schematic / not approved for manufacture**

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
J1/J2 JST EH bus pass-through
  pin 1 GND ─────────────────────────────────────────────── GND
  pin 2 DXL_VDD (3.7–6.0 V; 5.0 V recommended) ── U4 ─── 3V3
  pin 3 DXL_DATA ── U3 ROBOTIS-reference half duplex ───── USART1
                                                     └──── TX_ENABLE

3V3 ── U1 STM32G030C8T6
         ├─ SPI1 ── U2 LSM6DSV16XTR
         ├─ INT1 ── U2 INT1
         ├─ USART1 TX/RX + GPIO direction ── U3
         ├─ 8 MHz HSE crystal
         └─ SWD header + reset/test points
```

### Active parts

| Ref | Selected part | Reason | JLC/LCSC evidence |
|---|---|---|---|
| U1 | STM32G030C8T6 | 64 MHz Cortex-M0+, 64 KB flash, SPI, USART, SWD, 2.0–3.6 V; LQFP-48 exposes HSE pins | `C529329`, JLC device UUID `f75337b6c21843b4a0cd684dc6f1d936` |
| U2 | LSM6DSV16XTR | exact runtime sensor; SFLP quaternion; SPI modes 0/3; VDD 1.71–3.6 V | `C5267406`, UUID `df91102e0558458ea6697768cf7c49bb` |
| U3 | SN74LVC2G241DCTR | exact topology class in the ROBOTIS 3.3 V TTL reference circuit; complementary enables provide receive/transmit steering | `C2676069`, UUID `fd706ee9f5e94b91833cadb369e166b1` |
| U4 | LP2985-33DBVR | 3.3 V, 150 mA LDO, 2.5–16 V input and low dropout; preserves margin at the XL330 minimum rail | `C95414`, UUID `fbb1d5eb191a4646aa282b0c9bd9afc6` |
| J1/J2 | JST B3B-EH-A(LF)(SN) | exact XL330 mating-family PCB header, pins GND/VDD/DATA | `C160259`, UUID `c8e6f5be2cdb4d1fb379fcd625589b0c` |
| Y1 | NDK NX3225GD-8MHZ-STD-CRA-3 | external timebase for repeatable 1 Mbps timing; 8 MHz, 8 pF load | `C889706`, UUID `b3a54ecd979846b3bffdaed0d36ab1b7` |

Stock observations are a dated sourcing snapshot, not a purchase order. On
2026-09-01 the LCSC pages showed stock for U1–U4, J1/J2 and Y1. Stock and exact
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
- Add a low-capacitance data ESD footprint near J1/J2. It is DNP until leakage,
  clamping and coexistence with the 3.3 V bus are reviewed.

The MCU controls direction in firmware. This is allowed for the ID200 board;
the separate host HAT remains constrained by the current runtime, which exposes
no direction GPIO.

### Power

- J1 and J2 pass DXL_VDD directly; the board never supplies servo current.
- The board operating input is the retail XL330 rail, 3.7–6.0 V, with 5.0 V
  recommended by ROBOTIS. It must not be connected to an unregulated 2S pack.
- U4 input: 1 µF X7R plus 10 µF local bulk; output: 4.7 µF X7R plus 100 nF.
- Tie U4 `ON/OFF` to DXL_VDD. A power TVS footprint is DNP until rail transient
  measurements select its standoff and clamp energy.
- Target board current is below 25 mA. Verify at 3.7 V and 6.0 V across cold,
  room and warm conditions; 3V3 must remain in both MCU and IMU limits.
- U1 follows ST's one 100 nF plus one 4.7 µF supply scheme; VREF+ receives
  100 nF. U2 VDD and VDD_IO each receive 100 nF at the pins.

### MCU pin assignment

| U1 signal | Pin/function | Net |
|---|---|---|
| PF0 / PF1 | HSE oscillator | Y1 and two 12 pF C0G load capacitors |
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

## Verification gates

The current schematic is suitable only for review. Fabrication remains blocked
until all of the following are complete:

1. Independent pin-number and footprint audit against every manufacturer
   datasheet and the JLC library objects.
2. Electrical-rule check with no unexplained errors.
3. Board outline, mounting holes and IMU orientation measured from the target
   trunk, not inferred from a screenshot.
4. One-servo bus test at 1 Mbps with TX-enable timing, idle voltage, overshoot,
   ringing and packet-error captures.
5. 3.7 V / 5.0 V / 6.0 V input tests, brownout and hot-plug tests using a
   current-limited supply; no direct unregulated 2S connection.
6. Reference-motion test for gyro scale, quaternion axes, startup validity and
   stale-sample behavior.
7. Full sixteen-device 50 Hz timing test before installation in the robot.

## Current JLCEDA artifact and review result

The private JLCEDA project `Microduck-imu_to_dxl-prototype` currently contains
the v0 P1 schematic. The 2026-09-01 review snapshot contains 28 BOM components
and 18 named nets. A fresh strict DRC completed with zero errors and zero
warnings, and the generated netlist was checked pin-by-pin for 3V3, GND,
DXL_VDD, DXL_DATA, both transceiver-side nets, UART, SPI, HSE, reset and SWD.
The captured schematic is available as
[`imu_to_dxl_v0_schematic.png`](imu_to_dxl_v0_schematic.png).

This result clears schematic construction only. It does not clear fabrication.
Two JLC library details remain explicit audit items:

- Y1 is a physical two-terminal NDK crystal but the current library symbol calls
  terminal 2 `GND`; the netlist correctly connects it to `HSE_OUT`. Confirm the
  two-pad footprint and manufacturer drawing before PCB conversion.
- U4 library pin 3 is displayed as `ON/OFF#`, while the TI LP2985 datasheet
  defines the enable behavior. It is intentionally tied to DXL_VDD; verify the
  symbol pin number and active level against the exact orderable revision.

The DRC also reports informational empty `Value` properties on some active
devices. These are not electrical errors; supplier part numbers and footprints
remain populated in the generated netlist.

## Primary sources

- Runtime contract: <https://github.com/pollen-robotics/microduck/blob/main/duck-control/src/imu.rs>
- Combined bus transaction: <https://github.com/pollen-robotics/microduck/blob/main/duck-control/src/bus.rs>
- IDs and baud rate: <https://github.com/pollen-robotics/microduck/blob/main/duck-control/src/model.rs>
- XL330 electrical and communication reference: <https://emanual.robotis.com/docs/en/dxl/x/xl330-m288/>
- LSM6DSV16X product and datasheet: <https://www.st.com/en/mems-and-sensors/lsm6dsv16x.html>
- ST sensor-fusion example: <https://github.com/STMicroelectronics/STMems_Standard_C_drivers/blob/master/lsm6dsv16x_STdC/examples/lsm6dsv16x_sensor_fusion.c>
- STM32G030 datasheet: <https://www.st.com/resource/en/datasheet/stm32g030c6.pdf>
- SN74LVC2G241 datasheet: <https://www.ti.com/lit/ds/symlink/sn74lvc2g241.pdf>
- LP2985 datasheet: <https://www.ti.com/lit/ds/symlink/lp2985.pdf>

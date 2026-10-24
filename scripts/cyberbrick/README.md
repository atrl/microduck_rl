# CyberBrick remote → MicroDuck (TaishanPi)

Four-axis remote input bridge for the stock **CyberBrick X12 transmitter + X11 receiver** and Pollen MicroDuck **`netpadd`**. CyberBrick stays paired over its regular radio link; the receiver exposes USB-CDC text to the TaishanPi, and a host Python script sends **motion intent**, not joint angles, as UDP `DKPD` packets.

**Compatibility:** This is an input adapter, not a Feetech HD-1910/URT-2 motor driver. Only the Pollen `robotd/netpadd` protocol is targeted. The Luwu XGO-Duck / Arduino UNO Q and custom Feetech TaishanPi runtimes need a separate adapter to their real velocity/action API. Upstream has 14 XL330 joints whereas your XGO build has 15 HD-1910 servos; do **not** assume compatible gait, calibration, IMU frames, joint order, or safety.

## Compact UART installation (recommended when USB ports are occupied)

The X11's **D1 WS2812 signal** is A11 **GPIO21 = TX**, and D2 signal is **GPIO20 = RX**. Community examples reuse these as hardware UART; this PR's `receiver_main.py` now transmits the same receiver frames to UART1 **and** prints them on USB CDC for debugging. No USB host port is needed during operation.

| X11/Core A11 | TaishanPi RK3566 | Notes |
| --- | --- | --- |
| D1 **signal** (GPIO21/TX) | 40-pin **physical pin 10**, UART3_RX_M1 | **Use level conversion:** TaishanPi docs rate GPIO input maximum **3.0 V**, ESP32-C3 TX may output **3.3 V** |
| Receiver ground (DC power negative / shared GND) | physical **pin 6** GND (or any ground) | Mandatory common ground |
| X11 **XH2.54 DC supply input** | protected raw battery branch | X11 specified for **7.4–12.6 V**; a 2S Li-ion/LiPo is 8.4 V full and may fall below 7.4 V as it discharges. Verify actual rail and undervoltage behavior first. |
| D2 signal (GPIO20/RX) | Not connected | One-way control bridge; no UART return is needed |

**Voltage divider example (one-way):** X11 D1 signal → **2.2 kΩ series** → TaishanPi pin 10; a **10 kΩ resistor** from TaishanPi pin 10 to GND. With 3.3 V TX this yields about **2.70 V** at RX. Share grounds. Check actual IO rail with a multimeter and follow the applicable TaishanPi revision's electrical limits before connecting. Do not apply the X11 battery voltage to any TaishanPi GPIO. **DO NOT** use the X11 D1 3-pin connector's supply pin as a UART signal. Confirm its signal/GND pins against the PCB silkscreen and schematic before crimping.

The TaishanPi user UART3 is `/dev/ttyS3` when enabled by the board's pinmux/device tree (not the debug UART2). **Pin 8 is UART3_TX; pin 10 is UART3_RX.** Make sure your custom HAT does not already allocate these pins, and confirm the Linux UART node exists. If the HAT uses pin 10, use another free UART with device-tree setup instead of joining two outputs.

```bash
# test with the robot physically supported and all motors disabled
ls -l /dev/ttyS3
python3 scripts/cyberbrick/bridge.py --port /dev/ttyS3 --dry-run

# only when the Pollen MicroDuck netpadd runtime is installed
# and you have verified safe neutral and disconnect behavior
python3 scripts/cyberbrick/bridge.py --port /dev/ttyS3 --target 127.0.0.1
```

The original USB-CDC testing path remains available (`--port /dev/ttyACM0`).

**References:** [Bambu forum pin mapping](https://forum.bambulab.com/t/extending-the-of-inputs-and-outputs-of-transmitter-and-receiver/180026) · [TaishanPi UART3 header pinout](https://wiki.lckfb.com/zh-hans/linux-docs/linux-driver-related-subsystems/gpio-subsystem/concepts-to_configure_gpio.html) · [TaishanPi GPIO voltage caution](https://wiki.lckfb.com/zh-hans/tspi-rk3566/documentation/io-allocation-table.html)

## Preparation

1. Pair your X12 transmitter and X11 receiver in the CyberBrick tooling. Check that receiver firmware provides the official `rc_module` API.
2. **Back up** the CyberBrick receiver's stock `boot.py`, `main.py` and other startup files. Test `receiver_main.py` interactively in Thonny or `mpremote`. Do not overwrite the firmware's existing startup flow blindly. The script emits `CB,<ticks_ms>,<L1>,<L2>,<L3>,<R1>,<R2>,<R3>,<K1>,<K2>,<K3>,<K4>` about 30 times per second when the radio link is valid, and emits no `CB` frames if the RF link is gone.
3. Connect the receiver's **USB data port** to a TaishanPi USB host port. Identify `/dev/ttyACM*` or `/dev/ttyUSB*`. Do not connect the receiver to URT-2 or to the servo battery rail.
4. Install `pyserial` in the TaishanPi Python environment, support the robot so it cannot walk, and test **without UDP output**:

   ```bash
   python3 -m pip install pyserial
   python3 scripts/cyberbrick/bridge.py --port /dev/ttyACM0 --dry-run
   ```

   Check that all four axes are close to zero at rest. To calibrate, enter observed center ADC values in L2,L3,R2,R3 order:

   ```bash
   python3 scripts/cyberbrick/bridge.py --port /dev/ttyACM0 \
     --centers 2080,1960,1960,1920 --dry-run
   ```

5. **For an installed Pollen MicroDuck runtime only**, enable the unauthenticated UDP pad service on a **trusted** local network and then start bridging:

   ```bash
   sudo robotctl configure                  # set [netpad] enabled = true
   sudo systemctl restart padd netpadd
   systemctl is-active padd netpadd         # expect: inactive / active
   python3 scripts/cyberbrick/bridge.py --port /dev/ttyACM0 --target 127.0.0.1
   ```

   Keep the robot supported during initial tests, with an accessible physical power disconnect. The UDP `netpadd` port is **not authenticated**, even if the local bridge targets localhost.

## Mapping

| CyberBrick | MicroDuck |
| --- | --- |
| L2 (left horizontal) | `lx`: sideways |
| L3 (left vertical) | `ly`: forward/back |
| R2 (right horizontal) | `rx`: yaw |
| R3 (right vertical) | `ry`: head/body depending on policy mode |
| K1 (active low) | Start: robot init / mode (can cause motion) |
| K2 / K3 / K4 (active low) | A / X / D-pad Down, only with `--extra-buttons` and physical switches installed |
| L1 / R1 | intentionally unused |

ADC decreases when the stick moves right/up. `--centers` defaults are examples, not per-device calibration. The bridge intentionally leaves the deadzone to upstream pad mapping. If dry-run reveals reversed axes, correct the mapping before any physical movement.

## Link protection

- The receiver attaches its own monotonic timestamp to every frame. The host rejects reordered or excessively delayed data and drops serial backlog.
- After 200 ms with no fresh valid frame, it sends a **single neutral command** then goes silent. On clean Ctrl-C, it also sends neutral. This lets Pollen's own defaults (`stale_ms=300`, `timeout_ms=1000`) stop movement and release the client. These timeouts are **not** established for custom XGO runtimes.
- All packets are exactly 28 bytes, `DKPD` version 1, with an incrementing 32-bit sequence number, monotonic clock, 6 signed axes and active-low key mapping. No cached RF state is replayed.
- Serial unplug causes the process to exit; `netpadd` must enforce its deadman timeout. Always keep a physical power cutoff handy.

## Test without a robot

```bash
python3 -m unittest discover -s tests -p 'test_cyberbrick_bridge.py' -v
```

Tests cover parsing and bounds, four-axis calibration, active-low buttons, exact packet layout, delayed/reordered frames and receiver timestamp wrap. **USB RF latency and real servo operation have not been bench-tested.**

## Source contracts

- [CyberBrick official rc_module](https://github.com/CyberBrick-Official/CyberBrick_Controller_Core/blob/master/docs/cyberbrick_core/lib/rc_module.rst)
- [MicroDuck netpadd UDP documentation](https://github.com/pollen-robotics/microduck/blob/main/docs/robot/udp-pad.md)
- [X12 GPIO and joystick channel mapping](https://github-wiki-see.page/m/rotorman/CyberBrick_ESPNOW/wiki/CyberBrick-Transmitter-Shield-%28X12%29)

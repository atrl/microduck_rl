# CyberBrick remote → MicroDuck (TaishanPi)

Four-axis remote input bridge for the stock **CyberBrick X12 transmitter + X11 receiver** and Pollen MicroDuck **`netpadd`**. CyberBrick stays paired over its regular radio link; the receiver exposes USB-CDC text to the TaishanPi, and a host Python script sends **motion intent**, not joint angles, as UDP `DKPD` packets.

**Compatibility:** This is an input adapter, not a Feetech HD-1910/URT-2 motor driver. Only the Pollen `robotd/netpadd` protocol is targeted. The Luwu XGO-Duck / Arduino UNO Q and custom Feetech TaishanPi runtimes need a separate adapter to their real velocity/action API. Upstream has 14 XL330 joints whereas your XGO build has 15 HD-1910 servos; do **not** assume compatible gait, calibration, IMU frames, joint order, or safety.

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

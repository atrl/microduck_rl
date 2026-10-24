"""CyberBrick X11 receiver -> timestamped ASCII over UART and USB CDC.

Run as a script after pairing the standard X12 transmitter with X11 receiver.
Back up the stock CyberBrick firmware's boot files before making it permanent.

UART1 is routed to X11 D1 (A11 GPIO21 / TX) and D2 (GPIO20 / RX).
Do not connect these pins to servos or LEDs while the bridge is running.
Connect D1's signal to a TaishanPi UART RX *through a voltage divider/
level shifter*: TaishanPi's documentation rates GPIO input up to 3.0 V.
"""
import time
from machine import Pin, UART
import rc_module

# Uses a hardware UART: USB remains free for development/debugging.
uart = UART(1, baudrate=115200, tx=Pin(21), rx=Pin(20))
if rc_module.rc_slave_init() is False:
    raise RuntimeError("CyberBrick receiver initialization failed")

print("CBREADY")
while True:
    try:
        channels = rc_module.rc_slave_data()
        # None means the RF link is gone; never repeat the last control frame.
        if channels is not None and len(channels) == 10:
            line = "CB,{},{}".format(
                time.ticks_ms(), ",".join(str(int(v)) for v in channels)
            )
            uart.write(line + "\n")
            print(line)  # USB CDC debug, optional during setup.
    except Exception as exc:
        # The Linux bridge ignores all non-CB lines, then times out to neutral.
        print("CBERROR," + str(exc))
    time.sleep_ms(33)

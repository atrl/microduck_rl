"""CyberBrick X11 receiver -> timestamped ASCII on USB CDC (MicroPython).

Run as a script after pairing the standard X12 transmitter with X11 receiver.
Back up the stock CyberBrick firmware's boot files before making it permanent.
"""
import time
import rc_module

if rc_module.rc_slave_init() is False:
    raise RuntimeError("CyberBrick receiver initialization failed")

print("CBREADY")
while True:
    try:
        channels = rc_module.rc_slave_data()
        # None means the RF link is gone; never repeat the last control frame.
        if channels is not None and len(channels) == 10:
            print("CB,{},{:s}".format(
                time.ticks_ms(), ",".join(str(int(v)) for v in channels)
            ))
    except Exception as exc:
        # The Linux bridge ignores all non-CB lines, then times out to neutral.
        print("CBERROR," + str(exc))
    time.sleep_ms(33)

"""No hardware, GPU, runtime installation or pyserial needed."""
import struct
import unittest

from scripts.cyberbrick.bridge import (
    START, TICK_MODULUS, FreshnessGuard, RemoteFrame, axis,
    encode_packet, pad_state, parse_line,
)


class CyberBrickBridgeTests(unittest.TestCase):
    def setUp(self):
        self.channels = (2000, 2080, 1960, 1800, 1960, 1920, 1, 1, 1, 1)

    def test_parse_receiver_frame(self):
        line = b"CB,123," + b",".join(str(x).encode() for x in self.channels) + b"\r\n"
        self.assertEqual(parse_line(line), RemoteFrame(123, self.channels))

    def test_reject_malformed_or_out_of_range(self):
        valid = "CB,123," + ",".join(map(str, self.channels))
        for sample in ("CBREADY", "CBERROR,oh no", "CB,abc," + valid[7:],
                       valid + ",0", valid.replace(",2080,", ",4096,"),
                       valid[:-1] + "2", b"\xff", "CB,-1," + valid[7:]):
            self.assertIsNone(parse_line(sample), sample)

    def test_axes_range_and_center(self):
        self.assertEqual(axis(2080, 2080), 0)
        self.assertEqual(axis(0, 2080), 32767)
        self.assertEqual(axis(4095, 2080), -32767)

    def test_all_four_axes(self):
        axes, buttons = pad_state(RemoteFrame(1, self.channels))
        self.assertEqual(axes, (0, 0, 0, 0, 0, 0))
        self.assertEqual(buttons, 0)
        c = list(self.channels)
        c[1], c[2], c[4], c[5] = 0, 4095, 4095, 0
        axes, _ = pad_state(RemoteFrame(2, tuple(c)))
        self.assertEqual(axes[:4], (32767, -32767, -32767, 32767))

    def test_buttons_active_low_and_optional(self):
        c = list(self.channels)
        c[6:] = (0, 0, 0, 0)
        frame = RemoteFrame(3, tuple(c))
        self.assertEqual(pad_state(frame)[1], START)
        self.assertEqual(pad_state(frame, extra_buttons=True)[1],
                         START | 1 << 0 | 1 << 2 | 1 << 9)

    def test_dkpd_wire_layout(self):
        packet = encode_packet(0xFFFFFFFF, 123456, (123, -456, 0, 32767, 0, 0), START)
        self.assertEqual(len(packet), 28)
        self.assertEqual(packet[:4], b"DKPD")
        self.assertEqual(struct.unpack("<BBII6hH", packet[4:]),
                         (1, 0, 0xFFFFFFFF, 123456, 123, -456, 0, 32767, 0, 0, START))
        self.assertEqual(encode_packet(0, 0), b"DKPD\x01\x00" + bytes(22))

    def test_freshness_rejects_delayed_and_reordered_frames(self):
        guard = FreshnessGuard(max_lag_ms=150)
        self.assertTrue(guard.accept(1000, 5000))
        self.assertTrue(guard.accept(1033, 5040))
        self.assertFalse(guard.accept(1066, 5320))  # +254 ms queued
        self.assertFalse(guard.accept(1030, 5321))  # reordered
        self.assertTrue(guard.accept(1099, 5100))

    def test_tick_wrap(self):
        guard = FreshnessGuard()
        self.assertTrue(guard.accept(TICK_MODULUS - 10, 1000))
        self.assertTrue(guard.accept(20, 1030))
        self.assertFalse(guard.accept(20, 1031))


if __name__ == "__main__":
    unittest.main()

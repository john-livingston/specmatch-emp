"""Tests for specmatchemp.detrend.Detrend.

Run with ``python -m unittest tests.test_detrend`` or ``pytest tests/test_detrend.py``.
The table is written to a temporary file, so the tests do not read the
user's ~/.specmatchemp/detrend.csv.
"""
import os
import tempfile
import unittest

from specmatchemp.detrend import Detrend

TABLE = """# param, uncal_1, cal_1, uncal_2, cal_2
feh, -0.4540, -0.6, 0.4575, 0.6
radius, 1.184, 1.0, 1.748, 2.0
teff, 4000, 3900, 6000, 6100
"""


class DetrendTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._dir = tempfile.TemporaryDirectory()
        path = os.path.join(cls._dir.name, "detrend.csv")
        with open(path, "w") as f:
            f.write(TABLE)
        cls.detrend = Detrend(path)

    @classmethod
    def tearDownClass(cls):
        cls._dir.cleanup()

    def test_radius_lower_edge_is_the_table_value(self):
        self.assertAlmostEqual(self.detrend.detrend(1.184, "radius"), 1.0, places=12)

    def test_radius_upper_edge_is_the_table_value(self):
        # The range is half open, so 1.748 itself is outside and unchanged.
        self.assertAlmostEqual(self.detrend.detrend(1.747999, "radius"), 2.0, places=3)
        self.assertEqual(self.detrend.detrend(1.748, "radius"), 1.748)

    def test_radius_is_monotonic_inside_the_range(self):
        values = [1.184 + 0.564 * i / 100 for i in range(100)]
        out = [self.detrend.detrend(v, "radius") for v in values]
        self.assertTrue(all(b > a for a, b in zip(out, out[1:])))

    def test_radius_outside_the_range_is_unchanged(self):
        for value in (0.5, 1.0, 1.183, 1.748, 2.5):
            self.assertEqual(self.detrend.detrend(value, "radius"), value)

    def test_feh_is_unchanged(self):
        # Values computed before the radius fix.
        self.assertAlmostEqual(self.detrend.detrend(-0.3, "feh"), -0.3972572682391662, places=12)
        self.assertAlmostEqual(self.detrend.detrend(0.1, "feh"), 0.12934722984092162, places=12)
        self.assertAlmostEqual(self.detrend.detrend(0.4, "feh"), 0.5243006034009875, places=12)
        self.assertEqual(self.detrend.detrend(-1.0, "feh"), -1.0)

    def test_teff_is_unchanged(self):
        self.assertAlmostEqual(self.detrend.detrend(4000.0, "teff"), 3900.0, places=9)
        self.assertAlmostEqual(self.detrend.detrend(5000.0, "teff"), 5000.0, places=9)
        self.assertEqual(self.detrend.detrend(7000.0, "teff"), 7000.0)


if __name__ == "__main__":
    unittest.main()

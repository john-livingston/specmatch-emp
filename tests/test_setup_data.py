"""Tests for setup_data, the install-time data file helpers.

Run with ``python -m unittest tests.test_setup_data`` from the repository root.
"""
import csv
import os
import tempfile
import unittest
from unittest import mock

import setup_data

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class CopyIfMissingTest(unittest.TestCase):
    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.dir = self._dir.name
        self.src = os.path.join(self.dir, "src.csv")
        with open(self.src, "w") as f:
            f.write("new\n")

    def tearDown(self):
        self._dir.cleanup()

    def test_copies_when_missing(self):
        dest = os.path.join(self.dir, "dest.csv")
        self.assertTrue(setup_data.copy_if_missing(self.src, dest))
        with open(dest) as f:
            self.assertEqual(f.read(), "new\n")

    def test_never_overwrites(self):
        dest = os.path.join(self.dir, "dest.csv")
        with open(dest, "w") as f:
            f.write("mine\n")
        self.assertFalse(setup_data.copy_if_missing(self.src, dest))
        with open(dest) as f:
            self.assertEqual(f.read(), "mine\n")


class DownloadIfMissingTest(unittest.TestCase):
    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.dest = os.path.join(self._dir.name, "table.csv")

    def tearDown(self):
        self._dir.cleanup()

    def _wget(self, content, status=0):
        def fake(cmd):
            if content is not None:
                with open(cmd[cmd.index("-O") + 1], "wb") as f:
                    f.write(content)
            return status

        return mock.patch("setup_data.subprocess.call", side_effect=fake)

    def test_existing_file_is_not_downloaded_or_overwritten(self):
        with open(self.dest, "w") as f:
            f.write("mine\n")
        with mock.patch("setup_data.subprocess.call") as call:
            self.assertFalse(setup_data.download_if_missing("http://x/y", self.dest))
        call.assert_not_called()
        with open(self.dest) as f:
            self.assertEqual(f.read(), "mine\n")

    def test_downloads_when_missing(self):
        with self._wget(b"a,b\n1,2\n"):
            self.assertTrue(setup_data.download_if_missing("http://x/y", self.dest))
        with open(self.dest, "rb") as f:
            self.assertEqual(f.read(), b"a,b\n1,2\n")

    def test_html_page_is_not_kept(self):
        with self._wget(b"<!DOCTYPE html>\n<html></html>"):
            self.assertFalse(setup_data.download_if_missing("http://x/y", self.dest))
        self.assertEqual(os.listdir(os.path.dirname(self.dest)), [])

    def test_empty_body_is_not_kept(self):
        for body in (b"", b"  \n"):
            with self._wget(body):
                self.assertFalse(setup_data.download_if_missing("http://x/y", self.dest))
            self.assertEqual(os.listdir(os.path.dirname(self.dest)), [])

    def test_failed_download_leaves_nothing(self):
        with self._wget(b"partial", status=8):
            self.assertFalse(setup_data.download_if_missing("http://x/y", self.dest))
        self.assertEqual(os.listdir(os.path.dirname(self.dest)), [])


class InstallDataFilesTest(unittest.TestCase):
    """The three csv files ship in the repository and are copied when missing, never downloaded."""

    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.dest = os.path.join(self._dir.name, "specmatchemp")
        os.mkdir(self.dest)

    def tearDown(self):
        self._dir.cleanup()

    def test_lists_the_three_files(self):
        self.assertEqual(
            sorted(setup_data.DATA_FILES),
            ["detrend.csv", "hires_telluric_mask.csv", "uncertainties.csv"],
        )

    def test_all_three_are_in_the_repository(self):
        for name in setup_data.DATA_FILES:
            self.assertTrue(os.path.isfile(os.path.join(REPO, name)), name)

    def test_all_three_are_in_the_source_distribution(self):
        with open(os.path.join(REPO, "MANIFEST.in")) as f:
            lines = [line.strip() for line in f]
        for name in setup_data.DATA_FILES:
            self.assertIn("include " + name, lines)

    def test_copies_all_three_when_missing(self):
        copied = setup_data.install_data_files(REPO, self.dest)
        self.assertEqual(sorted(copied), sorted(setup_data.DATA_FILES))
        for name in setup_data.DATA_FILES:
            with open(os.path.join(REPO, name), "rb") as a, open(os.path.join(self.dest, name), "rb") as b:
                self.assertEqual(a.read(), b.read())

    def test_makes_the_destination_directory(self):
        dest = os.path.join(self._dir.name, "new", "specmatchemp")
        setup_data.install_data_files(REPO, dest)
        self.assertEqual(sorted(os.listdir(dest)), sorted(setup_data.DATA_FILES))

    def test_existing_files_are_left_alone(self):
        for name in setup_data.DATA_FILES:
            with open(os.path.join(self.dest, name), "w") as f:
                f.write("mine " + name)
        self.assertEqual(setup_data.install_data_files(REPO, self.dest), [])
        for name in setup_data.DATA_FILES:
            with open(os.path.join(self.dest, name)) as f:
                self.assertEqual(f.read(), "mine " + name)

    def test_only_the_missing_file_is_copied(self):
        with open(os.path.join(self.dest, "detrend.csv"), "w") as f:
            f.write("mine")
        self.assertEqual(
            sorted(setup_data.install_data_files(REPO, self.dest)),
            ["hires_telluric_mask.csv", "uncertainties.csv"],
        )
        with open(os.path.join(self.dest, "detrend.csv")) as f:
            self.assertEqual(f.read(), "mine")

    def test_no_download_at_install(self):
        with mock.patch("setup_data.subprocess.call") as call:
            setup_data.install_data_files(REPO, self.dest)
        call.assert_not_called()


class ShippedFilesTest(unittest.TestCase):
    def _rows(self, name):
        with open(os.path.join(REPO, name), newline="") as f:
            return list(csv.reader(f))

    def test_detrend_is_exactly_the_three_lines(self):
        with open(os.path.join(REPO, "detrend.csv"), "rb") as f:
            data = f.read()
        self.assertEqual(
            data,
            b"# param, uncal_1, cal_1, uncal_2, cal_2\n"
            b"feh, -0.4540, -0.6, 0.4575, 0.6\n"
            b"radius, 1.184, 1.0, 1.748, 2.0",
        )

    def test_detrend_loads_and_maps_the_radius_edge(self):
        from specmatchemp.detrend import Detrend

        detrend = Detrend(os.path.join(REPO, "detrend.csv"))
        self.assertAlmostEqual(detrend.detrend(1.184, "radius"), 1.0, places=12)
        self.assertAlmostEqual(detrend.detrend(-0.4540, "feh"), -0.6, places=12)

    def test_uncertainties_parses(self):
        rows = self._rows("uncertainties.csv")[1:]
        self.assertTrue(rows)
        for row in rows:
            self.assertEqual(len(row), 4, row)
            [float(x) for x in row[1:]]

    def test_telluric_mask_is_a_plain_table(self):
        rows = self._rows("hires_telluric_mask.csv")
        self.assertEqual(rows[0], ["chip", "order", "minpix", "maxpix"])
        self.assertGreater(len(rows), 1)
        for row in rows[1:]:
            self.assertIn(row[0], ("rj", "ij"))
            self.assertEqual(len(row), 4, row)
            [int(x) for x in row[1:]]

    def test_telluric_mask_is_read_by_specmatch(self):
        import pandas as pd

        mask = pd.read_csv(os.path.join(REPO, "hires_telluric_mask.csv"))
        self.assertEqual(list(mask.columns), ["chip", "order", "minpix", "maxpix"])


if __name__ == "__main__":
    unittest.main()

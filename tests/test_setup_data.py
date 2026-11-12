"""Tests for setup_data, the install-time data file helpers.

Run with ``python -m unittest tests.test_setup_data`` from the repository root.
"""
import os
import tempfile
import unittest
from unittest import mock

import setup_data


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


if __name__ == "__main__":
    unittest.main()

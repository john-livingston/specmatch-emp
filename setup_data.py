"""Helpers for setup.py to put the data files in ~/.specmatchemp without overwriting existing ones."""
import os
import shutil
import subprocess


def copy_if_missing(src, dest):
    """Copy `src` to `dest` unless `dest` exists. Returns True when a copy was made."""
    if os.path.exists(dest):
        return False
    shutil.copyfile(src, dest)
    return True


def download_if_missing(url, dest):
    """Download `url` to `dest` unless `dest` exists. Returns True when the file was written.

    The download goes to a temporary name first and is kept only when wget succeeds
    and the file is not an HTML page, so a failed download never leaves a bad file at `dest`.
    """
    if os.path.exists(dest):
        return False
    part = dest + ".part"
    try:
        status = subprocess.call(["wget", "--no-check-certificate", url, "-O", part])
        if status != 0 or not os.path.exists(part):
            return False
        with open(part, "rb") as f:
            head = f.read(512).lstrip().lower()
        if head.startswith((b"<!doctype html", b"<html")):
            return False
        os.replace(part, dest)
        return True
    finally:
        if os.path.exists(part):
            os.remove(part)

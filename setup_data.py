"""Helpers for setup.py to put the data files in ~/.specmatchemp without overwriting existing ones.

The csv tables ship in the repository. download_if_missing is for the large library files."""
import os
import shutil
import subprocess

# The csv tables that ship in the repository (beside setup.py) and go to ~/.specmatchemp.
DATA_FILES = ("uncertainties.csv", "detrend.csv", "hires_telluric_mask.csv")


def copy_if_missing(src, dest):
    """Copy `src` to `dest` unless `dest` exists. Returns True when a copy was made."""
    if os.path.exists(dest):
        return False
    shutil.copyfile(src, dest)
    return True


def install_data_files(src_dir, dest_dir):
    """Copy each file of DATA_FILES from `src_dir` to `dest_dir` unless it is already there.

    Creates `dest_dir` when needed and never overwrites or downloads. Returns the names that were copied.
    """
    os.makedirs(dest_dir, exist_ok=True)
    return [
        name
        for name in DATA_FILES
        if copy_if_missing(os.path.join(src_dir, name), os.path.join(dest_dir, name))
    ]


def download_if_missing(url, dest):
    """Download `url` to `dest` unless `dest` exists. Returns True when the file was written.

    The download goes to a temporary name first and is kept only when wget succeeds
    and the file is not empty and not an HTML page, so a failed download never leaves a bad file at `dest`.
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
        if not head or head.startswith((b"<!doctype html", b"<html")):
            return False
        os.replace(part, dest)
        return True
    finally:
        if os.path.exists(part):
            os.remove(part)

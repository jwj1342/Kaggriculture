#!/usr/bin/env python
"""The two Kaggle CLI calls this repo makes over and over, in one place.

Both `ghost.py` and `topeps.py` pull episode dumps out of Kaggle's daily
datasets, and both had grown their own copy of the same two things: a paged
`datasets files` listing, and a `datasets download` that has to cope with some
CLI versions leaving a `.zip` behind instead of the file you asked for. The
listing was byte-identical in both, under two different names (`_listing` and
`_files`), so a fix to one would never have reached the other.

Deliberately thin. This is not a Kaggle client -- it shells out to the same CLI
a human would type, because that is the only interface with a stable contract
here, and because a failure then looks like a command you can paste and rerun.
"""

import os
import subprocess
import zipfile

LIST_TIMEOUT = 300
GET_TIMEOUT = 900


def dataset_files(slug, suffix=".json", page_size=200, timeout=LIST_TIMEOUT):
    """Every file in a dataset, following `Next Page Token` to the end.

    The daily episode dumps run to thousands of files, and the CLI pages at a
    few hundred, so a single call silently returns a prefix. That is the bug
    this function exists to not have.
    """
    out, token = [], None
    while True:
        cmd = ["kaggle", "datasets", "files", slug, "--page-size", str(page_size)]
        if token:
            cmd += ["--page-token", token]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout).stdout
        token = None
        for line in r.splitlines():
            if line.startswith("Next Page Token = "):
                token = line.split(" = ", 1)[1].strip()
                continue
            parts = line.split()
            if parts and parts[0].endswith(suffix):
                out.append(parts[0])
        if not token:
            return out


def dataset_file(slug, name, dest, timeout=GET_TIMEOUT):
    """Download one file into `dest`. Returns its path, or None if it did not arrive.

    Some CLI versions hand back `<name>.zip` rather than `<name>`; unpack and
    remove it so callers see one shape either way. Returns None instead of
    raising, because the callers are pulling hundreds of files in a loop and one
    missing episode is not a reason to lose the batch.
    """
    os.makedirs(dest, exist_ok=True)
    path = os.path.join(dest, name)
    subprocess.run(["kaggle", "datasets", "download", slug, "-f", name,
                    "-p", dest, "--force"],
                   capture_output=True, text=True, timeout=timeout)
    if not os.path.exists(path):
        zp = path + ".zip"
        if os.path.exists(zp):
            with zipfile.ZipFile(zp) as z:
                z.extractall(dest)
            os.remove(zp)
    return path if os.path.exists(path) else None

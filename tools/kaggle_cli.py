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
import sys
import time
import zipfile

LIST_TIMEOUT = 300
GET_TIMEOUT = 900

# Kaggle answers 429 above some request rate and the CLI still exits 0, so a
# caller that only checks for a file sees "no data" rather than "slow down".
# Pushing concurrency up to find the ceiling without this check got the whole
# account rate-limited for several minutes and returned nothing. Back off
# instead: the pull is incremental, so waiting costs only time.
# Measured the hard way: a burst at -j 64 left the account limited for
# well over three minutes, so the tail here is long on purpose. The
# callers are incremental, so a slow recovery costs time and nothing else.
RETRY_ON_429 = (20, 60, 180, 300, 600)


def _is_429(r):
    """Is this actually a rate-limit refusal?

    Not `"429" in output`: the daily dumps are named after episode ids, so a
    perfectly good listing containing `91804729.json` matches that and gets
    thrown away. Forty minutes of "backing off" here were a healthy 11 KB
    listing being discarded once every two minutes. Match the error line, and
    require that the command actually failed to produce anything.
    """
    blob = (r.stdout or "") + (r.stderr or "")
    hard = ("429 Client Error" in blob or "Too Many Requests" in blob
            or "TooManyRequests" in blob)
    return hard and not (r.stdout or "").strip().startswith(("name", "Next Page Token"))


def _run(cmd, timeout):
    """Run a Kaggle CLI command, backing off on 429 rather than failing quietly."""
    for pause in RETRY_ON_429 + (None,):
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if not _is_429(r):
            return r.stdout
        if pause is None:
            raise RuntimeError("Kaggle is rate-limiting and did not recover; "
                               "lower --jobs and try again in a few minutes")
        sys.stderr.write(f"  429 from Kaggle -- backing off {pause}s\n")
        time.sleep(pause)
    return ""


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
        r = _run(cmd, timeout)
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
    _run(["kaggle", "datasets", "download", slug, "-f", name,
          "-p", dest, "--force"], timeout)
    if not os.path.exists(path):
        zp = path + ".zip"
        if os.path.exists(zp):
            with zipfile.ZipFile(zp) as z:
                z.extractall(dest)
            os.remove(zp)
    return path if os.path.exists(path) else None

"""Remove what Seam A runs leave behind on a Docker host.

Everything the harness starts (containers, networks, volumes, the mutant images
it builds) carries the label `housemate.test=1`, plus `housemate.test.run=<id>`
and `housemate.test.started=<epoch seconds>` of the run that made it. This
module removes by those labels and nothing else, so containers that share the
host (other projects') are never touched.

    python3 tests/seam_a/cleanup.py                  # runs older than an hour
    python3 tests/seam_a/cleanup.py --older-than 0   # every labelled run, any age
    python3 tests/seam_a/cleanup.py --dry-run        # list, remove nothing

The harness calls `sweep()` when it starts (stale runs, an hour old) and when
it exits (its own run, whatever the outcome).
"""

import argparse
import glob
import os
import shutil
import subprocess
import sys
import tempfile
import time

LABEL = "housemate.test"
RUN_LABEL = "housemate.test.run"
STARTED_LABEL = "housemate.test.started"
TMP_PREFIX = "housemate-seam-a-"
MUTANT_REPO = "housemate-mutant-"
STALE_AFTER = 3600


def _docker(*args):
    r = subprocess.run(["docker", *args], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else ""


def _rows(*args):
    return [line.split("\t") for line in _docker(*args).splitlines() if line.strip()]


def _wanted(started, run, cutoff, only_run):
    if only_run is not None:
        return run == only_run
    try:
        return int(started) <= cutoff
    except ValueError:
        return True  # labelled by us but unreadable: treat as stale


def sweep(older_than=STALE_AFTER, run=None, dry_run=False, now=None):
    """Remove labelled leftovers; returns a list of what was (or would be) removed.

    `run` removes that run's things whatever their age; otherwise things from
    runs that started `older_than` seconds ago or more.
    """
    cutoff = (time.time() if now is None else now) - older_than
    flt = f"label={LABEL}=1"
    fmt = lambda kind: "{{." + kind + "}}\t{{.Label \"" + RUN_LABEL + "\"}}\t{{.Label \"" + STARTED_LABEL + "\"}}"
    removed = []

    def act(kind, ident, *cmd):
        removed.append(f"{kind} {ident}")
        if not dry_run:
            _docker(*cmd)

    for cid, rid, started in _rows("ps", "-a", "--filter", flt, "--format", fmt("ID")):
        if _wanted(started, rid, cutoff, run):
            act("container", cid, "rm", "-f", "-v", cid)
    for nid, rid, started in _rows("network", "ls", "--filter", flt, "--format", fmt("ID")):
        if _wanted(started, rid, cutoff, run):
            act("network", nid, "network", "rm", nid)
    for name, rid, started in _rows("volume", "ls", "--filter", flt, "--format", fmt("Name")):
        if _wanted(started, rid, cutoff, run):
            act("volume", name, "volume", "rm", "-f", name)
    # Images: only the mutants this harness built (the image under test is never ours to remove).
    for iid, repo, tag in _rows(
        "image", "ls", "--filter", flt, "--format", "{{.ID}}\t{{.Repository}}\t{{.Tag}}",
    ):
        labels = _docker("image", "inspect", "-f",
                         "{{index .Config.Labels \"" + RUN_LABEL + "\"}}\t{{index .Config.Labels \"" + STARTED_LABEL + "\"}}",
                         iid).strip().split("\t")
        if len(labels) != 2:
            continue
        if repo.startswith(MUTANT_REPO) or repo == "<none>":
            if _wanted(labels[1], labels[0], cutoff, run):
                act("image", f"{repo}:{tag}" if repo != "<none>" else iid, "rmi", "-f", iid)
    # Scratch directories: root-owned files inside, so remove from a container.
    for path in glob.glob(os.path.join(tempfile.gettempdir(), TMP_PREFIX + "*")):
        name = os.path.basename(path)
        rid = name[len(TMP_PREFIX):].split("-", 1)[0]
        try:
            mtime = os.path.getmtime(path)
        except OSError:
            continue
        if run is not None and rid != run:
            continue
        if run is None and mtime > cutoff:
            continue
        act("directory", path)
        if not dry_run:
            _docker("run", "--rm", "--label", f"{LABEL}=1", "-v", f"{path}:/x", "busybox:stable",
                    "sh", "-c", "rm -rf /x/* /x/.[!.]* 2>/dev/null; true")
            shutil.rmtree(path, ignore_errors=True)
    return removed


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--older-than", type=int, default=60, metavar="MINUTES",
                   help="only runs that started this many minutes ago or more (default 60; 0 = all)")
    p.add_argument("--run", help="only this run id")
    p.add_argument("--dry-run", action="store_true", help="list what would be removed")
    a = p.parse_args(argv)
    for line in sweep(older_than=a.older_than * 60, run=a.run, dry_run=a.dry_run):
        print(("would remove " if a.dry_run else "removed ") + line)
    return 0


if __name__ == "__main__":
    sys.exit(main())

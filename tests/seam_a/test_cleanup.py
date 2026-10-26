"""The sweep: it removes a stale run's leftovers and nothing else.

Stages, on the real Docker host, a run that started two hours ago (a container
with an anonymous volume, a network, a named volume), a run that started just
now, and an unlabelled container, then sweeps and looks at what is left.
"""

import subprocess
import time
import unittest
import uuid

import cleanup
from harness import RUN_ID, STUB_IMAGE, docker


def plain(*args):
    """Docker without the harness's labels: what some other project would run."""
    return subprocess.run(["docker", *args], capture_output=True, text=True)


def exists(kind, name):
    return plain(kind, "inspect", name).returncode == 0


class Sweep(unittest.TestCase):
    def stage(self, run, started):
        """One run's container (with an anonymous volume), network and named volume."""
        labels = ["--label", f"{cleanup.LABEL}=1", "--label", f"{cleanup.RUN_LABEL}={run}",
                  "--label", f"{cleanup.STARTED_LABEL}={started}"]
        names = {k: f"hm-sweep-test-{run}-{k}" for k in ("c", "n", "v")}
        self.addCleanup(plain, "network", "rm", names["n"])  # runs last, after the container
        self.addCleanup(plain, "volume", "rm", "-f", names["v"])
        self.addCleanup(plain, "rm", "-f", "-v", names["c"])
        plain("network", "create", *labels, names["n"])
        plain("volume", "create", *labels, names["v"])
        r = plain("run", "-d", *labels, "--name", names["c"], "--network", names["n"],
                  "-v", "/anonymous", STUB_IMAGE, "sleep", "300")
        self.assertEqual(r.returncode, 0, r.stderr)
        volume = plain("inspect", "-f", '{{range .Mounts}}{{.Name}}{{end}}', names["c"]).stdout.strip()
        self.addCleanup(plain, "volume", "rm", "-f", volume)
        self.assertTrue(volume)
        names["anon"] = volume
        return names

    def test_a_stale_run_goes_and_a_stranger_and_a_fresh_run_stay(self):
        stale = self.stage("stale" + uuid.uuid4().hex[:6], int(time.time()) - 7200)
        fresh = self.stage("fresh" + uuid.uuid4().hex[:6], int(time.time()))
        stranger = f"hm-sweep-test-stranger-{uuid.uuid4().hex[:6]}"
        self.addCleanup(plain, "rm", "-f", "-v", stranger)
        plain("run", "-d", "--name", stranger, STUB_IMAGE, "sleep", "300")

        removed = cleanup.sweep()

        self.assertFalse(exists("container", stale["c"]))
        self.assertFalse(exists("network", stale["n"]))
        self.assertFalse(exists("volume", stale["v"]))
        self.assertFalse(exists("volume", stale["anon"]), "the container's anonymous volume leaked")
        self.assertTrue(exists("container", stranger), "an unlabelled container was removed")
        self.assertTrue(exists("container", fresh["c"]), "a run under an hour old was removed")
        self.assertTrue(exists("network", fresh["n"]))
        self.assertTrue(exists("volume", fresh["anon"]))
        self.assertTrue(any(r.startswith("container ") for r in removed))

    def test_one_run_can_be_swept_whatever_its_age(self):
        run = "mine" + uuid.uuid4().hex[:6]
        mine = self.stage(run, int(time.time()))
        cleanup.sweep(run=run)
        self.assertFalse(exists("container", mine["c"]))
        self.assertFalse(exists("volume", mine["anon"]))

    def test_dry_run_removes_nothing(self):
        stale = self.stage("dry" + uuid.uuid4().hex[:6], int(time.time()) - 7200)
        self.assertTrue(cleanup.sweep(dry_run=True))
        self.assertTrue(exists("container", stale["c"]))


if __name__ == "__main__":
    unittest.main()

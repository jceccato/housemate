"""The Seam A tests must be able to fail.

Each case builds a deliberately broken variant of the image on top of the one
under test, and checks that the harness notices. A test suite that cannot be
made to fail is a green light with no wiring behind it.
"""

import os
import tempfile
import time
import unittest
from pathlib import Path

import harness
from harness import AddOn, docker, find_secret_everywhere

KEY = "hm-mutant-key-5d1c8b2e9a4f7063b8d2e1c4a7f90356"
RUN = "/etc/s6-overlay/s6-rc.d/code-server/run"
INIT = "/etc/s6-overlay/s6-rc.d/init-housemate/run"


def build_mutant(name, dockerfile_lines):
    with tempfile.TemporaryDirectory() as d:
        Path(d, "Dockerfile").write_text(f"FROM {harness.IMAGE}\n" + "\n".join(dockerfile_lines) + "\n")
        tag = f"housemate-mutant-{name}:{os.getpid()}"
        docker("build", "-q", "-t", tag, d)
    return tag


class Mutants(unittest.TestCase):
    def run_mutant(self, name, lines, wait=True):
        tag = build_mutant(name, lines)
        self.addCleanup(docker, "rmi", "-f", tag, check=False)
        saved = harness.IMAGE
        harness.IMAGE = tag
        self.addCleanup(setattr, harness, "IMAGE", saved)
        addon = AddOn({"provider": "go", "api_key": KEY})
        self.addCleanup(addon.stop)
        addon.start(wait=wait)
        return addon

    def leaks(self, name, lines):
        return find_secret_everywhere(self.run_mutant(name, lines), KEY)

    def test_the_image_under_test_is_clean(self):
        addon = AddOn({"provider": "go", "api_key": KEY})
        self.addCleanup(addon.stop)
        addon.start()
        self.assertEqual(find_secret_everywhere(addon, KEY), [])

    def test_a_key_in_the_logs_is_found(self):
        found = self.leaks("log", [
            f"RUN printf '%s\\n' 'bashio::log.info \"key=$(jq -r .api_key /data/options.json)\"' >> {INIT}",
        ])
        self.assertIn("the container logs", found)

    def test_a_key_in_the_workspace_is_found(self):
        found = self.leaks("workspace", [
            f"RUN printf '%s\\n' 'jq -r .api_key /data/options.json > /config/key.txt' >> {INIT}",
        ])
        self.assertIn("file /config/key.txt", found)

    def test_a_key_on_a_command_line_is_found(self):
        found = self.leaks("argv", [
            f"RUN sed -i 's|^exec code-server|bash -c \"sleep 600; true\" \"$(jq -r .api_key /data/options.json)\" \\&\\nexec code-server|' {RUN}",
        ])
        self.assertIn("a process command line or environment", found)

    def test_a_key_in_the_environment_is_found(self):
        found = self.leaks("env", [
            f"RUN sed -i 's|^exec code-server|export OPENCODE_KEY=\"$(jq -r .api_key /data/options.json)\"\\nexec code-server|' {RUN}",
        ])
        self.assertIn("a process command line or environment", found)

    def test_a_key_left_in_a_cache_file_is_found(self):
        found = self.leaks("cache", [
            f"RUN printf '%s\\n' 'jq -r .api_key /data/options.json > /tmp/leftover' >> {INIT}",
        ])
        self.assertIn("file /tmp/leftover", found)

    def test_a_dead_code_server_fails_the_start(self):
        with self.assertRaises(RuntimeError):
            self.run_mutant("dead", [f"RUN sed -i 's|^exec code-server.*|exec sleep 600|' {RUN}"])

    def test_an_open_front_door_is_noticed(self):
        addon = self.run_mutant("opennginx", [
            "RUN sed -i 's/^deny all;/allow all;/' /etc/s6-overlay/s6-rc.d/nginx/run",
        ])
        r = addon.other("wget", "-qO-", "-T", "5", f"http://{addon.ip}:1337/healthz")
        self.assertEqual(r.returncode, 0)  # what test_only_the_ingress_proxy_gets_in must catch

    def test_an_open_voice_endpoint_is_noticed(self):
        addon = self.run_mutant("openkickoff", [
            "RUN sed -i 's/if client_address\\[0\\] in ALLOWED:/if True:/' /usr/lib/housemate/kickoff.py",
        ])
        deadline = time.time() + 60
        while True:
            r = addon.other("wget", "-qO-", "-T", "3", f"http://{addon.ip}:8765/healthz")
            if r.returncode == 0 or time.time() > deadline:
                break
            time.sleep(1)
        self.assertEqual(r.returncode, 0)  # what test_core_reaches_the_endpoint_and_another_add_on_does_not must catch


if __name__ == "__main__":
    unittest.main()

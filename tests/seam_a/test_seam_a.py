"""Seam A: the Housemate (edge) container, driven from outside.

Run against a built image:

    HOUSEMATE_IMAGE=housemate-edge:dev python3 -m unittest discover -s tests/seam_a -v

See harness.py for how the container is started. Nothing here asserts how the
add-on does its work, only what a user or the Supervisor could see.
"""

import json
import re
import unittest

import yaml

from harness import ADDON_DIR, AddOn, docker, find_secret_everywhere

KEY = "hm-test-key-7f3a9c1e5b2d4086a1c3e5f70912b4d6"
CONFIG_FILES = {
    "configuration.yaml": "homeassistant:\n  name: Fixture\n",
    "secrets.yaml": "wifi_password: not-a-real-secret\n",
}


def pinned(arg):
    """The default of an ARG in the Dockerfile (the single source of a pin)."""
    text = (ADDON_DIR / "Dockerfile").read_text()
    return re.search(rf"^ARG {arg}=(\S+)", text, re.M).group(1)


class GoWithKey(unittest.TestCase):
    """The common case: OpenCode Go with a key."""

    @classmethod
    def setUpClass(cls):
        cls.addon = AddOn({"provider": "go", "api_key": KEY}, CONFIG_FILES)
        cls.addon.start()

    @classmethod
    def tearDownClass(cls):
        cls.addon.stop()

    def code_server_cmdline(self):
        return self.addon.exec(
            "for p in /proc/[0-9]*; do tr '\\0' ' ' < $p/cmdline | grep -e '[-]-bind-addr'; done; true"
        ).stdout

    # -- the panel ----------------------------------------------------------------

    def test_code_server_answers_on_the_ingress_port(self):
        status, _, body = self.addon.get("/healthz")
        self.assertEqual(status, 200)
        self.assertIn("lastHeartbeat", body)

    def test_the_workspace_is_config(self):
        status, headers, _ = self.addon.get("/")
        self.assertEqual(status, 302)
        # Relative, so that it works behind Ingress's path prefix.
        self.assertEqual(headers["Location"], "./?folder=/config")
        status, _, body = self.addon.get("/?folder=/config", follow=True)
        self.assertEqual(status, 200)

    def test_opencodes_extension_is_preinstalled(self):
        version = pinned("OPENCODE_EXTENSION_VERSION")
        r = self.addon.exec(
            f"cat /usr/local/lib/code-server/lib/vscode/extensions/sst-dev.opencode-{version}/package.json"
        )
        package = json.loads(r.stdout)
        self.assertEqual((package["publisher"], package["name"]), ("sst-dev", "opencode"))
        self.assertEqual(package["version"], version)

    def test_the_binaries_are_the_pinned_releases(self):
        self.assertEqual(self.addon.exec("opencode --version").stdout.strip(), pinned("OPENCODE_VERSION"))
        self.assertIn(f"{pinned('CODE_SERVER_VERSION')} ", self.addon.exec("code-server --version 2>/dev/null").stdout)

    def test_nothing_is_set_to_update_itself(self):
        env = self.addon.exec("opencode debug config").stdout
        self.assertFalse(json.loads(env)["autoupdate"])
        self.assertIn("--disable-update-check", self.code_server_cmdline())

    # -- OpenCode and the provider ----------------------------------------------

    def test_opencode_answers_and_sees_the_provider(self):
        config = json.loads(self.addon.exec("cd /config && opencode debug config").stdout)
        self.assertEqual(config["enabled_providers"], ["opencode-go"])
        self.assertIn("apiKey", config["provider"]["opencode-go"]["options"])
        models = self.addon.exec("opencode models opencode-go").stdout.split()
        self.assertTrue(models and all(m.startswith("opencode-go/") for m in models))

    def test_the_provider_config_carries_the_key_and_is_private(self):
        path = "/data/opencode/config/opencode/opencode.json"
        config = json.loads(self.addon.read_data("opencode/config/opencode/opencode.json"))
        self.assertEqual(config["provider"]["opencode-go"]["options"]["apiKey"], KEY)
        self.assertEqual(self.addon.exec(f"stat -c '%a %U' {path}").stdout.strip(), "600 root")

    def test_the_key_appears_nowhere_but_the_provider_config(self):
        self.assertEqual(find_secret_everywhere(self.addon, KEY), [])

    def test_the_built_in_rules_are_opencodes_global_agents_md(self):
        shipped = self.addon.exec("cat /usr/share/housemate/AGENTS.md").stdout
        self.assertIn("Housemate", shipped)
        self.assertEqual(self.addon.read_data("opencode/config/opencode/AGENTS.md"), shipped)

    # -- state under /data --------------------------------------------------------

    def test_state_lives_under_data(self):
        # OpenCode's database (sessions) and code-server's user data.
        self.assertTrue(self.addon.data_exists("code-server"))
        out = self.addon.exec("cd /config && opencode session list; ls /data/opencode/data/opencode").stdout
        self.assertIn("opencode.db", out)

    def test_the_workspace_is_read_write(self):
        self.addon.exec("echo created > /config/from-the-addon.txt")
        self.assertEqual((self.addon.config / "from-the-addon.txt").read_text().strip(), "created")

    def test_the_supervisor_token_reaches_a_terminal(self):
        # The agent's route to the Home Assistant API: present in a service's
        # environment (s6 keeps the base image's own copy in /run).
        env = self.addon.exec(
            "for p in /proc/[0-9]*; do "
            "if tr '\\0' ' ' < $p/cmdline | grep -q -e '[-]-bind-addr'; then tr '\\0' '\\n' < $p/environ; fi; done"
        ).stdout
        self.assertIn(f"SUPERVISOR_TOKEN={self.addon.supervisor_token}", env)


class RestartKeepsState(unittest.TestCase):
    """Restarts and option changes, the way the Supervisor does them."""

    OLD = "hm-old-key-0000aaaa1111bbbb2222cccc3333dddd"
    NEW = "hm-new-key-4444eeee5555ffff6666aaaa7777bbbb"

    @classmethod
    def setUpClass(cls):
        cls.addon = AddOn({"provider": "go", "api_key": cls.OLD}, CONFIG_FILES)
        cls.addon.start()

    @classmethod
    def tearDownClass(cls):
        cls.addon.stop()

    def test_state_survives_a_restart_and_the_options_are_reapplied(self):
        a = self.addon
        # Make state: a session in OpenCode's database, a user setting.
        a.exec(
            "cd /config && echo '{\"workbench.colorTheme\": \"Default Dark Modern\"}' "
            "> /data/code-server/User/settings.json"
        )
        # A real OpenCode session, made through the server API of the one the add-on runs.
        a.exec(
            "curl -sf -m 60 -X POST localhost:4096/session -H 'content-type: application/json' "
            "-d '{\"title\":\"survivor\"}'"
        )
        self.assertIn("survivor", a.exec("cd /config && opencode session list").stdout)
        shipped_rules = a.exec("cat /usr/share/housemate/AGENTS.md").stdout
        # The user tampers with the built-in rules: the next start restores them.
        a.exec("echo tampered > /data/opencode/config/opencode/AGENTS.md")
        a.exec("echo '# my notes' > /config/AGENTS.md")  # the user's own file

        a.set_options({"provider": "go", "api_key": self.NEW})
        a.restart()

        self.assertIn("Default Dark Modern", a.read_data("code-server/User/settings.json"))
        self.assertTrue(a.data_exists("opencode/data/opencode/opencode.db"))
        self.assertEqual((a.config / "AGENTS.md").read_text(), "# my notes\n")
        self.assertEqual(a.read_data("opencode/config/opencode/AGENTS.md"), shipped_rules)
        self.assertIn("survivor", a.exec("cd /config && opencode session list").stdout)
        config = json.loads(a.read_data("opencode/config/opencode/opencode.json"))
        self.assertEqual(config["provider"]["opencode-go"]["options"]["apiKey"], self.NEW)
        # The old key is gone from everywhere, and the new one is where it belongs.
        self.assertEqual(find_secret_everywhere(a, self.OLD), [])
        self.assertEqual(find_secret_everywhere(a, self.NEW), [])


class ZenWithoutKey(unittest.TestCase):
    """OpenCode Zen needs no key for its free models: the add-on still starts."""

    @classmethod
    def setUpClass(cls):
        cls.addon = AddOn({"provider": "zen", "api_key": ""}, CONFIG_FILES)
        cls.addon.start()

    @classmethod
    def tearDownClass(cls):
        cls.addon.stop()

    def test_provider_is_selected_without_a_key(self):
        config = json.loads(self.addon.read_data("opencode/config/opencode/opencode.json"))
        self.assertEqual(config["enabled_providers"], ["opencode"])
        self.assertNotIn("provider", config)
        self.assertIn("no key", self.addon.logs())


class UnknownProvider(unittest.TestCase):
    def test_an_unknown_provider_stops_the_add_on_with_a_reason(self):
        addon = AddOn({"provider": "nonsense", "api_key": ""}, CONFIG_FILES)
        try:
            addon.start(wait=False)
            import time
            for _ in range(60):
                if docker("inspect", "-f", "{{.State.Running}}", addon.name).stdout.strip() != "true":
                    break
                time.sleep(1)
            self.assertEqual(docker("inspect", "-f", "{{.State.Running}}", addon.name).stdout.strip(), "false")
            self.assertIn("Unknown provider", addon.logs())
        finally:
            addon.stop()


class Manifest(unittest.TestCase):
    """What the Supervisor reads before it runs anything."""

    @classmethod
    def setUpClass(cls):
        cls.config = yaml.safe_load((ADDON_DIR / "config.yaml").read_text())

    def test_identity(self):
        c = self.config
        self.assertEqual((c["slug"], c["name"]), ("housemate_edge", "Housemate (edge)"))
        self.assertEqual(c["image"], "ghcr.io/jceccato/{arch}-housemate-edge")
        self.assertEqual(sorted(c["arch"]), ["aarch64", "amd64"])

    def test_panel_is_admin_only_ingress_and_publishes_no_port(self):
        c = self.config
        self.assertTrue(c["ingress"])
        self.assertEqual(c["ingress_port"], 1337)
        self.assertIs(c["panel_admin"], True)
        self.assertNotIn("ports", c)
        self.assertNotIn("host_network", c)

    def test_access_is_declared(self):
        c = self.config
        self.assertTrue(c["homeassistant_api"])
        self.assertTrue(c["hassio_api"])
        self.assertEqual(c["hassio_role"], "manager")
        self.assertTrue(c["docker_api"])
        self.assertNotIn("full_access", c)
        self.assertNotIn("privileged", c)
        config_map = [m for m in c["map"] if m["type"] == "homeassistant_config"]
        self.assertEqual(config_map, [{"type": "homeassistant_config", "read_only": False, "path": "/config"}])

    def test_options_cover_the_provider_and_the_key(self):
        c = self.config
        self.assertEqual(c["schema"]["provider"], "list(go|zen)")
        self.assertEqual(c["schema"]["api_key"], "password?")

    def test_the_repository_lists_the_add_on(self):
        repo = yaml.safe_load((ADDON_DIR.parent / "repository.yaml").read_text())
        self.assertIn("name", repo)
        self.assertTrue((ADDON_DIR / "Dockerfile").exists())


if __name__ == "__main__":
    unittest.main()

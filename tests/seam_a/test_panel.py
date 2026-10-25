"""Seam A: the panel opens straight into OpenCode.

What a user would meet on opening the panel, checked from outside: the editor
settings the image owns, the launcher extension and the single OpenCode it
starts, OpenCode's resolved permission for Housemate's own files, the sidebar
switched on once, and the default model per provider. That the editor really
shows OpenCode in the editor area is looked at in a browser on the test VM.
"""

import json
import unittest

from harness import AddOn, docker
from test_mutants import INIT, build_mutant
import harness
from test_voice import VoiceAddOn

EXT = "/usr/local/lib/code-server/lib/vscode/extensions/housemate.launcher"
NODE = "/usr/local/lib/code-server/lib/node"
AGENT = "/usr/local/bin/housemate-agent"

# Run in the editor's own node with a stand-in for the editor's API: what does
# the launcher ask for when a window starts?
LAUNCH_SCRIPT = r"""
const Module = require('module');
const terminals = JSON.parse(process.argv[1]).map((name) => ({ name, show() { shown.push(name); } }));
const created = [], shown = [], commands = [];
const vscode = {
  window: {
    terminals,
    createTerminal(o) { created.push(o); return { name: o.name, show() {} }; },
    createStatusBarItem() { return { show() {} }; },
    showInformationMessage() {}, showQuickPick() {},
  },
  commands: { registerCommand(n) { commands.push(n); return {}; }, executeCommand(n) { commands.push('run:' + n); } },
  ViewColumn: { Active: -1 }, StatusBarAlignment: { Left: 1 },
};
const load = Module._load;
Module._load = (r, ...a) => (r === 'vscode' ? vscode : load(r, ...a));
const ext = require(process.argv[2]);
ext.activate({ subscriptions: [] });
setTimeout(() => { console.log(JSON.stringify({ created, shown, commands })); process.exit(0); }, 4000);
"""


def machine_settings_problems(addon):
    found = []
    machine = json.loads(addon.exec("cat /data/code-server/Machine/settings.json", check=False).stdout or "{}")
    if machine.get("chat.disableAIFeatures") is not True:
        found.append("VS Code's AI chat is not disabled")
    if machine.get("workbench.secondarySideBar.defaultVisibility") != "hidden":
        found.append("the secondary sidebar is not hidden")
    user = json.loads(addon.read_data("code-server/User/settings.json"))
    if user.get("workbench.colorTheme") != "Dark Modern":
        found.append("the default theme is not dark")
    return found


def launcher(addon, existing):
    r = docker("exec", "-i", addon.name, NODE, "-e", LAUNCH_SCRIPT, json.dumps(existing), f"{EXT}/extension.js", check=False)
    return json.loads(r.stdout)


def launcher_problems(addon):
    found = []
    manifest = json.loads(addon.exec(f"cat {EXT}/package.json").stdout)
    if "onStartupFinished" not in manifest["activationEvents"]:
        found.append("the launcher does not start with the window")
    fresh = launcher(addon, [])
    if len(fresh["created"]) != 1:
        found.append(f"a fresh window created {len(fresh['created'])} terminals")
    else:
        t = fresh["created"][0]
        if t.get("location") != {"viewColumn": -1}:
            found.append("the terminal is not in the editor area")
        if t.get("shellPath") != AGENT or t.get("shellArgs"):
            found.append("the terminal does not run housemate-agent for the newest chat")
    if "run:workbench.action.closePanel" not in fresh["commands"]:
        found.append("the bottom panel is not closed")
    again = launcher(addon, ["OpenCode"])
    if again["created"]:
        found.append("a window with OpenCode already open started a second")
    for c in ("housemate.openAgent", "housemate.newChat", "housemate.sessions"):
        if c not in fresh["commands"]:
            found.append(f"command {c} is missing")
    return found


def count_opencode(addon):
    r = addon.exec("for p in /proc/[0-9]*; do tr '\\0' ' ' < $p/cmdline 2>/dev/null; echo; done | grep -c '^opencode --continue '", check=False)
    return int(r.stdout.strip() or 0)


def open_panel(addon, *args):
    """What the editor's terminal does: housemate-agent on a terminal, attached for a moment."""
    docker("exec", "-t", addon.name, "timeout", "6", AGENT, *args, check=False)


def single_launcher_problems(addon):
    found = []
    open_panel(addon)
    open_panel(addon)
    open_panel(addon)
    if count_opencode(addon) != 1:
        found.append(f"{count_opencode(addon)} OpenCode processes after three opens")
    open_panel(addon, "--new")
    r = addon.exec("tmux -L housemate list-sessions | wc -l")
    if r.stdout.strip() != "2":
        found.append(f"a new chat did not get its own tab ({r.stdout.strip()} sessions)")
    return found


def permission_problems(addon):
    cfg = json.loads(addon.exec("cd /config && opencode debug config").stdout)
    perm = cfg.get("permission", {})
    found = []
    if perm.get("external_directory") != {"/usr/share/housemate/**": "allow"}:
        found.append(f"external_directory is {perm.get('external_directory')}")
    extra = set(perm) - {"external_directory"}
    if extra:
        found.append(f"other permissions were set: {sorted(extra)}")
    return found


class Panel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.addon = VoiceAddOn({"provider": "zen", "api_key": ""}, {"configuration.yaml": "homeassistant:\n"})
        cls.addon.start()

    @classmethod
    def tearDownClass(cls):
        cls.addon.stop()

    def sidebar_calls(self):
        out = docker("exec", self.addon.stub, "python3", "-c",
                     "import urllib.request;print(urllib.request.urlopen('http://127.0.0.1/_calls').read().decode())").stdout
        return [c for c in json.loads(out) if c["service"] == "addons/self/options" and "ingress_panel" in c["data"]]

    def test_editor_defaults_are_the_images_and_the_users_win(self):
        self.assertEqual(machine_settings_problems(self.addon), [])

    def test_the_launcher_opens_one_opencode_in_the_editor_area(self):
        self.assertEqual(launcher_problems(self.addon), [])

    def test_opening_the_panel_again_starts_no_second_opencode(self):
        self.assertEqual(single_launcher_problems(self.addon), [])

    def test_housemates_own_files_need_no_permission_and_nothing_else_is_widened(self):
        self.assertEqual(permission_problems(self.addon), [])

    def test_the_sidebar_is_switched_on_once_and_never_again(self):
        self.assertEqual([c["data"] for c in self.sidebar_calls()], [{"ingress_panel": True}])
        self.assertTrue(self.addon.data_exists(".housemate-sidebar-done"))
        self.addon.restart()
        self.addon.restart()
        self.assertEqual(len(self.sidebar_calls()), 1)

    def test_a_users_own_theme_survives_a_restart_and_an_old_file_gets_the_default_once(self):
        a = self.addon
        a.exec("echo '{\"workbench.colorTheme\": \"Default Light Modern\"}' > /data/code-server/User/settings.json")
        a.restart()
        self.assertEqual(json.loads(a.read_data("code-server/User/settings.json"))["workbench.colorTheme"], "Default Light Modern")
        a.exec("echo '{\"editor.fontSize\": 15}' > /data/code-server/User/settings.json")
        a.restart()
        got = json.loads(a.read_data("code-server/User/settings.json"))
        self.assertEqual(got, {"editor.fontSize": 15, "workbench.colorTheme": "Dark Modern"})


class Models(unittest.TestCase):
    def model(self, options):
        addon = AddOn(options)
        self.addCleanup(addon.stop)
        addon.start()
        return json.loads(addon.read_data("opencode/config/opencode/opencode.json"))["model"]

    def test_go_defaults_to_deepseek_flash(self):
        self.assertEqual(self.model({"provider": "go", "api_key": "k-go-0123456789"}), "opencode-go/deepseek-v4.1-flash")

    def test_zen_defaults_to_a_free_model(self):
        self.assertEqual(self.model({"provider": "zen", "api_key": ""}), "opencode/deepseek-v4.1-flash-free")

    def test_the_option_overrides_the_default(self):
        self.assertEqual(self.model({"provider": "go", "api_key": "k-go-0123456789", "model": "opencode-go/glm-5"}), "opencode-go/glm-5")

    def test_an_empty_option_means_the_default(self):
        self.assertEqual(self.model({"provider": "go", "api_key": "k-go-0123456789", "model": ""}), "opencode-go/deepseek-v4.1-flash")


class Mutants(unittest.TestCase):
    """Each check is able to fail."""

    def addon_with(self, name, lines):
        tag = build_mutant(name, lines)
        self.addCleanup(docker, "rmi", "-f", tag, check=False)
        saved = harness.IMAGE
        harness.IMAGE = tag
        self.addCleanup(setattr, harness, "IMAGE", saved)
        addon = VoiceAddOn({"provider": "zen", "api_key": ""}, {"configuration.yaml": "homeassistant:\n"})
        self.addCleanup(addon.stop)
        addon.start()
        return addon

    def test_chat_left_on_is_noticed(self):
        a = self.addon_with("chat", [f"RUN sed -i '/Machine\\/settings.json/d' {INIT}"])
        self.assertTrue(machine_settings_problems(a))

    def test_a_launcher_that_always_starts_a_second_opencode_is_noticed(self):
        a = self.addon_with("stack", ["RUN sed -i 's/-A -s \"${key}\"/-s \"${key}-$$\"/' " + AGENT])
        self.assertTrue(single_launcher_problems(a))

    def test_a_launcher_that_ignores_an_open_tab_is_noticed(self):
        a = self.addon_with("tab", [f"RUN sed -i 's/if (existing) {{ existing.show(); return; }}//' {EXT}/extension.js"])
        self.assertTrue(launcher_problems(a))

    def test_a_widened_permission_is_noticed(self):
        a = self.addon_with("perm", [f"RUN sed -i 's#\"/usr/share/housemate/\\*\\*\": \"allow\"#\"**\": \"allow\"#' {INIT}"])
        self.assertTrue(permission_problems(a))

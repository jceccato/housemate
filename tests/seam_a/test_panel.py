"""Seam A: the panel opens straight into OpenCode.

What a user would meet on opening the panel, checked from outside: the editor
settings the image owns, the launcher extension and the single OpenCode it
starts, OpenCode's resolved permission for Housemate's own files, the sidebar
switched on once, and the default model per provider. That the editor really
shows OpenCode in the editor area is looked at in a browser on the test VM.
"""

import json
import time
import unittest

from harness import AddOn, docker
from test_mutants import INIT, build_mutant
import harness
from test_voice import ADMIN, MEMBER, PORT, VoiceAddOn

EXT = "/usr/local/lib/code-server/lib/vscode/extensions/housemate.launcher"
NODE = "/usr/local/lib/code-server/lib/node"
AGENT = "/usr/local/bin/housemate-agent"

# Run in the editor's own node with a stand-in for the editor's API: what does
# the launcher ask for when a window starts?
LAUNCH_SCRIPT = r"""
const Module = require('module');
const terminals = JSON.parse(process.argv[1]).map((name) => ({ name: name.split('!')[0], exitStatus: name.includes('!') ? { code: 0 } : undefined, show() { shown.push(name); }, dispose() {} }));
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
setTimeout(() => { console.log(JSON.stringify({ created, shown, commands })); process.exit(0); }, 6500);
"""


def machine_settings_problems(addon):
    found = []
    machine = json.loads(addon.exec("cat /data/code-server/Machine/settings.json", check=False).stdout or "{}")
    if machine.get("chat.disableAIFeatures") is not True:
        found.append("VS Code's AI chat is not disabled")
    if machine.get("workbench.secondarySideBar.defaultVisibility") != "hidden":
        found.append("the secondary sidebar is not hidden")
    user = json.loads(addon.read_data("code-server/User/settings.json"))
    if user.get("workbench.colorTheme") != "Default Dark Modern":
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
        if t.get("shellPath") != AGENT or (t.get("shellArgs") and t["shellArgs"][0] != "--session"):
            found.append("the terminal does not run housemate-agent for the newest chat")
    if "run:workbench.action.closePanel" not in fresh["commands"]:
        found.append("the bottom panel is not closed")
    again = launcher(addon, ["OpenCode"])
    if again["created"]:
        found.append("a window with OpenCode already open started a second")
    if len(launcher(addon, ["OpenCode!ended"])["created"]) != 1:
        found.append("a tab left over from before an add-on restart kept the agent from reopening")
    for c in ("housemate.openAgent", "housemate.newChat", "housemate.sessions"):
        if c not in fresh["commands"]:
            found.append(f"command {c} is missing")
    return found


def count_opencode(addon):
    r = addon.exec("for p in /proc/[0-9]*; do tr '\\0' ' ' < $p/cmdline 2>/dev/null; echo; done | grep -c '^opencode attach http[^ ]* --session \\|^opencode attach http[^ ]* --continue\\|^opencode attach http[^ ]* $'", check=False)
    return int(r.stdout.strip() or 0)


def open_panel(addon, *args):
    """What the editor's terminal does: housemate-agent on a terminal, attached for a moment."""
    docker("exec", "-t", addon.name, "timeout", "6", AGENT, *args, check=False)


def sessions(addon):
    return addon.exec("tmux -L housemate list-sessions -F '#{session_name}' 2>/dev/null; true").stdout.split()


def single_launcher_problems(addon):
    found = []
    docker("exec", addon.name, "tmux", "-L", "housemate", "kill-server", check=False)
    for _ in range(3):
        open_panel(addon)
    # OpenCode starts a moment after its tmux session: let every start settle.
    time.sleep(8)
    chats = sessions(addon)
    if len(chats) != 1 or count_opencode(addon) != 1:
        found.append(f"three opens left {len(chats)} sessions and {count_opencode(addon)} OpenCode processes")
    open_panel(addon, "--new")
    if len(sessions(addon)) != 2:
        found.append(f"a new chat did not get its own tab ({sessions(addon)})")
    return found


def permission_problems(addon):
    cfg = json.loads(addon.exec("cd /config && opencode debug config").stdout)
    perm = cfg.get("permission", {})
    found = []
    if perm.get("external_directory") != {"/usr/share/housemate/**": "allow"}:
        found.append(f"external_directory is {perm.get('external_directory')}")
    extra = set(perm) - {"external_directory", "bash"}
    if extra:
        found.append(f"other permissions were set: {sorted(extra)}")
    if set(perm.get("bash", {}).values()) - {"deny"}:
        found.append(f"bash was widened: {perm.get('bash')}")
    return found


def run_bash(addon, command):
    """The command through OpenCode's own bash tool and the add-on's real permission rules (no model)."""
    params = json.dumps({"command": command, "description": "test"})
    r = addon.exec(f"cd /config && opencode debug agent build --tool bash --params '{params}' 2>&1", check=False)
    return r.stdout


POINTER = "/config/.housemate/current-session"


def new_session(addon, title):
    out = addon.exec(f"curl -s -XPOST localhost:4096/session -H 'content-type: application/json' -d '{{\"title\":\"{title}\"}}'").stdout
    return json.loads(out)["id"]


def the_chat_the_panel_opens(addon):
    """The OpenCode command line housemate-agent would run, as the id it names (None: the newest by default)."""
    docker("exec", addon.name, "tmux", "-L", "housemate", "kill-server", check=False)
    open_panel(addon)
    time.sleep(8)
    r = addon.exec("for p in /proc/[0-9]*; do tr '\\0' ' ' < $p/cmdline 2>/dev/null; echo; done | grep -a '^opencode attach http[^ ]* --session\\|^opencode attach http[^ ]* $'")
    return r.stdout.strip()


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

    def test_a_shell_command_that_names_the_add_ons_own_options_or_key_is_refused(self):
        a = self.addon
        a.exec("rm -f /tmp/ran")
        refused = [
            "curl -s -H \"Authorization: Bearer $SUPERVISOR_TOKEN\" http://supervisor/addons/self/info",
            "touch /tmp/ran; curl -s http://supervisor/addons/self/options/config | head -c 800",
            "touch /tmp/ran && cat /data/options.json",
            "echo a; jq . /data/options.json",
            "cat /data/opencode/config/opencode/opencode.json",
            "curl -s http://supervisor/addons/984d4583_housemate_edge/info",
        ]
        for command in refused:
            self.assertIn("rule which prevents", run_bash(a, command), command)
        self.assertEqual(a.exec("ls /tmp/ran", check=False).returncode, 2, "a refused command must not have run at all")

    def test_everything_else_in_the_shell_still_runs(self):
        a = self.addon
        for command in ("echo fine", "housemate-updates status", "curl -s http://supervisor/core/info -o /dev/null -w ok",
                        "ls /config"):
            out = run_bash(a, command)
            self.assertNotIn("rule which prevents", out, command)

    def test_the_sidebar_is_switched_on_once_and_never_again(self):
        self.assertEqual([c["data"] for c in self.sidebar_calls()], [{"ingress_panel": True}])
        self.assertTrue(self.addon.data_exists(".housemate-sidebar-done"))
        self.addon.restart()
        self.addon.restart()
        self.assertEqual(len(self.sidebar_calls()), 1)

    def kickoff(self, body):
        r = self.addon.as_core("curl", "-s", "-H", "Content-Type: application/json", "-d", json.dumps(body),
                               f"http://{self.addon.name}:{PORT}/kickoff")
        return json.loads(r.stdout)

    def wait_endpoint(self):
        for _ in range(60):
            if self.addon.as_core("curl", "-sf", f"http://{self.addon.name}:{PORT}/healthz").returncode == 0:
                return
            time.sleep(1)
        self.fail("the endpoint never answered")

    def test_the_panel_reopens_on_the_chat_a_job_marked_and_falls_back_to_the_newest(self):
        a = self.addon
        self.wait_endpoint()
        a.exec(f"rm -f {POINTER}")
        older = new_session(a, "older chat")
        time.sleep(1)
        newest = new_session(a, "newest chat")
        # No pointer: the newest chat.
        self.assertIn(newest, the_chat_the_panel_opens(a))
        # An admin's voice job marks its session; the panel opens into it, not the newest.
        job = self.kickoff({"text": "build me a night light", "user_id": ADMIN, "notify": "notify.mobile_app_test_phone"})["session_id"]
        self.assertEqual(a.exec(f"cat {POINTER}").stdout.strip(), job)
        new_session(a, "a chat made by hand afterwards")
        self.assertIn(job, the_chat_the_panel_opens(a))
        # Across an add-on restart (the tmux server is gone with the container): the same chat.
        a.restart()
        self.assertTrue(a.data_exists(".housemate-sidebar-done"))
        self.assertIn(job, the_chat_the_panel_opens(a))
        # A prepared review marks its session too; a non-admin's job does not take the panel over.
        review = self.kickoff({"text": "update review", "prepare": True})["session_id"]
        self.assertEqual(a.exec(f"cat {POINTER}").stdout.strip(), review)
        self.kickoff({"text": "turn everything off", "user_id": MEMBER})
        self.assertEqual(a.exec(f"cat {POINTER}").stdout.strip(), review)
        # A pointer to a chat that no longer exists: the newest.
        a.exec(f"echo ses_gone > {POINTER}")
        handmade = new_session(a, "the newest of all")
        opened = the_chat_the_panel_opens(a)
        self.assertNotIn("ses_gone", opened)
        self.assertIn(handmade, opened)

    def test_a_marked_chat_gets_a_tab_in_front_even_when_the_agent_is_already_open(self):
        a = self.addon
        self.wait_endpoint()
        a.exec("rm -f /config/.housemate/open-request")  # a link from another test is not this one's
        launcher(a, [])  # a first run: the welcome chat is made, and nothing else is pending
        job = self.kickoff({"text": "build me a night light", "user_id": ADMIN, "notify": "notify.mobile_app_test_phone"})["session_id"]
        made = launcher(a, ["OpenCode"])["created"]
        self.assertEqual([(t["shellPath"], t["shellArgs"]) for t in made], [(AGENT, ["--session", job])])
        # taken once: the next window start finds nothing new, and the open tab is enough
        self.assertEqual(launcher(a, ["OpenCode"])["created"], [])

    def test_a_first_run_opens_a_welcome_chat_that_has_been_asked_to_start_onboarding(self):
        a = self.addon
        a.exec("rm -f /config/.housemate/welcome-session /config/.housemate/onboarding.json /config/.housemate/open-request")
        made = launcher(a, [])["created"]
        self.assertEqual(len(made), 1)
        self.assertEqual(made[0]["shellArgs"][0], "--session")
        chats = json.loads(a.exec("curl -s localhost:4096/session").stdout)
        welcome = [c for c in chats if c["id"] == made[0]["shellArgs"][1]]
        self.assertEqual([c["title"] for c in welcome], ["Welcome to Housemate"])

    def ingress(self, *curl):
        return docker("exec", self.addon.ingress_client, "curl", "-s", "-w", "\n%{http_code}", *curl, check=False).stdout.rsplit("\n", 1)

    def test_a_link_naming_a_chat_reaches_the_editor_and_its_tab_comes_to_the_front(self):
        a = self.addon
        self.wait_endpoint()
        status, _, page = a.get("/?folder=/config")
        self.assertIn("_housemate/deeplink.js", page)
        script = a.get("/_housemate/deeplink.js")[2]
        self.assertIn("home-assistant/subscribe-properties", script)
        chat = new_session(a, "the chat a link names")
        url = f"http://{a.name}:1337/_housemate/open"
        a.exec("rm -f /config/.housemate/open-request")
        self.assertEqual(self.ingress("-X", "POST", f"{url}?session=ses_nothere")[1], "404")
        self.assertEqual(self.ingress("-X", "POST", f"{url}?session=../../etc")[1], "400")
        self.assertEqual(self.ingress(f"{url}?session={chat}")[1], "403", "only POST")
        self.assertEqual(a.exec("ls /config/.housemate/open-request", check=False).returncode, 2)
        self.assertEqual(self.ingress("-X", "POST", f"{url}?session={chat}")[1], "202")
        self.assertEqual(a.exec("cat /config/.housemate/open-request").stdout.strip(), chat)
        # The editor, with the agent already open, puts that chat's tab in front.
        made = launcher(a, ["OpenCode"])
        self.assertIn((AGENT, ["--session", chat]), [(t["shellPath"], t["shellArgs"]) for t in made["created"]])
        a.exec("rm -f /config/.housemate/open-request")

    def test_the_editor_page_carries_the_reconnect_helper(self):
        a = self.addon
        status, _, page = a.get("/?folder=/config")
        self.assertIn("_housemate/reconnect.js", page)
        status, headers, script = a.get("/_housemate/reconnect.js")
        self.assertEqual(status, 200)
        self.assertIn("location.reload()", script)
        # The boot id: stable while the container lives, new after a restart.
        _, _, first = a.get("/_housemate/boot")
        self.assertRegex(first.strip(), r"^[0-9a-f-]{36}$")
        self.assertEqual(a.get("/_housemate/boot")[2], first)
        a.restart()
        self.assertNotEqual(a.get("/_housemate/boot")[2], first)
        self.assertEqual(page.count("reconnect.js"), 1)
        # Behind Ingress the Supervisor names the panel's prefix, and the script is fetched from under it.
        r = docker("exec", a.ingress_client, "curl", "-s", "-H", "X-Ingress-Path: /api/hassio_ingress/abc",
                   f"http://{a.name}:1337/?folder=/config", check=False)
        self.assertIn('src="/api/hassio_ingress/abc/_housemate/reconnect.js"', r.stdout)

    def test_a_users_own_theme_survives_a_restart_and_an_old_file_gets_the_default_once(self):
        a = self.addon
        a.exec("echo '{\"workbench.colorTheme\": \"Default Light Modern\"}' > /data/code-server/User/settings.json")
        a.restart()
        self.assertEqual(json.loads(a.read_data("code-server/User/settings.json"))["workbench.colorTheme"], "Default Light Modern")
        a.exec("echo '{\"editor.fontSize\": 15}' > /data/code-server/User/settings.json")
        a.restart()
        got = json.loads(a.read_data("code-server/User/settings.json"))
        self.assertEqual(got, {"editor.fontSize": 15, "workbench.colorTheme": "Default Dark Modern"})


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
        a = self.addon_with("tab", [f"RUN sed -i 's/if (existing \\&\\& existing.exitStatus === undefined) {{ existing.show(); return; }}//' {EXT}/extension.js"])
        self.assertTrue(launcher_problems(a))

    def test_a_widened_permission_is_noticed(self):
        a = self.addon_with("perm", [f"RUN sed -i 's#\"/usr/share/housemate/\\*\\*\": \"allow\"#\"**\": \"allow\"#' {INIT}"])
        self.assertTrue(permission_problems(a))

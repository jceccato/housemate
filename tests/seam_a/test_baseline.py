"""Seam A: the baseline skills and commands, as OpenCode itself lists them.

OpenCode is asked from inside the container, in /config, what skills and
commands it found where the kit put them. The two lists are the whole contract:
a step only the user may start must be a command and must not be a skill,
because OpenCode ignores `disable-model-invocation` and offers every skill it
finds to the model.
"""

import json
import re
import unittest
from pathlib import Path

import harness
from harness import ADDON_DIR, AddOn
from test_mutants import build_mutant

ROOT = ADDON_DIR.parent
OPTIONS = {"provider": "zen", "api_key": ""}

# The model may load these on its own.
SKILLS = {
    "code-review", "writing-for-agents", "home-assistant",
    "tdd", "diagnosing-bugs", "codebase-design", "domain-modeling", "grilling", "orchestrator",
}
# Only the user may start these.
COMMANDS = {"grill", "to-spec", "to-tickets", "triage", "setup-matt-pocock-skills"}
# What those commands were called upstream, as skills: none may be offered to the model.
USER_ONLY_NAMES = COMMANDS | {"grill-with-docs"}


def listing(addon):
    """(skill names, command names) as OpenCode lists them from /config."""
    skills = json.loads(addon.exec("cd /config && opencode debug skill").stdout)
    config = json.loads(addon.exec("cd /config && opencode debug config").stdout)
    return [s["name"] for s in skills], sorted(config.get("command", {}))


def problems(skills, commands):
    found = []
    for name in sorted(SKILLS - set(skills)):
        found.append(f"skill {name} not found")
    for name in sorted(COMMANDS - set(commands)):
        found.append(f"command {name} not found")
    for name in sorted(USER_ONLY_NAMES & set(skills)):
        found.append(f"{name} is offered to the model as a skill")
    return found


class Baseline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.addon = AddOn(OPTIONS)
        cls.addon.start()
        cls.skills, cls.commands = listing(cls.addon)

    @classmethod
    def tearDownClass(cls):
        cls.addon.stop()

    def test_every_baseline_skill_and_command_is_found_by_opencode(self):
        self.assertEqual(problems(self.skills, self.commands), [])

    def test_user_only_steps_are_commands_and_never_skills(self):
        self.assertTrue(COMMANDS <= set(self.commands))
        self.assertEqual(USER_ONLY_NAMES & set(self.skills), set())

    def test_every_command_carries_a_prompt_and_no_dead_flag(self):
        config = json.loads(self.addon.exec("cd /config && opencode debug config").stdout)["command"]
        for name in COMMANDS:
            self.assertTrue(config[name]["template"].strip(), name)
            self.assertTrue(config[name]["description"].strip(), name)
        files = self.addon.exec("grep -rl '^disable-model-invocation' /config/.opencode || true").stdout.split()
        self.assertEqual(files, [])

    def test_a_commands_extra_files_are_not_commands(self):
        extra = [c for c in self.commands if c in {"AGENT-BRIEF", "OUT-OF-SCOPE", "triage-labels", "domain"}]
        self.assertEqual(extra, [])
        self.assertEqual(self.addon.exec("ls /config/.opencode/commands | wc -l").stdout.strip(), str(len(COMMANDS)))

    def test_the_tracker_is_preconfigured_for_local_markdown(self):
        for rel in ("docs/agents/issue-tracker.md", "docs/agents/triage-labels.md", "docs/agents/domain.md"):
            self.assertEqual(self.addon.exec(f"test -s /config/{rel}", check=False).returncode, 0, rel)
        text = self.addon.exec("cat /config/docs/agents/issue-tracker.md").stdout
        self.assertIn("tracker/", text)
        self.assertNotIn(".scratch", text)
        for name in COMMANDS:
            body = self.addon.exec(f"cat /config/.opencode/commands/{name}.md").stdout
            self.assertNotIn(".scratch/", body, name)

    def test_the_skills_are_seeded_into_the_manifest_so_incoming_covers_them(self):
        manifest = json.loads(self.addon.exec("cat /config/.housemate/kit-manifest.json").stdout)["files"]
        for rel in (".opencode/skills/tdd/SKILL.md", ".opencode/commands/grill.md",
                    ".opencode/skills/home-assistant/ha_ws.py", ".opencode/support/mattpocock-skills/LICENSE"):
            self.assertIn(rel, manifest)

    def test_the_licence_notice_travels_with_the_vendored_skills(self):
        licence = self.addon.exec("cat /config/.opencode/support/mattpocock-skills/LICENSE").stdout
        self.assertIn("Matt Pocock", licence)
        self.assertIn("Permission is hereby granted", licence)
        revision = re.search(r"^ARG MATT_SKILLS_REVISION=([0-9a-f]{40})$", dockerfile(), re.M).group(1)
        readme = self.addon.exec("cat /config/.opencode/support/mattpocock-skills/README.md").stdout
        self.assertIn(revision, readme)

    def test_the_ha_websocket_helper_runs(self):
        r = self.addon.exec("python3 -I /config/.opencode/skills/home-assistant/ha_ws.py --help")
        self.assertIn("websocket", r.stdout.lower())
        r = self.addon.exec("env -u SUPERVISOR_TOKEN -u HA_TOKEN python3 -I "
                            "/config/.opencode/skills/home-assistant/ha_ws.py '{\"type\":\"get_config\"}'", check=False)
        self.assertEqual(r.returncode, 1)
        self.assertIn("no token", r.stderr)


def dockerfile():
    return (ADDON_DIR / "Dockerfile").read_text()


class Repository(unittest.TestCase):
    """What the repository must say about the vendored revision (no container needed)."""

    def test_the_revision_is_pinned_and_renovate_is_told_where_to_look(self):
        m = re.search(r"^# renovate: git-refs (\S+) (\S+)\nARG MATT_SKILLS_REVISION=([0-9a-f]{40})$", dockerfile(), re.M)
        self.assertIsNotNone(m, "Dockerfile: '# renovate: git-refs <url> <branch>' above 'ARG MATT_SKILLS_REVISION=<40 hex>'")
        self.assertEqual(m.group(1), "https://github.com/mattpocock/skills")

    def test_the_notice_names_the_source_the_licence_and_the_revision(self):
        notices = (ROOT / "THIRD_PARTY_NOTICES.md").read_text()
        self.assertIn("github.com/mattpocock/skills", notices)
        self.assertIn("Copyright (c) 2026 Matt Pocock", notices)
        self.assertIn("MATT_SKILLS_REVISION", notices)

    def test_the_orchestrator_skill_keeps_the_flow_and_carries_nothing_of_a_lab(self):
        text = (ADDON_DIR / "rootfs/usr/share/housemate/kit/.opencode/skills/orchestrator/SKILL.md").read_text()
        for needed in ("grill it, or yolo", "/grill", "task", "gate", "code-review", "tracker/", "Status:"):
            self.assertIn(needed, text, needed)
        lab = ("sidebar", "session card", "powershell", ".ps1", "scratch/", "obsidian",
               "azure", "wayfinder")
        self.assertEqual([w for w in lab if w in text.lower()], [])


class AsksThroughTheQuestionTool(unittest.TestCase):
    """Setup and decision questions go through OpenCode's `question` tool, so it must be on."""

    @classmethod
    def setUpClass(cls):
        cls.addon = AddOn(OPTIONS)
        cls.addon.start()

    @classmethod
    def tearDownClass(cls):
        cls.addon.stop()

    def test_the_tool_is_enabled_in_a_shell_and_in_the_running_server(self):
        self.assertEqual(self.addon.exec("printenv OPENCODE_ENABLE_QUESTION_TOOL").stdout.strip(), "true")
        server = self.addon.exec("tr '\\0' '\\n' < /proc/$(pgrep -f 'opencode serve' | head -1)/environ").stdout
        self.assertIn("OPENCODE_ENABLE_QUESTION_TOOL=true", server)

    def test_the_skills_say_to_use_it(self):
        base = ADDON_DIR / "rootfs/usr/share/housemate"
        onboarding = (base / "skills/onboarding/SKILL.md").read_text()
        self.assertIn("Every question goes through the `question` tool", onboarding)
        self.assertIn("restart now\n(**recommended**", onboarding)
        self.assertIn("recommends \"later\"", onboarding)
        self.assertIn("`question` tool", (base / "AGENTS.md").read_text())
        self.assertIn("`question` tool", (base / "kit/.opencode/skills/orchestrator/SKILL.md").read_text())
        self.assertIn("`question` tool", (base / "skills/update-review/SKILL.md").read_text())


class BaselineMutants(unittest.TestCase):
    """The listing check must be able to fail."""

    def listing_of(self, name, lines):
        tag = build_mutant(name, lines)
        self.addCleanup(harness.docker, "rmi", "-f", tag, check=False)
        saved = harness.IMAGE
        harness.IMAGE = tag
        self.addCleanup(setattr, harness, "IMAGE", saved)
        addon = AddOn(OPTIONS)
        self.addCleanup(addon.stop)
        addon.start()
        return listing(addon)

    def test_a_user_only_step_shipped_as_a_skill_is_caught(self):
        skills, commands = self.listing_of("grill-as-skill", [
            "RUN mkdir -p /usr/share/housemate/kit/.opencode/skills/to-spec "
            "&& printf '%s\\n' '---' 'name: to-spec' 'description: x' '---' x "
            "> /usr/share/housemate/kit/.opencode/skills/to-spec/SKILL.md",
        ])
        self.assertIn("to-spec is offered to the model as a skill", problems(skills, commands))

    def test_a_missing_skill_is_caught(self):
        skills, commands = self.listing_of("no-tdd", ["RUN rm -r /usr/share/housemate/kit/.opencode/skills/tdd"])
        self.assertIn("skill tdd not found", problems(skills, commands))

    def test_a_missing_command_is_caught(self):
        skills, commands = self.listing_of("no-grill", ["RUN rm /usr/share/housemate/kit/.opencode/commands/grill.md"])
        self.assertIn("command grill not found", problems(skills, commands))


if __name__ == "__main__":
    unittest.main()

"""vendor_skills.py turns a checkout of Matt Pocock's skills into OpenCode skills and commands.

The seam is the script's command line: an upstream tree in, a kit tree out.
These tests use a small fake upstream; the real one is exercised when the image
builds (Seam A, tests/seam_a/test_baseline.py).
"""

import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "housemate_edge" / "build" / "vendor_skills.py"

REV = "5beb35b040e3de97e54fa9e386d7e42d15c295c2"


def write(base, rel, text):
    path = pathlib.Path(base) / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def fake_upstream(base, *, flag_drift=False):
    write(base, "LICENSE", "MIT License\n\nCopyright (c) 2026 Matt Pocock\n")
    eng = "skills/engineering/"
    write(base, eng + "grill-with-docs/SKILL.md",
          '---\nname: grill-with-docs\ndescription: Grill me.\ndisable-model-invocation: true\n---\n'
          'Call the Skill tool twice, for "grilling" and "domain-modeling". Then run /grill-with-docs again.\n')
    write(base, eng + "grill-with-docs/agents/openai.yaml", "interface: {}\n")
    write(base, eng + "to-spec/SKILL.md",
          '---\nname: to-spec\ndescription: Make a spec.\ndisable-model-invocation: true\n---\n'
          'Write it under `.scratch/<feature-slug>/spec.md`.\n')
    write(base, eng + "to-tickets/SKILL.md",
          '---\nname: to-tickets\ndescription: Make tickets.\ndisable-model-invocation: true\n---\nTickets.\n')
    write(base, eng + "triage/SKILL.md",
          '---\nname: triage\ndescription: Triage.\ndisable-model-invocation: true\n---\n'
          'See [AGENT-BRIEF.md](AGENT-BRIEF.md) and [the other](./OTHER.md).\n')
    write(base, eng + "triage/AGENT-BRIEF.md", "brief\n")
    write(base, eng + "triage/OTHER.md", "other\n")
    write(base, eng + "setup-matt-pocock-skills/SKILL.md",
          '---\nname: setup-matt-pocock-skills\ndescription: Set up.\ndisable-model-invocation: true\n---\nSetup.\n')
    write(base, eng + "setup-matt-pocock-skills/issue-tracker-local.md", "Issues live in `.scratch/`.\n")
    write(base, eng + "setup-matt-pocock-skills/issue-tracker-github.md", "GitHub tracker\n")
    write(base, eng + "setup-matt-pocock-skills/triage-labels.md", "# Triage Labels\n")
    write(base, eng + "setup-matt-pocock-skills/domain.md", "# Domain Docs\n")
    write(base, eng + "tdd/SKILL.md", "---\nname: tdd\ndescription: TDD.\n---\nRed, green. See [tests.md](tests.md).\n")
    write(base, eng + "tdd/tests.md", "tests\n")
    write(base, eng + "diagnosing-bugs/SKILL.md", "---\nname: diagnosing-bugs\ndescription: Diagnose.\n---\nLoop.\n")
    write(base, eng + "diagnosing-bugs/scripts/hitl-loop.template.sh", "#!/bin/sh\n")
    write(base, eng + "domain-modeling/SKILL.md", "---\nname: domain-modeling\ndescription: Model.\n---\nModel.\n")
    write(base, eng + "codebase-design/SKILL.md", "---\nname: codebase-design\ndescription: Design.\n---\nDesign.\n")
    grilling = "---\nname: grilling\ndescription: Grill.\n"
    if flag_drift:
        grilling += "disable-model-invocation: true\n"
    write(base, "skills/productivity/grilling/SKILL.md", grilling + "---\nAsk questions.\n")


def run(upstream, out, check=True):
    return subprocess.run(
        [sys.executable, "-I", str(SCRIPT), str(upstream), str(out), "--revision", REV],
        capture_output=True, text=True, check=check,
    )


class VendorSkills(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.up = pathlib.Path(self.tmp.name) / "up"
        self.out = pathlib.Path(self.tmp.name) / "kit"
        fake_upstream(self.up)

    def read(self, rel):
        return (self.out / rel).read_text()

    def test_model_invocable_skills_stay_skills_with_their_files(self):
        run(self.up, self.out)
        for name in ("tdd", "diagnosing-bugs", "grilling", "domain-modeling", "codebase-design"):
            self.assertTrue((self.out / ".opencode/skills" / name / "SKILL.md").is_file(), name)
        self.assertTrue((self.out / ".opencode/skills/tdd/tests.md").is_file())
        self.assertTrue((self.out / ".opencode/skills/diagnosing-bugs/scripts/hitl-loop.template.sh").is_file())
        self.assertFalse((self.out / ".opencode/skills/tdd/agents").exists())

    def test_user_invoked_steps_become_commands_not_skills(self):
        run(self.up, self.out)
        for command in ("grill", "to-spec", "to-tickets", "triage", "setup-matt-pocock-skills"):
            self.assertTrue((self.out / ".opencode/commands" / f"{command}.md").is_file(), command)
        for name in ("grill-with-docs", "grill", "to-spec", "to-tickets", "triage", "setup-matt-pocock-skills"):
            self.assertFalse((self.out / ".opencode/skills" / name).exists(), name)
        text = self.read(".opencode/commands/grill.md")
        self.assertTrue(text.startswith("---\ndescription: Grill me.\n---\n"))
        self.assertNotIn("disable-model-invocation", text)
        self.assertIn("$ARGUMENTS", text)

    def test_commands_dir_holds_only_commands(self):
        run(self.up, self.out)
        found = sorted(p.name for p in (self.out / ".opencode/commands").rglob("*") if p.is_file())
        self.assertEqual(found, ["grill.md", "setup-matt-pocock-skills.md", "to-spec.md", "to-tickets.md", "triage.md"])

    def test_a_commands_companion_files_sit_outside_the_commands_dir_and_links_follow(self):
        run(self.up, self.out)
        self.assertEqual(self.read(".opencode/support/triage/AGENT-BRIEF.md"), "brief\n")
        text = self.read(".opencode/commands/triage.md")
        self.assertIn("(.opencode/support/triage/AGENT-BRIEF.md)", text)
        self.assertIn("(.opencode/support/triage/OTHER.md)", text)

    def test_text_is_made_to_fit_this_tracker_and_this_agent(self):
        run(self.up, self.out)
        self.assertIn("`tracker/<feature-slug>/spec.md`", self.read(".opencode/commands/to-spec.md"))
        grill = self.read(".opencode/commands/grill.md")
        self.assertIn("the `skill` tool", grill)
        self.assertIn("/grill again", grill)
        self.assertNotIn(".scratch", self.read("docs/agents/issue-tracker.md"))

    def test_docs_agents_are_preconfigured_for_the_local_tracker(self):
        run(self.up, self.out)
        self.assertIn("tracker/", self.read("docs/agents/issue-tracker.md"))
        self.assertEqual(self.read("docs/agents/triage-labels.md"), "# Triage Labels\n")
        self.assertEqual(self.read("docs/agents/domain.md"), "# Domain Docs\n")
        self.assertEqual(self.read(".opencode/support/setup-matt-pocock-skills/issue-tracker-github.md"), "GitHub tracker\n")

    def test_licence_and_revision_travel_with_the_skills(self):
        run(self.up, self.out)
        self.assertIn("Copyright (c) 2026 Matt Pocock", self.read(".opencode/support/mattpocock-skills/LICENSE"))
        self.assertIn(REV, self.read(".opencode/support/mattpocock-skills/README.md"))

    def test_an_upstream_skill_that_changes_invocation_stops_the_build(self):
        fake_upstream(self.up, flag_drift=True)
        r = run(self.up, self.out, check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("grilling", r.stderr)

    def test_a_missing_upstream_skill_stops_the_build(self):
        shutil.rmtree(self.up / "skills/engineering/tdd")
        r = run(self.up, self.out, check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("tdd", r.stderr)


if __name__ == "__main__":
    unittest.main()

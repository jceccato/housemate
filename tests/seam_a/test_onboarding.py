"""Seam A: onboarding, as a fresh install meets it.

What is asserted is what OpenCode and the user could see from outside: the
skill OpenCode lists, the rule that starts it on a first open, the progress
tool's answer on a fresh install, and the scan's effect on the cheat sheet
against a stand-in Home Assistant. That a real model follows the skill is
proved on the test VM, not here.
"""

import json
import unittest

from harness import docker
from test_voice import VoiceAddOn

ENTITIES = [{"entity_id": "light.lounge_lamp", "area_id": "lounge", "aliases": ["the lamp"]}]
HOUSE = {
    "states": [
        {"entity_id": "light.lounge_lamp", "state": "off", "attributes": {"friendly_name": "Lounge lamp"}},
        {"entity_id": "climate.study", "state": "off", "attributes": {"friendly_name": "Study aircon"}},
        {"entity_id": "update.core", "state": "off", "attributes": {"friendly_name": "Core"}},
    ],
    "devices": [],
    "areas": [{"area_id": "lounge", "name": "Lounge"}],
    "services": {"notify": {"mobile_app_test_phone": {}, "notify": {}, "persistent_notification": {}}},
}


class OnboardingAddOn(VoiceAddOn):
    def _write_options(self):
        super()._write_options()
        # The stand-in serves the entity registry from registry.json (a list) and the rest from house.json.
        (self.tmp / "fake" / "registry.json").write_text(json.dumps(ENTITIES))
        (self.tmp / "fake" / "house.json").write_text(json.dumps(HOUSE))


class Onboarding(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.addon = OnboardingAddOn({"provider": "zen", "api_key": ""}, {"configuration.yaml": "homeassistant:\n"})
        cls.addon.start()

    @classmethod
    def tearDownClass(cls):
        cls.addon.stop()

    def sh(self, script, **kw):
        return self.addon.exec(script, **kw)

    def test_a_fresh_install_reports_new_so_the_first_open_starts_onboarding(self):
        self.assertIn("onboarding: new", self.sh("housemate-onboarding status").stdout)

    def test_the_built_in_rules_start_it_on_new_and_name_the_skill(self):
        rules = self.sh("cat /data/opencode/config/opencode/AGENTS.md").stdout
        self.assertIn("housemate-onboarding status", rules)
        self.assertIn("`new`", rules)
        self.assertIn("`onboarding` skill", rules)

    def test_opencode_lists_the_onboarding_skill_with_its_steps(self):
        skills = json.loads(self.sh("cd /config && opencode debug skill").stdout)
        skill = next(s for s in skills if s["name"] == "onboarding")
        for needle in ("/config/scripts/git-init.sh", "housemate-voice-install", "housemate-onboarding scan",
                       "housemate-onboarding phones", "orchestrator"):
            self.assertIn(needle, skill["content"])

    def test_the_skill_is_the_add_ons_not_the_kits_and_a_start_restores_it(self):
        manifest = json.loads(self.sh("cat /config/.housemate/kit-manifest.json").stdout)
        self.assertFalse([f for f in manifest["files"] if "onboarding" in f])
        self.sh("echo vandalised > /data/opencode/config/opencode/skills/onboarding/SKILL.md")
        self.addon.restart()
        self.assertIn("name: onboarding", self.sh("cat /data/opencode/config/opencode/skills/onboarding/SKILL.md").stdout)

    def test_the_scan_seeds_the_cheat_sheet_and_a_second_scan_changes_nothing(self):
        out = self.sh("housemate-onboarding scan").stdout
        self.assertIn("Wrote 2 entities", out)
        sheet = self.sh("cat /config/docs/cheat-sheet.md").stdout
        self.assertIn("| Lounge lamp | `light.lounge_lamp` | Lounge |", sheet)
        self.assertIn('also called "the lamp"', sheet)
        self.assertIn("| Study aircon | `climate.study` |", sheet)
        self.assertNotIn("update.core", sheet)
        self.assertLess(sheet.index("housemate-scan:start"), sheet.index("## Quirks"))
        self.sh("echo '- Mine.' >> /config/docs/cheat-sheet.md")
        before = self.sh("sed 's/Written by.*//' /config/docs/cheat-sheet.md").stdout
        self.sh("housemate-onboarding scan")
        after = self.sh("sed 's/Written by.*//' /config/docs/cheat-sheet.md").stdout
        self.assertEqual(before, after)
        self.assertIn("- Mine.", after)

    def test_the_phones_are_the_companion_apps_only(self):
        self.assertEqual(self.sh("housemate-onboarding phones").stdout.split(), ["notify.mobile_app_test_phone"])

    def test_the_review_phone_is_set_through_the_options_api_with_the_rest_kept(self):
        self.sh("housemate-onboarding review-notify notify.mobile_app_test_phone")
        calls = json.loads(self.sh("curl -s http://supervisor/_calls").stdout)
        sent = [c for c in calls if c["service"] == "addons/self/options"][-1]["data"]["options"]
        self.assertEqual(sent["review_notify"], "notify.mobile_app_test_phone")
        self.assertEqual(sent["provider"], "zen")
        live = json.loads(self.sh("cat /data/options.json").stdout)
        self.assertEqual(live["review_notify"], "notify.mobile_app_test_phone")  # the review reads this file
        self.assertIn("phone: done - notify.mobile_app_test_phone", self.sh("housemate-onboarding status").stdout)

    def restarts(self):
        calls = json.loads(self.sh("curl -s http://supervisor/_calls").stdout)
        return [c for c in calls if c["service"] == "core/restart"]

    def test_core_is_never_restarted_without_the_users_yes(self):
        out = self.sh("housemate-onboarding restart-core").stdout
        self.assertIn("Configuration check: valid", out)
        self.assertIn("Not restarting", out)
        self.assertEqual(self.restarts(), [])
        self.assertIn("restart is pending", self.sh("housemate-onboarding status").stdout)

    def test_core_restarts_once_when_told_yes_and_the_pending_note_clears(self):
        self.sh("housemate-onboarding restart-core")
        self.assertEqual(self.restarts(), [])
        out = self.sh("HOUSEMATE_RESTART_WAIT=1 housemate-onboarding restart-core --yes").stdout
        self.assertIn("restarted", out)
        self.assertEqual(len(self.restarts()), 1)
        self.assertNotIn("restart is pending", self.sh("housemate-onboarding status").stdout)

    def test_the_skill_asks_install_and_restart_as_two_questions(self):
        skill = self.sh("cat /data/opencode/config/opencode/skills/onboarding/SKILL.md").stdout
        self.assertIn("Question A", skill)
        self.assertIn("Question B", skill)
        self.assertIn("restart-core --yes", skill)
        self.assertNotIn("curl -fsS -X POST -H \"$auth\" http://supervisor/core/restart", skill)

    def test_a_step_answers_with_itself_and_status_with_the_list_once(self):
        out = self.sh("housemate-onboarding step remote skipped 'not now'").stdout
        self.assertEqual(out.strip(), "remote: skipped")
        self.assertEqual(self.sh("housemate-onboarding status").stdout.count("onboarding:"), 1)

    def test_the_skill_ends_voice_with_a_real_trial_and_where_to_find_the_chat(self):
        skill = self.sh("cat /data/opencode/config/opencode/skills/onboarding/SKILL.md").stdout
        self.assertNotIn("Housemate say hello", skill)
        self.assertIn("keep the best idea for step 7", " ".join(skill.split()))
        self.assertIn("/sessions", skill)
        self.assertIn("Chats", skill)

    def test_progress_is_kept_out_of_git(self):
        self.sh("housemate-onboarding step git done 'tracked'")
        self.sh("chown -R root:root /config")  # as in the real add-on
        self.sh("/config/scripts/git-init.sh")
        self.assertEqual(self.sh("git -C /config ls-files | grep -c onboarding.json || true").stdout.strip(), "0")
        self.assertIn("git: done", self.sh("housemate-onboarding status").stdout)


if __name__ == "__main__":
    unittest.main()

"""Seam A: sharing an improvement, as the image has it.

The tool's logic is tested without a container in tests/suggest; what is asserted
here is what only the image can show: the tool is installed and runs, the rules
tell the agent to use it, and the notification reaches Home Assistant (a stand-in).
That a real model follows the rules is proved on the test VM.
"""

import json
import unittest
import urllib.parse

from test_onboarding import OnboardingAddOn


class Suggest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.addon = OnboardingAddOn({"provider": "zen", "api_key": "", "review_notify": "notify.mobile_app_test_phone"},
                                    {"configuration.yaml": "homeassistant:\n"})
        cls.addon.start()

    @classmethod
    def tearDownClass(cls):
        cls.addon.stop()

    def sh(self, script, **kw):
        return self.addon.exec(script, **kw)

    def test_the_rules_tell_the_agent_to_offer_scrub_confirm_and_link(self):
        rules = self.sh("cat /data/opencode/config/opencode/AGENTS.md").stdout
        for needle in ("housemate-suggest state", "housemate-suggest decline", "housemate-suggest scrub",
                       "**Send**", "housemate-suggest link", "housemate-suggest notify"):
            self.assertIn(needle, rules)

    def test_a_no_is_remembered_in_the_add_ons_record(self):
        self.assertEqual(self.sh("housemate-suggest state skill:x").stdout.strip(), "new")
        self.sh("housemate-suggest decline skill:x")
        self.assertEqual(self.sh("housemate-suggest state skill:x").stdout.strip(), "declined")
        self.assertIn("skill:x", self.sh("cat /config/.housemate/suggest.json").stdout)

    def test_scrub_removes_what_the_house_would_leak(self):
        out = self.sh("printf 'light.lounge_lamp at 10.0.0.9, in the Lounge, api_key: abc123def456' | housemate-suggest scrub")
        for leaked in ("lounge_lamp", "10.0.0.9", "Lounge", "abc123def456"):
            self.assertNotIn(leaked, out.stdout)
        self.assertIn("Area 1", out.stdout)  # the stand-in's area registry was read

    def test_link_is_a_prefilled_ideas_discussion_and_a_long_body_is_split(self):
        self.sh("printf 'A short body.' > /tmp/s.md")
        link = json.loads(self.sh("housemate-suggest link --title T --kind Skill --file /tmp/s.md").stdout)
        self.assertEqual(link["mode"], "full")
        parts = urllib.parse.urlsplit(link["url"])
        self.assertEqual(parts.path, "/jceccato/housemate/discussions/new")
        self.assertEqual(urllib.parse.parse_qs(parts.query)["category"], ["ideas"])
        self.sh("python3 -c \"print('word ' * 5000)\" > /tmp/l.md")
        long = json.loads(self.sh("housemate-suggest link --title T --file /tmp/l.md").stdout)
        self.assertEqual(long["mode"], "short")
        self.assertLessEqual(long["url_chars"], 7000)
        self.assertGreater(len(self.sh(f"cat {long['rest_file']}").stdout), 1000)

    def test_notify_reaches_the_persistent_notification_and_the_phone(self):
        self.sh("housemate-suggest notify --url 'https://github.com/jceccato/housemate/discussions/new?category=ideas'")
        calls = json.loads(self.sh("curl -s http://supervisor/_calls").stdout)
        services = [c["service"] for c in calls]
        self.assertIn("persistent_notification/create", services)
        self.assertIn("notify/mobile_app_test_phone", services)


if __name__ == "__main__":
    unittest.main()

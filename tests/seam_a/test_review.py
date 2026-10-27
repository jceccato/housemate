"""Seam A: the daily update review, driven from outside the add-on.

Home Assistant is the stand-in Supervisor (fake_supervisor.py), which holds a
house with updates waiting. What is asserted is what the household could see:
the notifications, the briefed chat the Review link opens, what is shipped for
the agent to follow, and that nothing is announced when nothing is waiting.
"""

import json
import time
import unittest

import harness
from harness import docker
import test_voice
from test_voice import VoiceAddOn

SELF = "local_housemate_edge"
TARGET = "notify.mobile_app_test_phone"


def update(entity_id, installed, latest, slug=None, platform="hassio", on=True):
    return ({
        "entity_id": entity_id, "state": "on" if on else "off",
        "attributes": {"installed_version": installed, "latest_version": latest, "title": entity_id.split(".")[1],
                       "release_url": "https://github.com/example/thing/releases/tag/" + latest,
                       "entity_picture": None},
    }, {"entity_id": entity_id, "platform": platform,
        "unique_id": f"{slug}_version_latest" if slug else entity_id})


HOUSE = [
    update("update.home_assistant_core_update", "2026.9.3", "2026.10.4"),
    update("update.home_assistant_operating_system_update", "17.3", "18.3"),
    update("update.home_assistant_supervisor_update", "2026.10.0", "2026.10.0", on=False),
    update("update.mosquitto_broker_update", "6.5.0", "6.5.1", slug="core_mosquitto"),
    update("update.housemate_edge_update", "0.1.11", "0.1.12", slug=SELF),
    update("update.some_card_update", "1.0.0", "1.1.0", platform="hacs"),
    update("update.lamp_firmware", "1", "2", platform="zha"),
]


class ReviewAddOn(VoiceAddOn):
    house = []  # nothing waiting while the add-on starts: its own daily run finds nothing

    def _write_options(self):
        super()._write_options()
        self.set_house(self.house)

    def set_house(self, house):
        fake = self.tmp / "fake"
        (fake / "states.json").write_text(json.dumps([s for s, _ in house]))
        (fake / "registry.json").write_text(json.dumps([r for _, r in house]))


class Base:
    @classmethod
    def setUpClass(cls):
        cls.addon = ReviewAddOn({"provider": "zen", "api_key": "hm-test-key-0123456789abcdef",
                                 "review_notify": TARGET, "review_time": "09:00"},
                                {"configuration.yaml": "homeassistant:\n"})
        cls.addon.start()
        cls.wait_endpoint()
        cls.warm_up()
        # The service has made its run for today (and found nothing): the tests run the next ones by hand.
        deadline = time.time() + 90
        while time.time() < deadline and "last_date" not in cls.addon.exec("cat /data/update-review/state.json", check=False).stdout:
            time.sleep(1)
        cls.addon.set_house(HOUSE)
        # Kit changes waiting as incoming: a newer kit than the one /config was seeded from.
        cls.addon.exec("echo 'a better rule' >> /usr/share/housemate/kit/docs/cheat-sheet.md; "
                       "printf '# Kit changelog\\n\\n## Kit version 2\\nA better cheat sheet.\\n' > /usr/share/housemate/kit-changelog.md; "
                       "echo 2 > /usr/share/housemate/kit-version; /usr/share/housemate/seed-kit")

    @classmethod
    def tearDownClass(cls):
        cls.addon.stop()

    def run_daily(self):
        out = self.addon.exec("housemate-updates daily").stdout
        return json.loads(out)

    def calls(self, service):
        out = docker("exec", self.addon.stub, "python3", "-c",
                     "import urllib.request;print(urllib.request.urlopen('http://127.0.0.1/_calls').read().decode())").stdout
        return [c for c in json.loads(out) if c["service"] == service]

    def opencode(self, path):
        return json.loads(self.addon.exec(f"curl -s http://127.0.0.1:4096{path}").stdout)


class Review(Base, unittest.TestCase):
    def test_one_summary_covers_every_source(self):
        done = self.run_daily()
        self.assertTrue(done["sent"])
        persistent = self.calls("persistent_notification/create")[-1]["data"]
        self.assertEqual(persistent["notification_id"], "housemate_update_review")
        text = persistent["message"]
        for source in ("update.home_assistant_core_update", "Home Assistant Core: 2026.9.3 to 2026.10.4",
                       "Operating System: 17.3 to 18.3", "Add-on mosquitto_broker_update: 6.5.0 to 6.5.1",
                       "Housemate: 0.1.11 to 0.1.12", "HACS some_card_update: 1.0.0 to 1.1.0", "kit file",
                       "update.lamp_firmware"):
            if source.startswith("update."):
                continue
            self.assertIn(source, text)
        self.assertIn("not updated by housemate", text.lower())
        self.assertIn("lamp_firmware", text)
        self.assertNotIn("supervisor_update", text, "an update that is not waiting is not listed")
        self.assertRegex(text, rf"\(/app/{SELF}/ses_[A-Za-z0-9]+\)")

    def test_the_phone_gets_the_same_summary_with_a_review_button(self):
        self.run_daily()
        phone = self.calls("notify/mobile_app_test_phone")[-1]["data"]
        self.assertIn("5 updates and", phone["message"].lower() + " " + phone["title"].lower())
        self.assertRegex(phone["data"]["url"], rf"^/app/{SELF}/ses_[A-Za-z0-9]+$")  # the link names the review's chat
        action = phone["data"]["actions"][0]
        self.assertEqual((action["title"], action["uri"]), ("Review", phone["data"]["url"]))

    def test_review_opens_a_briefed_chat_in_which_nothing_has_run(self):
        done = self.run_daily()
        sid = done["session_id"]
        self.assertTrue(any(sid in c["data"]["message"] for c in self.calls("persistent_notification/create")))
        session = self.opencode(f"/session/{sid}")
        self.assertTrue(session["title"].startswith("Update review"))
        time.sleep(3)
        messages = self.opencode(f"/session/{sid}/message")
        self.assertEqual([m["info"]["role"] for m in messages], ["user"], "no model call was made")
        brief = messages[0]["parts"][0]["text"]
        self.assertIn("update-review", brief)
        self.assertIn("Home Assistant Core: 2026.9.3 to 2026.10.4", brief)
        self.assertEqual(self.opencode("/session/status").get(sid, {"type": "idle"})["type"], "idle")

    def test_the_same_updates_the_next_day_reuse_the_chat_and_new_ones_make_a_new_one(self):
        first = self.run_daily()["session_id"]
        self.assertEqual(self.run_daily()["session_id"], first)
        self.addon.set_house(HOUSE + [update("update.new_addon_update", "1", "2", slug="core_new")])
        try:
            self.assertNotEqual(self.run_daily()["session_id"], first)
        finally:
            self.addon.set_house(HOUSE)

    def test_nothing_waiting_sends_nothing(self):
        before = len(self.calls("persistent_notification/create")) + len(self.calls("notify/mobile_app_test_phone"))
        self.addon.set_house([update("update.home_assistant_core_update", "2026.10.4", "2026.10.4", on=False)])
        self.addon.exec("mv /config/.housemate/incoming /config/.housemate/incoming.off")
        try:
            done = self.run_daily()
        finally:
            self.addon.exec("mv /config/.housemate/incoming.off /config/.housemate/incoming")
            self.addon.set_house(HOUSE)
        self.assertFalse(done["sent"])
        after = len(self.calls("persistent_notification/create")) + len(self.calls("notify/mobile_app_test_phone"))
        self.assertEqual(before, after)

    def test_an_option_changed_while_running_is_read_live(self):
        """The Supervisor rewrites /data/options.json only at start: the review asks it instead."""
        fake = self.addon.tmp / "fake" / "options.json"
        original = fake.read_text()
        fake.write_text(json.dumps(dict(json.loads(original), review_notify="notify.mobile_app_new_phone")))
        try:
            self.run_daily()
        finally:
            fake.write_text(original)
        self.assertTrue(self.calls("notify/mobile_app_new_phone"))

    def test_the_prepared_chat_is_marked_as_the_current_session(self):
        sid = self.run_daily()["session_id"]
        self.assertEqual(self.addon.exec("cat /config/.housemate/current-session").stdout.strip(), sid)

    def test_the_agent_is_given_the_procedure(self):
        a = self.addon
        skill = a.exec("cat /data/opencode/config/opencode/skills/update-review/SKILL.md").stdout
        self.assertIn("name: update-review", skill)
        self.assertIn("two approvals", skill.lower())
        howto = a.exec("cat /config/docs/how-to/update-home-assistant.md").stdout
        for needle in ("housemate-updates backup", "Install", "Restart", "one at a time"):
            self.assertIn(needle, howto)
        self.assertIn("update-review", a.exec("cat /data/opencode/config/opencode/AGENTS.md").stdout)

    def test_the_daily_run_is_a_service_and_the_helper_lists_in_install_order(self):
        self.assertEqual(self.addon.exec("grep -l 'updates.py' /proc/[0-9]*/cmdline | head -1 | grep -q . && echo up", check=False).stdout.strip(), "up")
        listed = json.loads(self.addon.exec("housemate-updates list").stdout)
        self.assertEqual([u["kind"] for u in listed], ["os", "core", "addon", "hacs", "housemate", "other"])


class ReviewResume(Base, unittest.TestCase):
    """After a restart the review carries on by itself, but only with both approvals given."""

    def opencode_messages(self, sid):
        """OpenCode's server is not up yet for a moment after a restart: no messages until it is."""
        try:
            return self.opencode(f"/session/{sid}/message")
        except Exception:  # noqa: BLE001
            return []

    def restart(self):
        self.addon.restart()
        self.wait_endpoint()

    def helper(self, *args):
        return json.loads(self.addon.exec("housemate-updates " + " ".join(args)).stdout)

    def test_one_in_flight_with_both_approvals_is_continued_after_a_restart(self):
        sid = self.run_daily()["session_id"]
        self.assertEqual(self.helper("approved", "install")["session"], sid)
        self.helper("approved", "restart")
        self.restart()
        # Wait on the resume having been sent to the chat (the user's own message is stored when
        # OpenCode accepts it), never on a model's reply: how long a model takes is not under test.
        deadline = time.time() + 240
        texts = []
        while time.time() < deadline and not any("do not ask" in t for t in texts):
            time.sleep(1)
            texts = [p["text"] for m in self.opencode_messages(sid) for p in m["parts"] if p["type"] == "text"]
        self.assertTrue(any("do not ask" in t for t in texts), texts)
        while time.time() < deadline and '"resumed"' not in self.addon.exec(
                "cat /config/.housemate/updates/progress.json", check=False).stdout:
            time.sleep(1)
        time.sleep(1)  # the record is written in one go just after the notification
        steps = json.loads(self.addon.exec("cat /config/.housemate/updates/progress.json").stdout)
        self.assertEqual([x["step"] for x in steps].count("resumed"), 1)
        self.assertEqual(self.addon.exec("cat /config/.housemate/current-session").stdout.strip(), sid)
        titles = [c["data"]["title"] for c in self.calls("persistent_notification/create")]
        self.assertIn("Housemate is carrying on", titles)

    def test_the_restart_approval_still_outstanding_waits(self):
        self.addon.exec("rm -f /config/.housemate/updates/progress.json")
        sid = self.run_daily()["session_id"]
        self.helper("approved", "install")
        before = len(self.opencode_messages(sid))
        self.restart()
        time.sleep(15)
        self.assertEqual(len(self.opencode_messages(sid)), before, "nothing was sent to the chat")
        steps = self.addon.exec("cat /config/.housemate/updates/progress.json").stdout
        self.assertNotIn("resumed", steps)

    def test_a_finished_review_is_not_continued(self):
        self.addon.exec("rm -f /config/.housemate/updates/progress.json")
        sid = self.run_daily()["session_id"]
        for step in ("install", "restart"):
            self.helper("approved", step)
        self.helper("finish")
        before = len(self.opencode_messages(sid))
        self.restart()
        time.sleep(15)
        self.assertEqual(len(self.opencode_messages(sid)), before)

    def test_only_the_add_on_itself_may_continue_a_session(self):
        sid = self.run_daily()["session_id"]
        before = len(self.opencode_messages(sid))
        r = self.client("wget", "-qO-", "--header=Content-Type: application/json",
                        f"--post-data={json.dumps({'text': 'x', 'resume_session': sid})}",
                        f"http://{self.addon.name}:8765/kickoff")
        self.assertNotEqual(r.returncode, 0, "refused")
        time.sleep(3)
        self.assertEqual(len(self.opencode_messages(sid)), before)


# The waiting helpers are the voice tests': borrowed, not copied.
for _name in ("client", "wait_endpoint", "warm_up"):
    setattr(Base, _name, classmethod(getattr(test_voice.Voice, _name).__func__))


if __name__ == "__main__":
    unittest.main()

"""The update review's logic, without a container: what is waiting, how it is
summarised, when the daily run is due, what a health check calls a problem, and
which breaking changes touch this house. The HTTP around it is Seam A's
(tests/seam_a/test_review.py)."""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "housemate_edge/rootfs/usr/lib/housemate"))
import updates  # noqa: E402

SELF = "984d4583_housemate_edge"


def state(entity_id, on=True, installed="1.0", latest="1.1", picture=None, url="https://github.com/a/b/releases/tag/1.1", **extra):
    attrs = {"installed_version": installed, "latest_version": latest, "release_url": url,
             "title": entity_id, "entity_picture": picture, "supported_features": 25}
    attrs.update(extra)
    return {"entity_id": entity_id, "state": "on" if on else "off", "attributes": attrs}


STATES = [
    state("update.home_assistant_core_update", installed="2026.9.3", latest="2026.10.4"),
    state("update.home_assistant_operating_system_update", installed="17.3", latest="18.3"),
    state("update.home_assistant_supervisor_update", on=False, installed="2026.10.0", latest="2026.10.0"),
    state("update.mosquitto_broker_update", installed="6.5.0", latest="6.5.1", picture="/api/hassio/addons/core_mosquitto/icon"),
    state("update.core_mariadb_update", installed="2.7.0", latest="2.7.1", picture="/api/hassio/addons/core_mariadb/icon"),
    state("update.housemate_edge_update", installed="0.1.11", latest="0.1.12", picture=f"/api/hassio/addons/{SELF}/icon"),
    state("update.some_card_update", installed="1.0.0", latest="1.1.0"),
    state("update.zigbee_lamp_firmware", installed="1", latest="2"),
    {"entity_id": "light.kitchen", "state": "on", "attributes": {}},
]
REGISTRY = {
    "update.home_assistant_core_update": {"platform": "hassio"},
    "update.home_assistant_operating_system_update": {"platform": "hassio"},
    "update.home_assistant_supervisor_update": {"platform": "hassio"},
    "update.mosquitto_broker_update": {"platform": "hassio"},
    "update.core_mariadb_update": {"platform": "hassio"},
    "update.housemate_edge_update": {"platform": "hassio"},
    "update.some_card_update": {"platform": "hacs"},
    "update.zigbee_lamp_firmware": {"platform": "zha"},
}


class Pending(unittest.TestCase):
    def setUp(self):
        self.found = updates.pending_from(STATES, REGISTRY, SELF)
        self.kinds = {u["entity_id"]: u["kind"] for u in self.found}

    def test_every_source_is_named(self):
        self.assertEqual(self.kinds, {
            "update.home_assistant_core_update": "core",
            "update.home_assistant_operating_system_update": "os",
            "update.mosquitto_broker_update": "addon",
            "update.core_mariadb_update": "addon",
            "update.housemate_edge_update": "housemate",
            "update.some_card_update": "hacs",
            "update.zigbee_lamp_firmware": "other",
        })

    def test_an_add_on_from_a_custom_repository_has_no_picture_but_a_unique_id(self):
        """Seen on Home Assistant 2026.10: the Housemate update entity has no entity_picture."""
        states = [state("update.housemate_edge_update", picture=None)]
        reg = {"update.housemate_edge_update": {"platform": "hassio", "unique_id": f"{SELF}_version_latest"}}
        found = updates.pending_from(states, reg, SELF)
        self.assertEqual((found[0]["kind"], found[0]["slug"]), ("housemate", SELF))
        other = {"update.x": {"platform": "hassio", "unique_id": "core_ssh_version_latest"}}
        self.assertEqual(updates.pending_from([state("update.x")], other, SELF)[0]["slug"], "core_ssh")

    def test_an_update_that_is_off_is_not_waiting(self):
        self.assertNotIn("update.home_assistant_supervisor_update", self.kinds)

    def test_the_order_is_the_order_to_install_in(self):
        order = [u["kind"] for u in self.found]
        self.assertEqual(order, ["os", "core", "addon", "addon", "hacs", "housemate", "other"])
        addons = [u["slug"] for u in self.found if u["kind"] == "addon"]
        self.assertEqual(addons, ["core_mariadb", "core_mosquitto"], "the database add-on goes first, on its own")

    def test_supervisor_comes_first_when_it_is_waiting(self):
        states = STATES + [state("update.home_assistant_supervisor_update", installed="1", latest="2")]
        states = [s for s in states if not (s["entity_id"].endswith("supervisor_update") and s["state"] == "off")]
        reg = dict(REGISTRY, **{"update.home_assistant_supervisor_update": {"platform": "hassio"}})
        self.assertEqual(updates.pending_from(states, reg, SELF)[0]["kind"], "supervisor")

    def test_a_prerelease_is_marked(self):
        found = updates.pending_from([state("update.core_x", latest="2026.11.0b2", picture="/api/hassio/addons/core_x/icon")],
                                     {"update.core_x": {"platform": "hassio"}}, SELF)
        self.assertTrue(found[0]["prerelease"])
        self.assertFalse(self.found[0]["prerelease"])

    def test_a_commit_hash_ending_in_b_is_not_a_prerelease(self):
        for stable in ("2026.10.4", "6.5.1", "v1.2.3", "3f9a1b", "0.1.12"):
            self.assertFalse(updates.is_prerelease(stable), stable)
        for pre in ("2026.11.0b2", "1.2.0-rc1", "3.0.dev1", "1.0.0a1"):
            self.assertTrue(updates.is_prerelease(pre), pre)


class Summary(unittest.TestCase):
    def setUp(self):
        self.found = updates.pending_from(STATES, REGISTRY, SELF)

    def test_nothing_waiting_is_no_summary(self):
        self.assertIsNone(updates.summarise([], None))

    def test_one_line_for_each_source_and_the_kit(self):
        incoming = {"pending": True, "from_kit_version": 1, "kit_version": 2, "counts": {"apply": 3, "merge": 1}}
        s = updates.summarise(self.found, incoming)
        text = s["text"]
        for needle in ("Home Assistant Core: 2026.9.3 to 2026.10.4", "Operating System: 17.3 to 18.3",
                       "mosquitto", "HACS", "Housemate: 0.1.11 to 0.1.12", "4 kit files"):
            self.assertIn(needle, text)
        self.assertIn("not updated by housemate", text.lower())  # the firmware line
        self.assertIn("zigbee_lamp_firmware", text)
        self.assertEqual(s["count"], 6)
        self.assertIn("6 updates", s["title"] + s["short"])

    def test_the_kit_alone_is_still_a_summary(self):
        s = updates.summarise([], {"pending": True, "from_kit_version": 1, "kit_version": 2, "counts": {"apply": 1}})
        self.assertIn("1 kit file", s["text"])

    def test_incoming_that_is_not_pending_is_ignored(self):
        self.assertIsNone(updates.summarise([], {"pending": False, "counts": {}}))

    def test_the_digest_follows_what_is_waiting_not_the_day(self):
        a = updates.digest(self.found, None)
        self.assertEqual(a, updates.digest(list(reversed(self.found)), None))
        self.assertNotEqual(a, updates.digest(self.found[1:], None))
        newer = [dict(u) for u in self.found]
        newer[0]["latest"] = "2026.10.5"
        self.assertNotEqual(a, updates.digest(newer, None))

    def test_the_brief_tells_the_agent_to_load_the_skill_and_wait_for_the_person(self):
        brief = updates.brief(updates.summarise(self.found, None))
        self.assertIn("update-review", brief)
        self.assertIn("nothing has been changed", brief.lower())
        self.assertIn("Home Assistant Core", brief)


class Schedule(unittest.TestCase):
    def test_due_once_after_the_time_each_day(self):
        self.assertFalse(updates.due("08:59", "2026-10-26", None, "09:00"))
        self.assertTrue(updates.due("09:00", "2026-10-26", None, "09:00"))
        self.assertTrue(updates.due("17:30", "2026-10-26", "2026-10-25", "09:00"))
        self.assertFalse(updates.due("17:30", "2026-10-26", "2026-10-26", "09:00"))

    def test_a_bad_time_falls_back_to_the_default(self):
        self.assertEqual(updates.review_time({"review_time": "9am"}), "09:00")
        self.assertEqual(updates.review_time({"review_time": "07:45"}), "07:45")
        self.assertEqual(updates.review_time({}), "09:00")


class Health(unittest.TestCase):
    BASE = {"repairs": ["a/b"], "error_signatures": {"ERROR x | N": 2}, "unavailable": 10, "automations_on": 5}

    def now(self, **kw):
        return dict(self.BASE, **kw)

    def test_the_same_house_is_healthy(self):
        self.assertEqual(updates.compare(self.BASE, self.now(), True, ()), [])

    def test_each_kind_of_regression_is_a_problem(self):
        problems = updates.compare(self.BASE, self.now(
            repairs=["a/b", "c/d"], error_signatures={"ERROR x | N": 9, "ERROR new | N": 1},
            unavailable=25, automations_on=4), False, ())
        text = " ".join(problems)
        for needle in ("not RUNNING", "c/d", "ERROR new", "10 -> 25", "5 -> 4"):
            self.assertIn(needle, text)
        self.assertNotIn("ERROR x", text, "the same fault, logged again, is not new")

    def test_a_small_wander_in_unavailable_is_not_a_problem(self):
        self.assertEqual(updates.compare(self.BASE, self.now(unavailable=20), True, ()), [])

    def test_an_expected_repair_can_be_allowed(self):
        self.assertEqual(updates.compare(self.BASE, self.now(repairs=["a/b", "c/d"]), True, ("c/d",)), [])


INDEX = '<a href="/blog/2026/09/02/release-20269/">x</a><a href="/blog/2026/10/07/release-202610/">y</a><a href="/blog/2026/10/07/release-202610/">y</a>'
POST = """<h2>Intro</h2><p>hi</p>
<h2>Backward-incompatible changes <a href="#b"></a></h2>
<p>We do our best.</p>
<div class="details-block"><details><summary class="details-block-title"><span>Authentication</span><svg></svg></summary>
<div class="details-block-content"><p>Usernames are now lowercase.</p><p>(<a href="https://github.com/x">@x</a>) (<a href="/docs/authentication/providers/">Authentication documentation</a>)</p></div></details></div>
<div class="details-block"><details><summary class="details-block-title"><span>easyEnergy</span></summary>
<div class="details-block-content"><p>Sensors renamed.</p><p>(<a href="/integrations/easyenergy/">easyEnergy documentation</a>)</p></div></details></div>
<div class="details-block"><details><summary class="details-block-title"><span>Hue</span></summary>
<div class="details-block-content"><p>Removed a service.</p><p>(<a href="/integrations/hue/">Hue documentation</a>)</p></div></details></div>
<h2>Need help?</h2><p>no</p>"""


class Breaking(unittest.TestCase):
    def test_core_months_crossed(self):
        self.assertEqual(updates.core_months("2026.9.3", "2026.10.4"), ["2026.10"])
        self.assertEqual(updates.core_months("2026.11.1", "2027.2.0"), ["2026.12", "2027.1", "2027.2"])
        self.assertEqual(updates.core_months("2026.10.1", "2026.10.4"), [], "a patch release crosses no month")

    def test_the_post_is_found_in_the_index(self):
        self.assertEqual(updates.release_post_url(INDEX, "2026.10"), "https://www.home-assistant.io/blog/2026/10/07/release-202610/")
        self.assertEqual(updates.release_post_url(INDEX, "2026.9"), "https://www.home-assistant.io/blog/2026/09/02/release-20269/")
        self.assertIsNone(updates.release_post_url(INDEX, "2026.11"))

    def test_the_breaking_section_becomes_items(self):
        items = updates.breaking_items(POST)
        self.assertEqual([i["title"] for i in items], ["Authentication", "easyEnergy", "Hue"])
        self.assertEqual(items[1]["integration"], "easyenergy")
        self.assertIsNone(items[0]["integration"])
        self.assertIn("Sensors renamed.", items[1]["text"])
        self.assertNotIn("Need help", " ".join(i["text"] for i in items))

    def test_items_are_matched_against_this_house(self):
        items = updates.breaking_items(POST)
        surface = {"integrations": ["hue", "mqtt"], "yaml_keys": ["automation", "easyenergy_x"], "custom_components": []}
        marked = {i["title"]: i["applies"] for i in updates.match_items(items, surface)}
        self.assertEqual(marked, {"Authentication": "general", "easyEnergy": "no", "Hue": "yes"})

    def test_a_post_with_no_breaking_section_has_no_items(self):
        self.assertEqual(updates.breaking_items("<h2>Intro</h2><p>x</p>"), [])


def approved(kind, session="ses_1"):
    return {"step": "approved", "kind": kind, "session": session}


class Resume(unittest.TestCase):
    def test_both_approvals_and_updates_left_means_carry_on(self):
        text = updates.resume_wanted([approved("install"), approved("restart")], True)
        self.assertIn("do not ask", text)
        self.assertIn("housemate-updates status", text)

    def test_the_restart_still_outstanding_waits_as_before(self):
        self.assertIsNone(updates.resume_wanted([approved("install")], True))
        self.assertIsNone(updates.resume_wanted([], True))

    def test_nothing_left_or_finished_means_nothing_to_do(self):
        both = [approved("install"), approved("restart")]
        self.assertIsNone(updates.resume_wanted(both, False))
        self.assertIsNone(updates.resume_wanted(both + [{"step": "review finished"}], True))

    def test_a_new_review_after_a_finished_one_starts_clean(self):
        steps = [approved("install"), approved("restart"), {"step": "review finished"}, approved("install")]
        self.assertEqual(updates.flight(steps)["restart"], False)
        self.assertIsNone(updates.resume_wanted(steps, True))

    def test_a_review_that_keeps_dying_is_left_to_the_person(self):
        steps = [approved("install"), approved("restart")] + [{"step": "resumed"}] * updates.MAX_RESUMES
        self.assertIsNone(updates.resume_wanted(steps, True))
        self.assertIsNotNone(updates.resume_wanted(steps[:-1], True))

    def test_the_session_is_the_one_the_approvals_named(self):
        steps = [approved("install", "ses_a"), approved("restart", "ses_b")]
        self.assertEqual(updates.flight(steps)["session"], "ses_b")


if __name__ == "__main__":
    unittest.main()

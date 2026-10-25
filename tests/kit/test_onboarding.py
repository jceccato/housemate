"""Onboarding: the scan that seeds the cheat sheet, and the record of progress.

Run on the host against fixture registries (no container, no Home Assistant).
The container-level proof, against a stand-in Supervisor, is
tests/seam_a/test_onboarding.py.
"""

import importlib.machinery
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

TOOL = Path(__file__).resolve().parents[2] / "housemate_edge" / "rootfs" / "usr" / "local" / "bin" / "housemate-onboarding"


def load(config_dir):
    loader = importlib.machinery.SourceFileLoader("housemate_onboarding", str(TOOL))
    spec = importlib.util.spec_from_loader("housemate_onboarding", loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    module.CONFIG = str(config_dir)
    module.STATE_FILE = str(Path(config_dir) / ".housemate" / "onboarding.json")
    module.SHEET = str(Path(config_dir) / "docs" / "cheat-sheet.md")
    return module


def state(entity_id, name=None, **attributes):
    if name:
        attributes["friendly_name"] = name
    return {"entity_id": entity_id, "state": "on", "attributes": attributes}


AREAS = [{"area_id": "lounge", "name": "Lounge"}, {"area_id": "hall", "name": "Hall"}]
DEVICES = [{"id": "dev1", "area_id": "hall"}, {"id": "dev2", "area_id": None}]
ENTITIES = [
    {"entity_id": "light.lamp", "name": "Reading lamp", "area_id": "lounge", "aliases": ["the lamp"]},
    {"entity_id": "light.hall_ceiling", "device_id": "dev1"},
    {"entity_id": "sensor.hall_battery", "device_id": "dev1", "entity_category": "diagnostic"},
    {"entity_id": "switch.old", "disabled_by": "user"},
    {"entity_id": "switch.hidden", "hidden_by": "user"},
    {"entity_id": "sensor.power", "device_id": "dev2", "original_name": "Power"},
]
STATES = [
    state("light.lamp", "Lamp (from the integration)"),
    state("light.hall_ceiling", "Hall ceiling"),
    state("sensor.hall_battery", "Hall battery", device_class="battery"),
    state("switch.old", "Old"),
    state("switch.hidden", "Hidden"),
    state("sensor.power", "Power", device_class="power", unit_of_measurement="W"),
    state("climate.study", "Study aircon"),  # no registry entry: a YAML-defined entity
    state("update.core", "Core update"),
    state("button.restart", "Restart"),
    state("sun.sun", "Sun"),
]


class Scan(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.mod = load(self.tmp.name)
        self.rows, self.left_out = self.mod.build_rows(STATES, ENTITIES, DEVICES, AREAS)
        self.by_id = {r["entity_id"]: r for r in self.rows}

    def test_the_name_a_person_set_beats_the_integrations_name(self):
        self.assertEqual(self.by_id["light.lamp"]["name"], "Reading lamp")
        self.assertEqual(self.by_id["light.hall_ceiling"]["name"], "Hall ceiling")

    def test_an_entity_takes_its_devices_area_when_it_has_none_of_its_own(self):
        self.assertEqual(self.by_id["light.lamp"]["area"], "Lounge")
        self.assertEqual(self.by_id["light.hall_ceiling"]["area"], "Hall")
        self.assertEqual(self.by_id["sensor.power"]["area"], "")

    def test_disabled_hidden_diagnostic_and_unaskable_things_are_left_out(self):
        self.assertEqual(
            sorted(self.by_id),
            ["climate.study", "light.hall_ceiling", "light.lamp", "sensor.power"],
        )

    def test_an_entity_with_no_registry_entry_is_still_listed(self):
        self.assertEqual(self.by_id["climate.study"]["name"], "Study aircon")

    def test_aliases_and_units_are_in_the_notes(self):
        self.assertIn('also called "the lamp"', self.by_id["light.lamp"]["notes"])
        self.assertIn("power (W)", self.by_id["sensor.power"]["notes"])

    def test_rooms_come_first_alphabetically_and_unassigned_things_last(self):
        self.assertEqual([r["area"] for r in self.rows], ["Hall", "Lounge", "", ""])

    def test_a_long_house_is_cut_and_says_so(self):
        many = [state(f"light.l{i:04}", f"Light {i}") for i in range(self.mod.MAX_ROWS + 25)]
        rows, left_out = self.mod.build_rows(many, [], [], [])
        self.assertEqual((len(rows), left_out), (self.mod.MAX_ROWS, 25))
        self.assertIn("25 more were left out", self.mod.render_block(rows, left_out, [], []))

    def test_the_table_survives_a_pipe_in_a_name(self):
        rows = [{"name": "Tom | Jerry", "entity_id": "light.x", "area": "", "notes": "light"}]
        self.assertIn("| Tom / Jerry |", self.mod.render_block(rows, 0, [], []))


class Sheet(unittest.TestCase):
    def setUp(self):
        self.mod = load("/nonexistent")
        self.block = self.mod.render_block(
            [{"name": "Lamp", "entity_id": "light.lamp", "area": "Lounge", "notes": "light"}], 0, AREAS, DEVICES, when="T")

    def test_it_goes_before_the_quirks_and_keeps_the_users_words(self):
        sheet = "# Cheat sheet\n\nMine.\n\n## Quirks\n\n- The porch light flickers.\n"
        placed = self.mod.place_block(sheet, self.block)
        self.assertLess(placed.index("light.lamp"), placed.index("## Quirks"))
        self.assertIn("Mine.", placed)
        self.assertTrue(placed.endswith("- The porch light flickers.\n"))

    def test_running_it_twice_changes_nothing_and_a_rescan_replaces_only_its_block(self):
        sheet = "# Cheat sheet\n\n## Quirks\n\n- Mine.\n"
        once = self.mod.place_block(sheet, self.block)
        self.assertEqual(self.mod.place_block(once, self.block), once)
        newer = self.mod.render_block(
            [{"name": "Fan", "entity_id": "fan.fan", "area": "", "notes": "fan"}], 0, AREAS, DEVICES, when="T2")
        again = self.mod.place_block(once, newer)
        self.assertNotIn("light.lamp", again)
        self.assertIn("fan.fan", again)
        self.assertEqual(again.count(self.mod.START), 1)
        self.assertIn("- Mine.", again)

    def test_a_sheet_with_no_quirks_gets_it_at_the_end(self):
        placed = self.mod.place_block("# Mine\n", self.block)
        self.assertTrue(placed.startswith("# Mine\n"))
        self.assertTrue(placed.rstrip().endswith(self.mod.END))


class ReviewNotify(unittest.TestCase):
    def setUp(self):
        self.mod = load("/nonexistent")

    def test_only_the_review_phone_changes_and_the_key_is_kept(self):
        options = {"provider": "go", "api_key": "k", "review_time": "09:00"}
        self.assertEqual(
            self.mod.with_review_notify(options, "notify.mobile_app_pixel"),
            {**options, "review_notify": "notify.mobile_app_pixel"})

    def test_something_that_is_not_a_notify_service_is_refused(self):
        for bad in ("", "light.lamp", "notify.", "notify.a b", "notify.mobile_app_x; rm"):
            with self.assertRaises(SystemExit):
                self.mod.with_review_notify({}, bad)


class Progress(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.mod = load(self.tmp.name)

    def test_a_fresh_install_is_new(self):
        self.assertEqual(self.mod.overall(self.mod.load_state()), "new")

    def test_touching_a_step_starts_it_and_every_step_settled_completes_it(self):
        self.mod.set_step("provider", "done", "zen")
        self.assertEqual(self.mod.overall(self.mod.load_state()), "in_progress")
        for step in self.mod.STEPS:
            self.mod.set_step(step, "skipped" if step == "remote" else "done")
        self.assertEqual(self.mod.overall(self.mod.load_state()), "complete")

    def test_declining_stops_the_offer_but_not_a_later_start(self):
        data = self.mod.load_state()
        data["declined"] = True
        self.mod.save_state(data)
        self.assertEqual(self.mod.overall(self.mod.load_state()), "declined")
        self.mod.set_step("provider", "done")
        self.assertEqual(self.mod.overall(self.mod.load_state()), "in_progress")

    def test_a_step_can_be_run_again_after_it_was_skipped(self):
        self.mod.set_step("remote", "skipped")
        self.mod.set_step("remote", "pending")
        self.assertEqual(self.mod.load_state()["steps"]["remote"]["state"], "pending")

    def test_progress_is_written_where_git_ignores_it(self):
        self.mod.set_step("git", "done")
        self.assertTrue((Path(self.tmp.name) / ".housemate" / "onboarding.json").is_file())
        data = json.loads((Path(self.tmp.name) / ".housemate" / "onboarding.json").read_text())
        self.assertEqual(data["steps"]["git"]["state"], "done")

    def test_a_wrong_step_or_state_is_refused(self):
        with self.assertRaises(SystemExit):
            self.mod.set_step("nonsense", "done")
        with self.assertRaises(SystemExit):
            self.mod.set_step("git", "finished")


if __name__ == "__main__":
    unittest.main()

"""housemate-suggest: scrubbing, the pre-filled link, and the memory of a "no".

Host-side, no container and no Home Assistant: the house's registries are passed
in as plain data. The seeded personal details below are made up; the tests prove
none of them survives the scrub.
"""

import importlib.machinery
import importlib.util
import json
import tempfile
import unittest
import urllib.parse
from pathlib import Path

TOOL = Path(__file__).resolve().parents[2] / "housemate_edge" / "rootfs" / "usr" / "local" / "bin" / "housemate-suggest"


def load():
    loader = importlib.machinery.SourceFileLoader("housemate_suggest", str(TOOL))
    spec = importlib.util.spec_from_loader("housemate_suggest", loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


S = load()

HOUSE = {
    "names": ["Priya Raman", "Sam"],
    "areas": ["Garage Studio"],
    "devices": ["Hallway Thermostat Pro"],
    "friendly_names": ["Priya's Bedside Lamp"],
    "places": ["Raman Residence"],
    "latitude": -33.865143,
    "longitude": 151.209900,
}


class Scrub(unittest.TestCase):
    def scrub(self, text, house=None):
        return S.scrub(text, house or {})[0]

    def assertGone(self, text, *secrets, house=None):
        out = self.scrub(text, house)
        for secret in secrets:
            self.assertNotIn(secret, out, f"{secret!r} survived: {out!r}")
        return out

    def test_entity_ids_become_numbered_placeholders_consistently(self):
        out = self.assertGone("turn off light.priyas_lamp then light.priyas_lamp and switch.garage_heater",
                              "priyas_lamp", "garage_heater")
        self.assertEqual(out, "turn off light.example then light.example and switch.example_2")

    def test_service_names_survive(self):
        out = self.scrub("call light.turn_on, automation.reload and homeassistant.restart")
        self.assertEqual(out, "call light.turn_on, automation.reload and homeassistant.restart")

    def test_entities_that_merely_start_like_a_service_are_scrubbed(self):
        out = self.assertGone("automation.run_kitchen_lights script.call_mum sensor.pressure_bedroom "
                              "sensor.lock_battery switch.start_pool_pump sensor.media_room_temp",
                              "kitchen", "call_mum", "pressure", "battery", "pool_pump", "media_room")

    def test_existing_placeholders_are_not_merged_with_new_ones(self):
        out = self.scrub("light.example is a placeholder; light.kitchen is real")
        self.assertEqual(out, "light.example is a placeholder; light.example_2 is real")

    def test_code_is_not_mangled(self):
        text = "x[1::2] and sensor.some_really_long_object_identifier_with_digits_1234567890abcdef"
        self.assertTrue(self.scrub(text).startswith("x[1::2] and sensor."))

    def test_corp_hosts(self):
        self.assertGone("ssh nas.corp", "nas.corp")

    def test_file_names_are_not_taken_for_entities(self):
        self.assertEqual(self.scrub("edit configuration.yaml and packages/lights.yaml"),
                         "edit configuration.yaml and packages/lights.yaml")

    def test_ip_addresses_mac_addresses_and_emails(self):
        out = self.assertGone("host 192.168.1.50, also 10.0.0.7; mac AA:BB:CC:11:22:33; mail jo.bloggs@gmail.com; v6 fe80::1ff:fe23:4567:890a",
                              "192.168.1.50", "10.0.0.7", "AA:BB:CC", "jo.bloggs", "fe80::")
        self.assertIn("192.0.2.1", out)
        self.assertIn("user@example.com", out)

    def test_same_ip_gets_the_same_placeholder(self):
        out = self.scrub("10.1.2.3 and 10.1.2.4 and 10.1.2.3")
        self.assertEqual(out, "192.0.2.1 and 192.0.2.2 and 192.0.2.1")

    def test_private_hostnames_and_urls(self):
        out = self.assertGone(
            "open http://homeassistant.local:8123/lovelace/0 or https://nas.lan/x or https://abc123.ui.nabu.casa/ "
            "or https://myhouse.duckdns.org or http://192.168.0.2:8123/api?token=zzz",
            "homeassistant.local", "nas.lan", "abc123", "myhouse", "192.168.0.2", "zzz")
        self.assertIn("example.invalid", out)

    def test_public_urls_survive_without_their_query(self):
        out = self.scrub("see https://www.home-assistant.io/docs/automation/?utm=abc#top")
        self.assertEqual(out, "see https://www.home-assistant.io/docs/automation/")

    def test_url_credentials_are_dropped(self):
        self.assertGone("git clone https://bob:hunter2@github.com/bob/private.git", "hunter2", "bob:")

    def test_tokens_and_keys(self):
        jwt = "eyJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJhYmMifQ.c2lnbmF0dXJlc2lnbmF0dXJl"
        self.assertGone(
            "Authorization: Bearer abcdef1234567890abcdef\n"
            "token ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789\n"
            "key sk-proj-abcdefghijklmnop1234\n"
            f"jwt {jwt}\n"
            "api_key: s3cr3tvalue\n"
            'password = "hunter2hunter2"\n'
            "hash 0123456789abcdef0123456789abcdef0123456789abcdef\n"
            "-----BEGIN PRIVATE KEY-----\nMIIBVQIBADANBgkqhkiG9w0BAQEFAASC\n-----END PRIVATE KEY-----",
            "abcdef1234567890abcdef", "ghp_ABC", "sk-proj", "eyJhbGci", "s3cr3tvalue", "hunter2hunter2",
            "0123456789abcdef0123456789abcdef", "MIIBVQ")

    def test_secret_references_are_kept(self):
        self.assertEqual(self.scrub("api_key: !secret openai_key"), "api_key: !secret openai_key")

    def test_coordinates(self):
        self.assertGone("latitude: -33.865143\nlongitude: 151.2099\nhome at -33.865143, 151.209900", "33.865143", "151.2099")

    def test_registry_terms_by_kind_and_case(self):
        text = "Priya asked; PRIYA RAMAN and Priya's Bedside Lamp is in the garage studio near the Hallway Thermostat Pro at Raman Residence. Sam too."
        out = self.assertGone(text, "Priya", "Raman", "Bedside", "garage studio", "Hallway Thermostat", house=HOUSE)
        self.assertIn("Person 1", out)
        self.assertIn("Area 1", out)
        self.assertIn("Device 1", out)

    def test_registry_terms_do_not_eat_inside_longer_words(self):
        out = self.scrub("Samsung and sample", {"names": ["Sam"]})
        self.assertEqual(out, "Samsung and sample")

    def test_house_coordinates_from_registry(self):
        self.assertGone("lat -33.8651 lon 151.2099", "33.8651", "151.2099", house=HOUSE)

    def test_the_report_counts_without_echoing_values(self):
        _, report = S.scrub("light.priyas_lamp at 10.0.0.9", {})
        self.assertEqual(report["entity"], 1)
        self.assertEqual(report["ip"], 1)
        self.assertNotIn("priyas", json.dumps(report))

    def test_idempotent(self):
        once = self.scrub("light.priyas_lamp 10.0.0.9 jo@gmail.com", HOUSE)
        self.assertEqual(self.scrub(once, HOUSE), once)

    def test_generic_text_is_left_alone(self):
        text = "## Runbook\n\n1. Check the config.\n2. Reload automations.\n"
        self.assertEqual(self.scrub(text), text)


class Link(unittest.TestCase):
    def parse(self, url):
        parts = urllib.parse.urlsplit(url)
        return parts, urllib.parse.parse_qs(parts.query)

    def test_a_short_suggestion_fits_in_one_link(self):
        link = S.build_link("Skill: tidy lights", "A short body.\n\nWith *markdown* & symbols?", kind="Skill")
        self.assertEqual(link["mode"], "full")
        parts, q = self.parse(link["url"])
        self.assertEqual((parts.netloc, parts.path), ("github.com", "/jceccato/housemate/discussions/new"))
        self.assertEqual(q["category"], ["ideas"])
        self.assertEqual(q["title"], ["Skill: tidy lights"])
        self.assertEqual(q["body"], ["A short body.\n\nWith *markdown* & symbols?"])
        self.assertEqual(q["kind"], ["Skill"])
        self.assertIsNone(link["rest"])

    def test_a_long_body_becomes_a_short_body_and_the_rest(self):
        body = "\n\n".join(f"Paragraph {i}: " + "word " * 60 for i in range(80))
        link = S.build_link("Long one", body)
        self.assertEqual(link["mode"], "short")
        self.assertLessEqual(len(link["url"]), S.MAX_URL)
        _, q = self.parse(link["url"])
        self.assertTrue(q["body"][0].startswith("Paragraph 0"))
        self.assertIn("rest", q["body"][0].lower())
        self.assertTrue(link["rest"])
        # Nothing is lost: the link's body (minus the note) plus the rest is the original.
        head = q["body"][0].split(S.NOTE_MARK)[0].rstrip()
        self.assertEqual((head + "\n\n" + link["rest"]).split(), body.split())

    def test_one_enormous_paragraph_is_still_split(self):
        body = "x" * 20000
        link = S.build_link("Huge", body)
        self.assertEqual(link["mode"], "short")
        self.assertLessEqual(len(link["url"]), S.MAX_URL)
        self.assertGreater(len(link["rest"]), 10000)

    def test_a_huge_title_cannot_break_the_limit(self):
        self.assertLessEqual(len(S.build_link("t" * 20000, "body")["url"]), S.MAX_URL)

    def test_a_multibyte_body_is_measured_encoded(self):
        link = S.build_link("Emoji", "é" * 3000)
        self.assertLessEqual(len(link["url"]), S.MAX_URL)


class Memory(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = str(Path(self.tmp.name) / ".housemate" / "suggest.json")

    def tearDown(self):
        self.tmp.cleanup()

    def test_new_then_declined_then_shared(self):
        self.assertEqual(S.item_state(self.path, "skill:tidy-lights"), "new")
        S.record(self.path, "skill:tidy-lights", "declined")
        self.assertEqual(S.item_state(self.path, "skill:tidy-lights"), "declined")
        self.assertEqual(S.item_state(self.path, "skill:other"), "new")
        S.record(self.path, "skill:other", "shared")
        self.assertEqual(S.item_state(self.path, "skill:other"), "shared")

    def test_the_key_is_normalised(self):
        S.record(self.path, "Skill: Tidy Lights", "declined")
        self.assertEqual(S.item_state(self.path, "skill:  tidy lights"), "declined")

    def test_a_broken_file_reads_as_new(self):
        Path(self.path).parent.mkdir(parents=True)
        Path(self.path).write_text("{not json")
        self.assertEqual(S.item_state(self.path, "x"), "new")


if __name__ == "__main__":
    unittest.main()

"""The name you call Housemate by: validation, the sentences made from it, and the rename."""

import importlib.machinery
import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

TOOL = Path(__file__).resolve().parents[2] / "housemate_edge" / "rootfs" / "usr" / "local" / "bin" / "housemate-voice"


def load():
    loader = importlib.machinery.SourceFileLoader("housemate_voice", str(TOOL))
    spec = importlib.util.spec_from_loader("housemate_voice", loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


V = load()


class Check(unittest.TestCase):
    def test_the_default_and_an_ordinary_name_pass(self):
        self.assertEqual(V.check("Housemate"), ("Housemate", []))
        self.assertEqual(V.check("Jarvis")[0], "Jarvis")
        self.assertEqual(V.check("  Max   the  Butler ")[0], "Max the Butler")

    def test_hey_and_a_trailing_comma_are_dropped(self):
        self.assertEqual(V.check("Hey Jarvis,")[0], "Jarvis")

    def test_empty_or_blank_is_refused(self):
        for bad in ("", "   ", None, "hey", ","):
            with self.assertRaises(V.BadName, msg=repr(bad)):
                V.check(bad)

    def test_a_word_home_assistants_own_commands_start_with_is_refused(self):
        for bad in ("Turn", "turn it", "What", "Set the table", "Play", "stop", "Shopping list", "OK"):
            with self.assertRaises(V.BadName, msg=bad):
                V.check(bad)

    def test_sentence_syntax_and_odd_characters_are_refused(self):
        for bad in ("Jar{vis}", "Jar[vis]", "a|b", "Jarvis <x>", "Jarvis; rm", 'say "hi"'):
            with self.assertRaises(V.BadName, msg=bad):
                V.check(bad)

    def test_too_long_or_too_many_words_is_refused(self):
        with self.assertRaises(V.BadName):
            V.check("x" * 25)
        with self.assertRaises(V.BadName):
            V.check("one two three four")

    def test_an_everyday_word_or_a_device_with_that_name_is_a_warning_not_a_refusal(self):
        name, warnings = V.check("Home")
        self.assertEqual(name, "Home")
        self.assertTrue(warnings and "everyday" in warnings[0])
        name, warnings = V.check("Kitchen Radio", known_names=["kitchen radio"])
        self.assertTrue(any("also called" in w for w in warnings))

    def test_apostrophes_hyphens_digits_and_other_scripts_are_fine(self):
        for ok in ("Mo's", "Jar-vis", "R2 D2", "Élan"):
            self.assertEqual(V.check(ok)[0], ok)


class Sentences(unittest.TestCase):
    def test_both_forms_are_made_from_the_name_without_a_comma(self):
        self.assertEqual(V.phrases("Jarvis"), ["Jarvis {request}", "Hey Jarvis {request}"])

    def test_the_package_carries_the_phrases_and_the_phone(self):
        text = V.package_text("Jarvis", "notify.mobile_app_x")
        self.assertIn('notify_service: "notify.mobile_app_x"', text)
        self.assertIn('- "Jarvis {request}"', text)
        self.assertIn("path: housemate/voice_kickoff.yaml", text)
        self.assertEqual(V.current_name(text), "Jarvis")

    def test_the_default_name_reads_back(self):
        self.assertEqual(V.current_name(V.package_text("Housemate")), "Housemate")

    def test_a_rename_changes_only_the_phrases(self):
        text = V.package_text("Housemate", "notify.mobile_app_x")
        out = V.rename_text(text, "Jarvis")
        self.assertEqual(V.current_name(out), "Jarvis")
        self.assertIn('"Hey Jarvis {request}"', out)
        self.assertNotIn("Housemate {request}", out)
        self.assertIn('notify_service: "notify.mobile_app_x"', out)
        self.assertEqual(V.rename_text(out, "Housemate"), text)

    def test_a_package_without_phrases_cannot_be_renamed(self):
        with self.assertRaises(V.BadName):
            V.rename_text("automation: []\n", "Jarvis")


class Commands(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        p = mock.patch.object(V, "PACKAGE", os.path.join(self.tmp.name, "packages", "housemate_voice.yaml"))
        p.start()
        self.addCleanup(p.stop)
        q = mock.patch.object(V, "house_names", lambda: [])
        q.start()
        self.addCleanup(q.stop)
        self.calls = []

    def fake_api(self, result="valid"):
        def api(path, method="GET", body=None):
            self.calls.append((method, path))
            return {"result": result} if path.endswith("check_config") else None
        p = mock.patch.object(V, "api", api)
        p.start()
        self.addCleanup(p.stop)

    def test_write_then_rename_checks_reloads_and_needs_no_restart(self):
        self.assertEqual(V.main(["write-package", "Housemate", "notify.mobile_app_x"]), 0)
        self.fake_api()
        self.assertEqual(V.main(["rename", "Jarvis"]), 0)
        self.assertEqual(V.current_name(open(V.PACKAGE).read()), "Jarvis")
        self.assertEqual(self.calls, [("POST", "/api/config/core/check_config"), ("POST", "/api/services/automation/reload")])

    def test_a_rename_that_fails_the_check_puts_the_old_name_back(self):
        V.main(["write-package", "Housemate"])
        self.fake_api(result="invalid")
        self.assertEqual(V.main(["rename", "Jarvis"]), 1)
        self.assertEqual(V.current_name(open(V.PACKAGE).read()), "Housemate")
        self.assertNotIn(("POST", "/api/services/automation/reload"), self.calls)

    def test_a_refused_name_changes_nothing(self):
        V.main(["write-package", "Housemate"])
        before = open(V.PACKAGE).read()
        self.fake_api()
        self.assertEqual(V.main(["rename", "Turn"]), 1)
        self.assertEqual(open(V.PACKAGE).read(), before)
        self.assertEqual(self.calls, [])

    def test_write_package_will_not_overwrite_and_a_bad_name_writes_nothing(self):
        self.assertEqual(V.main(["write-package", "Turn"]), 1)
        self.assertFalse(os.path.exists(V.PACKAGE))
        V.main(["write-package", "Max"])
        self.assertEqual(V.main(["write-package", "Jarvis"]), 1)
        self.assertEqual(V.current_name(open(V.PACKAGE).read()), "Max")


if __name__ == "__main__":
    unittest.main()

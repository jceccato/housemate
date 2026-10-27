"""The link in a notification names the chat it is about."""

import pathlib
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "housemate_edge/rootfs/usr/lib/housemate"))
import kickoff  # noqa: E402


class PanelUrl(unittest.TestCase):
    def setUp(self):
        p = mock.patch.object(kickoff, "addon_slug", return_value="abc_housemate_edge")
        p.start()
        self.addCleanup(p.stop)

    def test_without_a_chat_it_is_the_panel(self):
        self.assertEqual(kickoff.panel_url(), "/app/abc_housemate_edge")

    def test_with_a_chat_it_names_it_after_the_slug(self):
        self.assertEqual(kickoff.panel_url("ses_e86697451ffe2xz2Avynge19Ui"), "/app/abc_housemate_edge/ses_e86697451ffe2xz2Avynge19Ui")

    def test_anything_that_is_not_a_chat_id_is_left_out(self):
        for bad in ("../x", "ses_ ", "", None, "ses_a/b", 5):
            self.assertEqual(kickoff.panel_url(bad), "/app/abc_housemate_edge", bad)

    def test_the_notification_carries_the_chat_link_both_ways(self):
        calls = []
        with mock.patch.object(kickoff, "service", lambda d, n, data: calls.append((d, n, data))):
            kickoff.notify("ses_abc123", "mobile_app_x", "Housemate needs you", "Which room?")
        phone = calls[0][2]["data"]
        self.assertEqual((phone["url"], phone["clickAction"]), ("/app/abc_housemate_edge/ses_abc123",) * 2)
        self.assertIn("(/app/abc_housemate_edge/ses_abc123)", calls[1][2]["message"])


if __name__ == "__main__":
    unittest.main()

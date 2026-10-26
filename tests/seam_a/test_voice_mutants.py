"""The voice tests must be able to fail: break the image two ways and check they notice."""

import unittest

import harness
import test_voice
from harness import docker

KICKOFF = "/usr/lib/housemate/kickoff.py"
OPENCODE_RUN = "/etc/s6-overlay/s6-rc.d/opencode-server/run"


def failures_with(dockerfile_lines, test_name):
    """Run one Voice test against a broken image; the failures it reports."""
    tag = harness.build_image("voice", dockerfile_lines)
    saved = harness.IMAGE
    harness.IMAGE = tag
    try:
        result = unittest.TestResult()
        unittest.defaultTestLoader.loadTestsFromName(f"test_voice.Voice.{test_name}").run(result)
        return result.failures + result.errors
    finally:
        harness.IMAGE = saved
        docker("rmi", "-f", tag, check=False)


class VoiceMutants(unittest.TestCase):
    def test_everyone_treated_as_an_admin_is_caught(self):
        failed = failures_with(
            [f"RUN sed -i 's|^def who_asked(user_id):|def who_asked(user_id):\\n    return True, \"Anyone\"|' {KICKOFF}"],
            "test_a_non_admins_request_waits_in_the_chat",
        )
        self.assertTrue(failed)

    def test_opencodes_server_on_the_network_is_caught(self):
        failed = failures_with(
            [f"RUN sed -i 's|--hostname 127.0.0.1|--hostname 0.0.0.0|' {OPENCODE_RUN}"],
            "test_the_host_cannot_reach_it_but_the_network_can",
        )
        self.assertTrue(failed)

    def test_no_notification_is_caught(self):
        failed = failures_with(
            [f"RUN sed -i 's|^def notify(session_id, target, title, message):|def notify(session_id, target, title, message):\\n    return|' {KICKOFF}"],
            "test_an_admins_request_starts_a_session_and_notifies_without_waiting",
        )
        self.assertTrue(failed)


if __name__ == "__main__":
    unittest.main()

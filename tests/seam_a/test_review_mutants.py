"""The review tests must be able to fail: break the image two ways and check they notice."""

import unittest

import harness
import test_review
from harness import docker

UPDATES = "/usr/lib/housemate/updates.py"
KICKOFF = "/usr/lib/housemate/kickoff.py"


def failures_with(dockerfile_lines, test_name):
    """Run one Review test against a broken image; the failures it reports."""
    tag = harness.build_image("review", dockerfile_lines)
    saved = harness.IMAGE
    harness.IMAGE = tag
    try:
        result = unittest.TestResult()
        unittest.defaultTestLoader.loadTestsFromName((test_name if "." in test_name else f"test_review.Review.{test_name}")).run(result)
        return result.failures + result.errors
    finally:
        harness.IMAGE = saved
        docker("rmi", "-f", tag, check=False)


class ReviewMutants(unittest.TestCase):
    def test_a_summary_that_leaves_out_hacs_is_caught(self):
        failed = failures_with(
            [f"RUN sed -i 's|todo = \\[u for u in found if u\\[\"kind\"\\] != \"other\"\\]|todo = [u for u in found if u[\"kind\"] not in (\"other\", \"hacs\")]|' {UPDATES}"],
            "test_one_summary_covers_every_source",
        )
        self.assertTrue(failed)

    def test_a_review_chat_that_starts_running_is_caught(self):
        failed = failures_with(
            [f"RUN sed -i 's|{{\"noReply\": True, \"parts\"|{{\"parts\"|' {KICKOFF}"],
            "test_review_opens_a_briefed_chat_in_which_nothing_has_run",
        )
        self.assertTrue(failed)

    def test_resuming_without_the_restart_approval_is_caught(self):
        failed = failures_with(
            [f"RUN sed -i 's|f\\[\"install\"\\] and f\\[\"restart\"\\] and|f[\"install\"] and|' {UPDATES}"],
            "test_review.ReviewResume.test_the_restart_approval_still_outstanding_waits",
        )
        self.assertTrue(failed)


if __name__ == "__main__":
    unittest.main()

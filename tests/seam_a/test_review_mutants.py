"""The review tests must be able to fail: break the image two ways and check they notice."""

import os
import tempfile
import unittest
from pathlib import Path

import harness
import test_review
from harness import docker

UPDATES = "/usr/lib/housemate/updates.py"
KICKOFF = "/usr/lib/housemate/kickoff.py"


def failures_with(dockerfile_lines, test_name):
    """Run one Review test against a broken image; the failures it reports."""
    with tempfile.TemporaryDirectory() as d:
        Path(d, "Dockerfile").write_text(f"FROM {harness.IMAGE}\n" + "\n".join(dockerfile_lines) + "\n")
        tag = f"housemate-mutant-review:{os.getpid()}"
        docker("build", "-q", "-t", tag, d)
    saved = harness.IMAGE
    harness.IMAGE = tag
    try:
        result = unittest.TestResult()
        unittest.defaultTestLoader.loadTestsFromName(f"test_review.Review.{test_name}").run(result)
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


if __name__ == "__main__":
    unittest.main()

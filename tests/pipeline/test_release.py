"""The release pipeline's decisions, tested without a network.

    python3 -m unittest discover -s tests/pipeline -v

`.github/scripts/release.py` holds every decision the publish and promotion
workflows make (which version to publish, what the changelog says, what stable
becomes). The workflows only call it, so this is the seam.
"""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / ".github" / "scripts"))

import release  # noqa: E402

EDGE_CONFIG = """\
name: Housemate (edge)
version: 0.1.4
slug: housemate_edge
description: The newest Housemate build, for testers.
url: https://github.com/jceccato/housemate
# comment: version: 9.9.9 must not be touched
image: ghcr.io/jceccato/{arch}-housemate-edge
arch:
  - aarch64
  - amd64
panel_title: Housemate
options:
  provider: go
"""

CHANGELOG = """\
# Changelog

## 0.1.4

- Fourth.

## 0.1.3

- Third.
- Third again.

## 0.1.2

- Second.

## 0.1.0

- First.
"""


class Versions(unittest.TestCase):
    def test_read_version_ignores_comments_and_quotes(self):
        self.assertEqual(release.read_version(EDGE_CONFIG), "0.1.4")
        self.assertEqual(release.read_version('version: "1.2.3"\n'), "1.2.3")

    def test_read_version_fails_without_one(self):
        with self.assertRaises(release.PipelineError):
            release.read_version("name: x\n")

    def test_set_version_changes_only_the_version_line(self):
        out = release.set_version(EDGE_CONFIG, "0.1.5")
        self.assertEqual(release.read_version(out), "0.1.5")
        self.assertEqual(out.replace("0.1.5", "0.1.4", 1), EDGE_CONFIG)

    def test_bump_patch_is_numeric_not_textual(self):
        self.assertEqual(release.bump_patch("0.1.9"), "0.1.10")

    def test_compare_is_numeric(self):
        self.assertLess(release.parse("0.1.9"), release.parse("0.1.10"))

    def test_junk_versions_are_refused(self):
        for v in ("1.2", "1.2.3-rc1", "v1.2.3", "latest", ""):
            with self.assertRaises(release.PipelineError, msg=v):
                release.parse(v)


class Plan(unittest.TestCase):
    """Which version does a merge publish, and does the config need a bump?"""

    def test_published_version_means_publish_the_next_and_bump(self):
        published = {"0.1.4"}
        self.assertEqual(release.plan("0.1.4", published.__contains__), ("0.1.5", True))

    def test_hand_bumped_unpublished_version_is_published_as_is(self):
        # What an agent does today: bump config.yaml and merge. No second bump.
        self.assertEqual(release.plan("0.1.5", lambda v: False), ("0.1.5", False))

    def test_skips_versions_whose_image_already_exists(self):
        # A tag is never overwritten: 0.1.5 exists (a bump that never landed).
        published = {"0.1.4", "0.1.5"}
        self.assertEqual(release.plan("0.1.4", published.__contains__), ("0.1.6", True))

    def test_gives_up_rather_than_loop_forever(self):
        with self.assertRaises(release.PipelineError):
            release.plan("0.1.0", lambda v: True)


class Changelog(unittest.TestCase):
    def test_finds_an_entry_and_its_body(self):
        self.assertEqual(release.changelog_entry(CHANGELOG, "0.1.3"), "- Third.\n- Third again.")

    def test_a_missing_entry_is_none(self):
        self.assertIsNone(release.changelog_entry(CHANGELOG, "0.1.9"))

    def test_version_is_matched_whole(self):
        # 0.1 must not match 0.1.0's heading, nor 0.1.4 match 0.1.40.
        self.assertIsNone(release.changelog_entry(CHANGELOG, "0.1.40"))

    def test_add_entry_goes_first_under_the_title(self):
        out = release.add_changelog_entry(CHANGELOG, "0.1.5", ["Add a thing", "Fix a thing"])
        self.assertTrue(out.startswith("# Changelog\n\n## 0.1.5\n\n- Add a thing\n- Fix a thing\n\n## 0.1.4\n"))

    def test_add_entry_refuses_a_duplicate(self):
        with self.assertRaises(release.PipelineError):
            release.add_changelog_entry(CHANGELOG, "0.1.4", ["again"])

    def test_add_entry_with_no_notes_still_explains(self):
        out = release.add_changelog_entry(CHANGELOG, "0.1.5", [])
        self.assertIn("## 0.1.5\n\n- Rebuilt", out)

    def test_add_entry_to_an_empty_file_makes_the_title(self):
        out = release.add_changelog_entry("", "0.1.0", ["First"])
        self.assertEqual(out, "# Changelog\n\n## 0.1.0\n\n- First\n")

    def test_entries_between_is_exclusive_low_inclusive_high_newest_first(self):
        got = release.entries_between(CHANGELOG, "0.1.2", "0.1.4")
        self.assertEqual([v for v, _ in got], ["0.1.4", "0.1.3"])

    def test_entries_between_with_no_low_bound_takes_everything_up_to_high(self):
        got = release.entries_between(CHANGELOG, None, "0.1.3")
        self.assertEqual([v for v, _ in got], ["0.1.3", "0.1.2", "0.1.0"])


class Promotion(unittest.TestCase):
    def test_stable_config_is_the_edge_config_renamed(self):
        out = release.stable_config(EDGE_CONFIG, "0.1.3")
        self.assertIn("name: Housemate\n", out)
        self.assertIn("slug: housemate\n", out)
        self.assertIn("image: ghcr.io/jceccato/{arch}-housemate\n", out)
        self.assertEqual(release.read_version(out), "0.1.3")
        self.assertIn("provider: go", out)
        self.assertNotIn("edge", out.split("# comment")[0])

    def test_stable_config_fails_if_the_edge_config_has_a_shape_it_does_not_know(self):
        with self.assertRaises(release.PipelineError):
            release.stable_config(EDGE_CONFIG.replace("slug: housemate_edge", "slug: other"), "0.1.3")

    def test_promotion_notes_gather_every_edge_entry_since_stable(self):
        notes = release.promotion_notes(CHANGELOG, "0.1.2", "0.1.4")
        self.assertEqual(notes, "- Fourth.\n- Third.\n- Third again.")

    def test_promotion_notes_dedupe_repeated_lines(self):
        text = "# Changelog\n\n## 0.1.2\n\n- Same.\n\n## 0.1.1\n\n- Same.\n- Other.\n"
        self.assertEqual(release.promotion_notes(text, None, "0.1.2"), "- Same.\n- Other.")

    def test_no_edge_entry_for_the_version_fails_closed(self):
        with self.assertRaises(release.PipelineError) as cm:
            release.promotion_notes(CHANGELOG, "0.1.2", "0.1.9")
        self.assertIn("0.1.9", str(cm.exception))

    def test_an_empty_edge_entry_fails_closed(self):
        with self.assertRaises(release.PipelineError):
            release.promotion_notes("# Changelog\n\n## 0.1.9\n\n## 0.1.2\n\n- x\n", "0.1.2", "0.1.9")

    def test_cannot_promote_a_version_not_newer_than_stable(self):
        with self.assertRaises(release.PipelineError):
            release.check_promotable("0.1.3", "0.1.3", lambda v: True)
        with self.assertRaises(release.PipelineError):
            release.check_promotable("0.1.2", "0.1.3", lambda v: True)

    def test_cannot_promote_a_build_edge_has_no_image_for(self):
        with self.assertRaises(release.PipelineError):
            release.check_promotable("0.1.4", None, lambda v: False)

    def test_first_promotion_has_no_stable_version(self):
        release.check_promotable("0.1.4", None, lambda v: True)

    def test_stable_changelog_gets_the_gathered_entry(self):
        out = release.add_changelog_entry("# Changelog\n", "0.1.4", ["- x"], raw=True)
        self.assertEqual(out, "# Changelog\n\n## 0.1.4\n\n- x\n")


class Docs(unittest.TestCase):
    EDGE = (
        "# Housemate (edge)\n\n<!-- edge-only -->\nThe newest build, for testers.\n<!-- /edge-only -->\n\n"
        "## What it gives you\n\nA panel.\n"
    )

    def test_stable_docs_drop_edge_only_blocks_and_the_edge_title(self):
        self.assertEqual(release.stable_docs(self.EDGE), "# Housemate\n\n## What it gives you\n\nA panel.\n")

    def test_unpaired_marker_fails(self):
        with self.assertRaises(release.PipelineError):
            release.stable_docs("# x\n<!-- edge-only -->\ntext\n")

    def test_docs_without_markers_only_lose_the_edge_title(self):
        self.assertEqual(release.stable_docs("# Housemate (edge)\n\ntext\n"), "# Housemate\n\ntext\n")


class Registry(unittest.TestCase):
    def test_published_needs_every_architecture(self):
        have = {("amd64", "0.1.4")}
        exists = lambda arch, name, v: (arch, v) in have  # noqa: E731
        self.assertFalse(release.published("housemate-edge", "0.1.4", exists))
        have.add(("aarch64", "0.1.4"))
        self.assertTrue(release.published("housemate-edge", "0.1.4", exists))

    def test_a_half_pushed_version_is_spent_for_planning(self):
        exists = lambda arch, name, v: arch == "amd64"  # noqa: E731
        self.assertFalse(release.published("housemate-edge", "0.1.4", exists))
        self.assertTrue(release.published("housemate-edge", "0.1.4", exists, any_arch=True))

    def test_status_404_is_absent_200_is_present_anything_else_is_an_error(self):
        self.assertTrue(release.interpret_manifest_status(200))
        self.assertFalse(release.interpret_manifest_status(404))
        for code in (401, 403, 429, 500, 502):
            with self.assertRaises(release.PipelineError, msg=code):
                release.interpret_manifest_status(code)


class BumpCommand(unittest.TestCase):
    """cmd_bump against a real git history in a temporary directory."""

    def git(self, *args):
        import subprocess

        return subprocess.run(
            ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *args],
            cwd=self.dir, check=True, capture_output=True, text=True,
        ).stdout

    def setUp(self):
        import tempfile

        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = pathlib.Path(self._tmp.name)
        self.git("init", "-q", "-b", "main")
        (self.dir / "edge").mkdir()
        (self.dir / "edge" / "config.yaml").write_text(EDGE_CONFIG)
        (self.dir / "edge" / "CHANGELOG.md").write_text(CHANGELOG)
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "Initial")
        self.git("tag", "edge-0.1.4")
        for name, subject in (("a", "Add the thing"), ("b", "Fix the other thing")):
            (self.dir / "edge" / name).write_text(name)
            self.git("add", "-A")
            self.git("commit", "-q", "-m", subject)
        (self.dir / "unrelated").write_text("x")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "Touch something outside the add-on")

    def run_bump(self, *extra):
        import contextlib
        import io
        import os

        cwd = os.getcwd()
        os.chdir(self.dir)
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                release.main(["bump", "--config", "edge/config.yaml", "--changelog", "edge/CHANGELOG.md",
                              "--path", "edge", "--version", "0.1.5", "--since", "edge-0.1.4", "--until", "HEAD", *extra])
        finally:
            os.chdir(cwd)

    def test_bump_writes_version_and_the_subjects_since_the_last_build(self):
        self.run_bump()
        config = (self.dir / "edge" / "config.yaml").read_text()
        self.assertEqual(release.read_version(config), "0.1.5")
        entry = release.changelog_entry((self.dir / "edge" / "CHANGELOG.md").read_text(), "0.1.5")
        self.assertEqual(entry, "- Fix the other thing\n- Add the thing")

    def test_bump_never_goes_backwards(self):
        cfg = self.dir / "edge" / "config.yaml"
        cfg.write_text(release.set_version(cfg.read_text(), "0.1.9"))
        self.run_bump()
        self.assertEqual(release.read_version(cfg.read_text()), "0.1.9")
        self.assertIsNone(release.changelog_entry((self.dir / "edge" / "CHANGELOG.md").read_text(), "0.1.5"))


if __name__ == "__main__":
    unittest.main()

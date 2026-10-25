"""Incoming: the three-way staging of kit changes, one fixture kit per case.

These run the real scripts on the host (bash, jq, sha256sum) against throwaway
kits and /config directories, so the logic is proved without a container. The
container-level proof is in tests/seam_a/test_kit.py.

A fixture is: the kit the user was seeded with (version 1), the user's /config
after the user's own edits, and the kit a newer image carries (version 2).
"""

import hashlib
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

SHARE = Path(__file__).resolve().parents[2] / "housemate_edge" / "rootfs" / "usr" / "share" / "housemate"
BIN = Path(__file__).resolve().parents[2] / "housemate_edge" / "rootfs" / "usr" / "local" / "bin"
SEED = SHARE / "seed-kit"
INCOMING = BIN / "housemate-incoming"

CHANGELOG = """# Kit changelog

## Kit version 3
Third.

## Kit version 2
- The cheat sheet gained a section.

## Kit version 1
First kit.
"""


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


class Fixture:
    """A /config seeded from `old_kit`, then edited by the user, then a newer image."""

    def __init__(self, test, old_kit, new_kit, user_edits=None, new_version="2", changelog=CHANGELOG):
        self.tmp = Path(tempfile.mkdtemp(prefix="housemate-kit-"))
        test.addCleanup(subprocess.run, ["rm", "-rf", str(self.tmp)])
        self.config = self.tmp / "config"
        self.config.mkdir()
        self.old_kit = self.tmp / "kit-old"
        self.new_kit = self.tmp / "kit-new"
        self.write_kit(self.old_kit, old_kit)
        self.write_kit(self.new_kit, new_kit)
        (self.tmp / "version-old").write_text("1\n")
        (self.tmp / "version-new").write_text(new_version + "\n")
        (self.tmp / "changelog").write_text(changelog)
        self.run_seed(self.old_kit, "version-old")  # first start
        for rel, text in (user_edits or {}).items():
            path = self.config / rel
            if text is None:
                path.unlink()
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text)

    @staticmethod
    def write_kit(root, files):
        for rel, text in files.items():
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)

    def env(self, kit, version):
        return {
            **os.environ,
            "HOUSEMATE_INCOMING": str(INCOMING),
            "HOUSEMATE_CONFIG_DIR": str(self.config),
            "HOUSEMATE_KIT_DIR": str(kit),
            "HOUSEMATE_KIT_VERSION_FILE": str(self.tmp / version),
            "HOUSEMATE_KIT_CHANGELOG": str(self.tmp / "changelog"),
        }

    def run_seed(self, kit, version):
        return subprocess.run([str(SEED)], env=self.env(kit, version), capture_output=True, text=True, check=True)

    def start_new_image(self):
        return self.run_seed(self.new_kit, "version-new")

    def incoming(self, *args, check=True):
        return subprocess.run([str(INCOMING), *args], env=self.env(self.new_kit, "version-new"),
                              capture_output=True, text=True, check=check)

    @property
    def staged(self):
        return self.config / ".housemate" / "incoming"

    def entry(self, rel):
        manifest = json.loads((self.staged / "manifest.json").read_text())
        return manifest["files"].get(rel)

    def manifest(self):
        return json.loads((self.staged / "manifest.json").read_text())

    def snapshot(self):
        """Everything in /config outside .housemate: path, bytes, mode, mtime."""
        out = {}
        for p in sorted(self.config.rglob("*")):
            if ".housemate" in p.relative_to(self.config).parts or not p.is_file():
                continue
            st = p.stat()
            out[p.relative_to(self.config).as_posix()] = (p.read_bytes(), st.st_mode, st.st_mtime_ns)
        return out


OLD = {"AGENTS.md": "rules v1\n", "docs/sheet.md": "sheet v1\n", "scripts/a.sh": "a v1\n"}


class StagingCases(unittest.TestCase):
    """One fixture kit per case of the three-way logic."""

    def test_user_unchanged_and_kit_changed_is_staged_for_the_batch(self):
        f = Fixture(self, OLD, {**OLD, "docs/sheet.md": "sheet v2\n"})
        f.start_new_image()
        e = f.entry("docs/sheet.md")
        self.assertEqual((e["change"], e["user"], e["outcome"]), ("changed", "untouched", "apply"))
        self.assertEqual((f.staged / "new/docs/sheet.md").read_text(), "sheet v2\n")
        self.assertEqual((f.staged / "base/docs/sheet.md").read_text(), "sheet v1\n")
        self.assertEqual((f.config / "docs/sheet.md").read_text(), "sheet v1\n")

    def test_user_changed_and_kit_unchanged_is_not_staged(self):
        f = Fixture(self, OLD, {**OLD, "docs/sheet.md": "sheet v2\n"}, {"AGENTS.md": "my rules\n"})
        f.start_new_image()
        self.assertIsNone(f.entry("AGENTS.md"))
        self.assertEqual((f.config / "AGENTS.md").read_text(), "my rules\n")

    def test_both_changed_needs_a_merge_and_carries_all_three_texts(self):
        f = Fixture(self, OLD, {**OLD, "AGENTS.md": "rules v2\n"}, {"AGENTS.md": "my rules\n"})
        f.start_new_image()
        e = f.entry("AGENTS.md")
        self.assertEqual((e["change"], e["user"], e["outcome"]), ("changed", "modified", "merge"))
        self.assertEqual((f.staged / "new/AGENTS.md").read_text(), "rules v2\n")
        self.assertEqual((f.staged / "base/AGENTS.md").read_text(), "rules v1\n")
        self.assertEqual((f.config / "AGENTS.md").read_text(), "my rules\n")

    def test_a_file_the_kit_added_is_staged_if_the_user_has_nothing_there(self):
        f = Fixture(self, OLD, {**OLD, "docs/new.md": "new\n"})
        f.start_new_image()
        e = f.entry("docs/new.md")
        self.assertEqual((e["change"], e["user"], e["outcome"]), ("added", "missing", "apply"))
        self.assertEqual((f.staged / "new/docs/new.md").read_text(), "new\n")
        self.assertFalse((f.config / "docs/new.md").exists())

    def test_a_file_the_kit_added_where_the_user_has_their_own_is_a_conflict(self):
        f = Fixture(self, OLD, {**OLD, "docs/new.md": "new\n"}, {"docs/new.md": "mine\n"})
        f.start_new_image()
        self.assertEqual(f.entry("docs/new.md")["outcome"], "conflict")
        self.assertEqual((f.config / "docs/new.md").read_text(), "mine\n")

    def test_a_file_the_kit_removed_and_the_user_never_changed_is_staged_for_the_batch(self):
        new = {k: v for k, v in OLD.items() if k != "scripts/a.sh"}
        f = Fixture(self, OLD, new)
        f.start_new_image()
        e = f.entry("scripts/a.sh")
        self.assertEqual((e["change"], e["user"], e["outcome"]), ("removed", "untouched", "apply"))
        self.assertEqual((f.staged / "base/scripts/a.sh").read_text(), "a v1\n")
        self.assertTrue((f.config / "scripts/a.sh").exists())

    def test_a_file_the_kit_removed_and_the_user_changed_is_for_review(self):
        new = {k: v for k, v in OLD.items() if k != "scripts/a.sh"}
        f = Fixture(self, OLD, new, {"scripts/a.sh": "my a\n"})
        f.start_new_image()
        self.assertEqual(f.entry("scripts/a.sh")["outcome"], "review")
        self.assertEqual((f.config / "scripts/a.sh").read_text(), "my a\n")

    def test_a_file_the_user_deleted_is_not_brought_back_but_is_asked_about(self):
        f = Fixture(self, OLD, {**OLD, "docs/sheet.md": "sheet v2\n"}, {"docs/sheet.md": None})
        f.start_new_image()
        e = f.entry("docs/sheet.md")
        self.assertEqual((e["change"], e["user"], e["outcome"]), ("changed", "missing", "user_deleted"))
        self.assertFalse((f.config / "docs/sheet.md").exists())

    def test_a_file_the_user_deleted_and_the_kit_did_not_change_is_left_alone(self):
        f = Fixture(self, OLD, {**OLD, "docs/other.md": "x\n"}, {"AGENTS.md": None})
        f.start_new_image()
        self.assertIsNone(f.entry("AGENTS.md"))
        self.assertFalse((f.config / "AGENTS.md").exists())

    def test_a_user_who_already_made_the_kits_change_has_nothing_to_review(self):
        f = Fixture(self, OLD, {**OLD, "docs/sheet.md": "sheet v2\n"}, {"docs/sheet.md": "sheet v2\n"})
        f.start_new_image()
        self.assertEqual(f.entry("docs/sheet.md")["outcome"], "converged")

    def test_a_file_the_user_already_had_at_first_start_is_compared_against_the_shipped_text(self):
        # Seeded as skipped: the user's file differed from the kit's.
        tmp_user = {"AGENTS.md": "mine from before\n"}
        f = Fixture(self, OLD, {**OLD, "AGENTS.md": "rules v2\n"})
        # Rebuild the first start with the user's own file already present.
        subprocess.run(["rm", "-rf", str(f.config / ".housemate")])
        (f.config / "AGENTS.md").write_text(tmp_user["AGENTS.md"])
        f.run_seed(f.old_kit, "version-old")
        manifest = json.loads((f.config / ".housemate/kit-manifest.json").read_text())
        self.assertIn("AGENTS.md", manifest["skipped_existing"])
        f.start_new_image()
        e = f.entry("AGENTS.md")
        self.assertEqual((e["user"], e["outcome"]), ("modified", "merge"))
        self.assertEqual((f.staged / "base/AGENTS.md").read_text(), "rules v1\n")


class SeamLevel(unittest.TestCase):
    """What a start does and does not do (the logic behind Seam A)."""

    def test_the_users_files_are_byte_identical_after_a_start_that_stages(self):
        f = Fixture(self, OLD, {**OLD, "AGENTS.md": "rules v2\n", "docs/sheet.md": "sheet v2\n", "docs/new.md": "n\n"},
                    {"AGENTS.md": "my rules\n", "docs/sheet.md": None, "extra.yaml": "x: 1\n"})
        before = f.snapshot()
        f.start_new_image()
        self.assertEqual(f.snapshot(), before)
        self.assertTrue(f.staged.is_dir())

    def test_the_same_kit_stages_nothing(self):
        f = Fixture(self, OLD, OLD)
        f.run_seed(f.old_kit, "version-old")
        self.assertFalse(f.staged.exists())

    def test_an_older_kit_than_the_manifest_stages_nothing(self):
        f = Fixture(self, OLD, {**OLD, "docs/sheet.md": "x\n"}, new_version="0")
        f.start_new_image()
        self.assertFalse(f.staged.exists())

    def test_a_kit_with_a_new_version_and_no_file_change_stages_an_empty_review(self):
        f = Fixture(self, OLD, OLD)
        f.start_new_image()
        self.assertEqual(f.manifest()["files"], {})
        self.assertEqual(f.manifest()["kit_version"], "2")

    def test_the_manifest_still_names_the_old_kit_until_the_review_is_finished(self):
        f = Fixture(self, OLD, {**OLD, "docs/sheet.md": "sheet v2\n"})
        before = (f.config / ".housemate/kit-manifest.json").read_text()
        f.start_new_image()
        self.assertEqual((f.config / ".housemate/kit-manifest.json").read_text(), before)
        self.assertEqual((f.config / ".housemate/base/docs/sheet.md").read_text(), "sheet v1\n")

    def test_staging_is_repeated_on_every_start_and_follows_what_the_user_did_since(self):
        f = Fixture(self, OLD, {**OLD, "docs/sheet.md": "sheet v2\n"})
        f.start_new_image()
        self.assertEqual(f.entry("docs/sheet.md")["outcome"], "apply")
        (f.config / "docs/sheet.md").write_text("edited meanwhile\n")
        f.start_new_image()
        self.assertEqual(f.entry("docs/sheet.md")["outcome"], "merge")

    def test_a_marker_for_the_update_notification(self):
        f = Fixture(self, OLD, {**OLD, "docs/sheet.md": "sheet v2\n", "docs/n.md": "n\n"}, {"docs/sheet.md": "mine\n"})
        f.start_new_image()
        m = f.manifest()
        self.assertEqual((m["from_kit_version"], m["kit_version"]), ("1", "2"))
        self.assertEqual(m["counts"], {"apply": 1, "merge": 1})
        status = json.loads(f.incoming("status", "--json").stdout)
        self.assertEqual(status["pending"], True)
        self.assertEqual(status["counts"], {"apply": 1, "merge": 1})

    def test_status_with_nothing_incoming(self):
        f = Fixture(self, OLD, OLD)
        status = json.loads(f.incoming("status", "--json").stdout)
        self.assertEqual(status["pending"], False)


class Safety(unittest.TestCase):
    def test_a_missing_kit_directory_stages_nothing_rather_than_staging_every_file_as_removed(self):
        f = Fixture(self, OLD, OLD)
        subprocess.run(["rm", "-rf", str(f.new_kit)], check=True)
        r = subprocess.run([str(INCOMING), "stage"], env=f.env(f.new_kit, "version-new"), capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertFalse(f.staged.exists())

    def test_apply_ignores_a_staged_path_that_leaves_config(self):
        f = Fixture(self, OLD, {**OLD, "docs/sheet.md": "v2\n"})
        f.start_new_image()
        outside = f.tmp / "outside.txt"
        outside.write_text("keep\n")
        m = f.manifest()
        m["files"]["../outside.txt"] = {"change": "removed", "user": "untouched", "outcome": "apply",
                                        "base_sha256": "", "new_sha256": "", "user_sha256": sha("keep\n")}
        (f.staged / "manifest.json").write_text(json.dumps(m))
        f.incoming("apply-untouched")
        self.assertTrue(outside.exists())


class ReleaseNotes(unittest.TestCase):
    def test_release_notes_travel_with_incoming_for_every_version_skipped_over(self):
        f = Fixture(self, OLD, {**OLD, "docs/sheet.md": "v3\n"}, new_version="3")
        f.start_new_image()
        notes = (f.staged / "RELEASE-NOTES.md").read_text()
        self.assertIn("Kit version 3", notes)
        self.assertIn("cheat sheet gained a section", notes)
        self.assertNotIn("First kit", notes)

    def test_a_missing_changelog_entry_is_said_so(self):
        f = Fixture(self, OLD, {**OLD, "docs/sheet.md": "v3\n"}, new_version="9",
                    changelog="# Kit changelog\n\n## Kit version 1\nFirst kit.\n")
        f.start_new_image()
        self.assertIn("No release notes", (f.staged / "RELEASE-NOTES.md").read_text())

    def test_the_real_kit_has_notes_for_its_own_version(self):
        version = (SHARE / "kit-version").read_text().strip()
        self.assertIn(f"## Kit version {version}", (SHARE / "kit-changelog.md").read_text())


class Applying(unittest.TestCase):
    def setUp(self):
        self.f = Fixture(self, {**OLD, "gone.md": "g\n"},
                         {"AGENTS.md": "rules v2\n", "docs/sheet.md": "sheet v2\n", "scripts/a.sh": "a v1\n",
                          "docs/new.md": "new\n", "docs/clash.md": "kit clash\n"},
                         {"AGENTS.md": "my rules\n", "docs/clash.md": "my clash\n"})
        self.f.start_new_image()

    def test_the_batch_applies_untouched_files_only(self):
        f = self.f
        out = f.incoming("apply-untouched").stdout
        self.assertEqual((f.config / "docs/sheet.md").read_text(), "sheet v2\n")
        self.assertEqual((f.config / "docs/new.md").read_text(), "new\n")
        self.assertFalse((f.config / "gone.md").exists())
        self.assertEqual((f.config / "AGENTS.md").read_text(), "my rules\n")
        self.assertEqual((f.config / "docs/clash.md").read_text(), "my clash\n")
        self.assertIn("docs/sheet.md", out)
        self.assertNotIn("AGENTS.md", out)

    def test_the_batch_skips_a_file_the_user_changed_since_staging(self):
        f = self.f
        (f.config / "docs/sheet.md").write_text("late edit\n")
        out = f.incoming("apply-untouched").stdout
        self.assertEqual((f.config / "docs/sheet.md").read_text(), "late edit\n")
        self.assertIn("skipped", out)

    def test_finish_refuses_while_the_batch_is_unapplied(self):
        r = self.f.incoming("finish", check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertTrue(self.f.staged.exists())

    def test_finish_moves_the_base_and_manifest_to_the_new_kit_and_clears_incoming(self):
        f = self.f
        f.incoming("apply-untouched")
        f.incoming("finish")
        self.assertFalse(f.staged.exists())
        m = json.loads((f.config / ".housemate/kit-manifest.json").read_text())
        self.assertEqual(m["kit_version"], "2")
        self.assertEqual(m["files"]["AGENTS.md"], sha("rules v2\n"))
        self.assertEqual((f.config / ".housemate/base/AGENTS.md").read_text(), "rules v2\n")
        self.assertFalse((f.config / ".housemate/base/gone.md").exists())
        self.assertNotIn("gone.md", m["files"])
        # The user's own AGENTS.md is untouched by finishing.
        self.assertEqual((f.config / "AGENTS.md").read_text(), "my rules\n")
        # And the next start with the same kit stages nothing.
        f.start_new_image()
        self.assertFalse(f.staged.exists())

    def test_after_finishing_a_later_kit_is_compared_against_the_new_base(self):
        f = self.f
        f.incoming("apply-untouched")
        f.incoming("finish")
        f.write_kit(f.new_kit, {"docs/sheet.md": "sheet v3\n"})
        (f.tmp / "version-new").write_text("3\n")
        f.start_new_image()
        self.assertEqual(f.entry("docs/sheet.md")["outcome"], "apply")
        self.assertEqual((f.staged / "base/docs/sheet.md").read_text(), "sheet v2\n")


class DeletedState(unittest.TestCase):
    """Decision: deleting .housemate/ re-seeds on the next start, and never overwrites."""

    def test_a_deleted_state_folder_reseeds_without_touching_any_existing_file(self):
        f = Fixture(self, OLD, OLD, {"AGENTS.md": "mine\n", "docs/sheet.md": None})
        subprocess.run(["rm", "-rf", str(f.config / ".housemate")], check=True)
        f.run_seed(f.old_kit, "version-old")
        self.assertEqual((f.config / "AGENTS.md").read_text(), "mine\n")
        self.assertEqual((f.config / "docs/sheet.md").read_text(), "sheet v1\n")  # the deleted file returns
        m = json.loads((f.config / ".housemate/kit-manifest.json").read_text())
        self.assertIn("AGENTS.md", m["skipped_existing"])
        self.assertEqual((f.config / ".housemate/base/AGENTS.md").read_text(), "rules v1\n")


if __name__ == "__main__":
    unittest.main()

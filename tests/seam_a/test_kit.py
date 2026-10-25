"""Seam A: the starter kit seeded into /config, and /config under git.

Same rules as test_seam_a.py: only what a user could see from outside the
container. The kit under test is the one in the image, compared with the copy
in this repository.
"""

import hashlib
import json
import unittest
from pathlib import Path

import harness
from harness import ADDON_DIR, AddOn, docker
from test_mutants import build_mutant

SHARE = ADDON_DIR / "rootfs" / "usr" / "share" / "housemate"
KIT = SHARE / "kit"
KIT_FILES = sorted(p.relative_to(KIT).as_posix() for p in KIT.rglob("*") if p.is_file())
OPTIONS = {"provider": "zen", "api_key": ""}
MANIFEST = ".housemate/kit-manifest.json"

# What a real /config holds that must stay out of git, and what must go in.
UNTRACKED = [
    "secrets.yaml",
    "home-assistant_v2.db",
    "home-assistant_v2.db-wal",
    "home-assistant.log",
    "home-assistant.log.1",
    "backups/full.tar",
    "media/clip.mp4",
    "tts/hello.mp3",
    ".storage/auth",
    ".storage/auth_provider.homeassistant",
    ".storage/core.config_entries",
    ".storage/core.restore_state",
    ".storage/onboarding",
    ".storage/person",
    ".storage/cloud",
    ".cloud/cloud.json",
    ".uuid",
    MANIFEST,
]
TRACKED = [
    "configuration.yaml",
    "automations.yaml",
    "packages/lights.yaml",
    ".storage/lovelace",
    ".storage/lovelace.dashboard_house",
    ".storage/lovelace_dashboards",
    ".storage/lovelace_resources",
    ".storage/input_boolean",
    ".storage/input_number",
    ".storage/input_select",
    ".storage/input_text",
    ".storage/input_datetime",
    ".storage/input_button",
    ".storage/counter",
    ".storage/timer",
    ".storage/schedule",
    "AGENTS.md",
    "docs/cheat-sheet.md",
    "scripts/git-init.sh",
]
SECRET_VALUE = "wifi_password: not-a-real-secret"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def snapshot(addon):
    """Every file under /config: path, content hash, mtime. Git's own are left out."""
    out = addon.exec(
        r"cd /config && find . -path ./.git -prune -o -type f -printf '%p %T@ ' -exec sha256sum {} \; | sort"
    ).stdout
    return out


def populate_house(addon):
    """Files a running Home Assistant would have made, secret and not."""
    files = {name: f"content of {name}\n" for name in UNTRACKED + TRACKED if name not in KIT_FILES and name != MANIFEST}
    files["secrets.yaml"] = SECRET_VALUE + "\n"
    for name, text in files.items():
        path = addon.config / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)


class FirstStart(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.addon = AddOn(OPTIONS, {"configuration.yaml": "homeassistant:\n  name: Fixture\n"})
        cls.addon.start()
        cls.manifest = json.loads(cls.addon.exec(f"cat /config/{MANIFEST}").stdout)

    @classmethod
    def tearDownClass(cls):
        cls.addon.stop()

    def test_the_kit_has_the_agreed_parts(self):
        for part in ("AGENTS.md", "docs/cheat-sheet.md", "memory/MEMORY.md", "scripts/git-init.sh", "tracker/README.md"):
            self.assertIn(part, KIT_FILES)
        how_tos = [f for f in KIT_FILES if f.startswith("docs/how-to/")]
        self.assertGreaterEqual(len(how_tos), 4)

    def test_every_kit_file_is_seeded_unchanged(self):
        for rel in KIT_FILES:
            r = self.addon.exec(f"sha256sum /config/{rel}", check=False)
            self.assertEqual(r.returncode, 0, f"{rel} was not seeded")
            self.assertEqual(r.stdout.split()[0], sha(KIT / rel), rel)

    def test_the_scripts_are_executable(self):
        self.assertEqual(self.addon.exec("stat -c %a /config/scripts/git-init.sh").stdout.strip(), "755")

    def test_the_manifest_records_the_kit_version_and_a_hash_per_file(self):
        self.assertEqual(self.manifest["kit_version"], (SHARE / "kit-version").read_text().strip())
        self.assertEqual(self.manifest["files"], {rel: sha(KIT / rel) for rel in KIT_FILES})
        self.assertEqual(self.manifest["skipped_existing"], [])

    def test_the_shipped_text_is_kept_as_the_base_for_a_later_compare(self):
        for rel in KIT_FILES:
            r = self.addon.exec(f"sha256sum /config/.housemate/base/{rel}")
            self.assertEqual(r.stdout.split()[0], self.manifest["files"][rel], rel)

    def test_what_the_user_already_had_is_untouched(self):
        self.assertEqual(self.addon.exec("cat /config/configuration.yaml").stdout, "homeassistant:\n  name: Fixture\n")
        self.assertNotIn("configuration.yaml", self.manifest["files"])


class SecondStart(unittest.TestCase):
    """The kit is seeded once: a restart, a user's edit or a newer kit change nothing."""

    @classmethod
    def setUpClass(cls):
        cls.addon = AddOn(OPTIONS, {"configuration.yaml": "homeassistant:\n"})
        cls.addon.start()

    @classmethod
    def tearDownClass(cls):
        cls.addon.stop()

    def test_a_second_start_with_the_same_kit_changes_nothing(self):
        a = self.addon
        before = snapshot(a)
        a.restart()
        self.assertEqual(snapshot(a), before)

    def test_user_edits_and_deletions_stay_and_a_newer_kit_is_not_written(self):
        a = self.addon
        manifest_before = a.exec(f"cat /config/{MANIFEST}").stdout
        a.exec("echo 'my own rules' > /config/AGENTS.md; rm /config/docs/how-to/read-history.md")
        # The image now carries a different kit (as a newer release would).
        a.exec("echo 'a better rule' >> /usr/share/housemate/kit/docs/cheat-sheet.md; "
               "echo 2 > /usr/share/housemate/kit-version; "
               "echo 'new file' > /usr/share/housemate/kit/docs/new.md")
        before = snapshot(a)
        a.exec("/usr/share/housemate/seed-kit")
        self.assertEqual(snapshot(a), before)
        self.assertEqual(a.exec(f"cat /config/{MANIFEST}").stdout, manifest_before)
        self.assertFalse(a.exec("test -e /config/docs/new.md", check=False).returncode == 0)
        self.assertFalse(a.exec("test -e /config/docs/how-to/read-history.md", check=False).returncode == 0)
        self.assertEqual(a.exec("cat /config/AGENTS.md").stdout, "my own rules\n")


class ExistingFilesAreNeverOverwritten(unittest.TestCase):
    def test_a_users_own_agents_md_survives_the_first_start(self):
        addon = AddOn(OPTIONS, {"AGENTS.md": "# mine\n", "docs/cheat-sheet.md": "my sheet\n"})
        try:
            addon.start()
            self.assertEqual((addon.config / "AGENTS.md").read_text(), "# mine\n")
            self.assertEqual((addon.config / "docs/cheat-sheet.md").read_text(), "my sheet\n")
            manifest = json.loads(addon.exec(f"cat /config/{MANIFEST}").stdout)
            self.assertEqual(sorted(manifest["skipped_existing"]), ["AGENTS.md", "docs/cheat-sheet.md"])
            self.assertNotIn("AGENTS.md", manifest["files"])
            self.assertIn("memory/MEMORY.md", manifest["files"])
        finally:
            addon.stop()


class GitInConfig(unittest.TestCase):
    """The kit's git-init script, as onboarding will call it."""

    @classmethod
    def setUpClass(cls):
        cls.addon = AddOn(OPTIONS, {"configuration.yaml": "homeassistant:\n"})
        populate_house(cls.addon)
        cls.addon.start()
        cls.run_git_init(cls.addon)

    @classmethod
    def run_git_init(cls, addon):
        # Home Assistant's /config belongs to root, as in the real add-on.
        addon.exec("chown -R root:root /config")
        addon.exec("/config/scripts/git-init.sh")

    @classmethod
    def tearDownClass(cls):
        cls.addon.stop()

    def tracked(self):
        return set(self.addon.exec("cd /config && git ls-files").stdout.split("\n"))

    def test_secrets_databases_and_credentials_are_untracked(self):
        tracked = self.tracked()
        for name in UNTRACKED:
            self.assertNotIn(name, tracked, name)
            self.assertEqual(self.addon.exec(f"cd /config && git check-ignore -q {name}", check=False).returncode, 0, name)

    def test_dashboards_helpers_and_configuration_are_tracked(self):
        tracked = self.tracked()
        for name in TRACKED:
            self.assertIn(name, tracked, name)

    def test_no_secret_value_is_anywhere_in_the_repository(self):
        found = self.addon.exec(
            f"cd /config && git grep -l -F '{SECRET_VALUE}' $(git rev-list --all) ; git log --all -p | grep -c -F '{SECRET_VALUE}'; true"
        ).stdout
        self.assertEqual(found.strip().splitlines()[-1], "0")

    def test_the_history_starts_with_the_configuration_and_the_tree_is_clean(self):
        log = self.addon.exec("cd /config && git log --format=%s").stdout.strip().splitlines()
        self.assertTrue(log[-1].startswith("Start tracking /config"))
        self.assertEqual(self.addon.exec("cd /config && git status --porcelain").stdout, "")

    def test_an_existing_gitignore_and_tracked_secrets_are_dealt_with(self):
        a = AddOn(OPTIONS, {"configuration.yaml": "x: 1\n", ".gitignore": "*.bak\n", "secrets.yaml": SECRET_VALUE + "\n"})
        self.addCleanup(a.stop)
        a.start()
        a.exec("chown -R root:root /config && cd /config && git init -q && git -c user.name=t -c user.email=t@t add secrets.yaml && "
               "git -c user.name=t -c user.email=t@t commit -qm old")
        a.exec("/config/scripts/git-init.sh")
        tracked = a.exec("cd /config && git ls-files").stdout.split("\n")
        self.assertNotIn("secrets.yaml", tracked)
        self.assertIn("configuration.yaml", tracked)
        self.assertIn("*.bak", a.exec("cat /config/.gitignore").stdout)

    def test_running_it_again_changes_nothing(self):
        head = self.addon.exec("cd /config && git rev-parse HEAD && cat .gitignore | sha256sum").stdout
        self.addon.exec("/config/scripts/git-init.sh")
        self.assertEqual(self.addon.exec("cd /config && git rev-parse HEAD && cat .gitignore | sha256sum").stdout, head)

    def test_a_change_is_committed_and_rolled_back(self):
        a = self.addon
        a.exec("cd /config && echo 'good: true' > packages/good.yaml && git add packages/good.yaml && git commit -qm 'Add good, because'")
        a.exec("cd /config && echo 'broken: [' > packages/good.yaml")
        a.exec("cd /config && git checkout -- packages/good.yaml")
        self.assertEqual(a.exec("cat /config/packages/good.yaml").stdout, "good: true\n")


class KitMutants(unittest.TestCase):
    """The kit tests must be able to fail: break the image and watch them notice."""

    def start_mutant(self, name, lines):
        tag = build_mutant(name, lines)
        self.addCleanup(docker, "rmi", "-f", tag, check=False)
        saved = harness.IMAGE
        harness.IMAGE = tag
        self.addCleanup(setattr, harness, "IMAGE", saved)
        addon = AddOn(OPTIONS, {"configuration.yaml": "homeassistant:\n"})
        self.addCleanup(addon.stop)
        return addon

    def test_a_seeder_that_overwrites_is_caught(self):
        addon = self.start_mutant("overwrite", [
            "RUN sed -i 's|^    if \\[\\[ -e \"${target}\" \\]\\]; then|    if false; then|' /usr/share/housemate/seed-kit",
        ])
        (addon.config / "AGENTS.md").write_text("# mine\n")
        addon.start()
        self.assertNotEqual((addon.config / "AGENTS.md").read_text(), "# mine\n")

    def test_a_seeder_that_runs_every_start_is_caught(self):
        addon = self.start_mutant("every", [
            "RUN sed -i 's|^if \\[\\[ -e \"${manifest}\" \\]\\]; then|if false; then|' /usr/share/housemate/seed-kit",
        ])
        addon.start()
        addon.exec("rm /config/docs/how-to/read-history.md")
        addon.restart()
        self.assertTrue(addon.exec("test -e /config/docs/how-to/read-history.md", check=False).returncode == 0)

    def test_an_ignore_policy_without_secrets_is_caught(self):
        addon = self.start_mutant("nosecrets", [
            "RUN sed -i -e '/^secrets.yaml$/d' -e '/^\\.storage\\/\\*$/d' /usr/share/housemate/kit/scripts/git-init.sh",
        ])
        populate_house(addon)
        addon.start()
        GitInConfig.run_git_init(addon)
        tracked = addon.exec("cd /config && git ls-files").stdout.split("\n")
        self.assertIn("secrets.yaml", tracked)
        self.assertIn(".storage/auth", tracked)


if __name__ == "__main__":
    unittest.main()

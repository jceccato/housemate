#!/usr/bin/env python3
"""The decisions of Housemate's publish and promotion workflows.

The workflows are thin: they call this script and act on what it prints. All
the logic lives here so tests/pipeline can run it without a network.

    release.py plan     --config F --changelog F      which version this merge publishes
    release.py bump     --config F --changelog F ...  write the bump (after the image is pushed)
    release.py promote  ...                           write the stable add-on folder

Standard library only: it runs on a bare runner.
"""

import argparse
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request

OWNER = "jceccato"
ARCHES = ("amd64", "aarch64")
MAX_SKIP = 50


class PipelineError(Exception):
    """A fail-closed stop: the message is what the workflow shows."""


# ---- versions --------------------------------------------------------------


def parse(version):
    m = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", version or "")
    if not m:
        raise PipelineError(f"'{version}' is not a plain MAJOR.MINOR.PATCH version")
    return tuple(int(p) for p in m.groups())


def bump_patch(version):
    major, minor, patch = parse(version)
    return f"{major}.{minor}.{patch + 1}"


def read_version(config_text):
    m = re.search(r'^version: *"?([^"\s#]+)"? *$', config_text, re.M)
    if not m:
        raise PipelineError("no top-level 'version:' in config.yaml")
    return m.group(1)


def set_version(config_text, version):
    parse(version)
    out, n = re.subn(r'^version: *"?[^"\s#]+"? *$', f"version: {version}", config_text, count=1, flags=re.M)
    if n != 1:
        raise PipelineError("no top-level 'version:' in config.yaml")
    return out


def plan(version, is_published):
    """Return (version to publish, whether config.yaml needs a bump after).

    A config.yaml version with no image yet is a hand bump: publish it as it
    stands. One that already has an image is spent: publish the next free
    patch version and bump config.yaml to it once the image is pushed.
    """
    if not is_published(version):
        return version, False
    candidate = version
    for _ in range(MAX_SKIP):
        candidate = bump_patch(candidate)
        if not is_published(candidate):
            return candidate, True
    raise PipelineError(f"{MAX_SKIP} versions after {version} all have images; something is wrong")


# ---- changelog -------------------------------------------------------------


def _entries(text):
    """[(version, body)] in file order, from '## <version>' headings."""
    parts = re.split(r"^## +(\S+) *$", text, flags=re.M)
    return [(parts[i], parts[i + 1].strip()) for i in range(1, len(parts) - 1, 2)]


def changelog_entry(text, version):
    for v, body in _entries(text):
        if v == version:
            return body
    return None


def add_changelog_entry(text, version, notes, raw=False):
    if changelog_entry(text, version) is not None:
        raise PipelineError(f"the changelog already has an entry for {version}")
    lines = list(notes) if raw else [f"- {n}" for n in notes]
    body = "\n".join(lines) if lines else "- Rebuilt; no add-on change since the last build."
    entry = f"## {version}\n\n{body}\n\n"
    if not text.strip():
        return f"# Changelog\n\n{entry}".rstrip("\n") + "\n"
    head, sep, rest = text.partition("\n## ")
    if not sep:
        return text.rstrip("\n") + "\n\n" + entry.rstrip("\n") + "\n"
    return head.rstrip("\n") + "\n\n" + entry + "## " + rest


def entries_between(text, low, high):
    """Entries with low < version <= high, newest first. low None = no lower bound."""
    out = []
    for v, body in _entries(text):
        p = parse(v)
        if p <= parse(high) and (low is None or p > parse(low)):
            out.append((v, body))
    return sorted(out, key=lambda e: parse(e[0]), reverse=True)


# ---- registry --------------------------------------------------------------


def interpret_manifest_status(code):
    if code == 200:
        return True
    if code == 404:
        return False
    raise PipelineError(f"the registry answered {code}; cannot tell whether the image exists")


def published(name, version, exists, any_arch=False):
    """True when every architecture's image for this version is in the registry.

    With any_arch, true when at least one is: that version is spent, because a
    tag is never overwritten and a half-pushed version must not be completed
    from a different commit.
    """
    found = (exists(arch, name, version) for arch in ARCHES)
    return any(found) if any_arch else all(found)


def registry_exists(arch, name, version):
    repo = f"{OWNER}/{arch}-{name}"
    token_url = f"https://ghcr.io/token?service=ghcr.io&scope=repository:{repo}:pull"
    try:
        with urllib.request.urlopen(token_url, timeout=30) as r:
            token = json.load(r)["token"]
    except urllib.error.HTTPError as e:
        # ghcr refuses an anonymous pull token for a package that does not
        # exist yet (stable's, before the first promotion). Our packages are
        # public, so a refusal means there is no such package.
        if e.code in (401, 403):
            return False
        raise PipelineError(f"ghcr token request answered {e.code}") from e
    req = urllib.request.Request(
        f"https://ghcr.io/v2/{repo}/manifests/{version}",
        method="HEAD",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": ", ".join(
                [
                    "application/vnd.oci.image.index.v1+json",
                    "application/vnd.oci.image.manifest.v1+json",
                    "application/vnd.docker.distribution.manifest.list.v2+json",
                    "application/vnd.docker.distribution.manifest.v2+json",
                ]
            ),
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return interpret_manifest_status(r.status)
    except urllib.error.HTTPError as e:
        return interpret_manifest_status(e.code)


# ---- promotion -------------------------------------------------------------


def stable_config(edge_text, version):
    """Edge's config.yaml, renamed into stable's, at the promoted version."""
    subs = [
        (r"^name: Housemate \(edge\) *$", "name: Housemate"),
        (r"^slug: housemate_edge *$", "slug: housemate"),
        (r"^image: (\S+)-housemate-edge *$", r"image: \1-housemate"),
    ]
    out = edge_text
    for pattern, repl in subs:
        out, n = re.subn(pattern, repl, out, count=1, flags=re.M)
        if n != 1:
            raise PipelineError(f"edge's config.yaml has no line matching {pattern!r}; teach release.py")
    out = re.sub(r"^description: .*$", "description: An agent in the sidebar that builds Home Assistant with you.", out, count=1, flags=re.M)
    return set_version(out, version)


def stable_docs(edge_docs):
    """Edge's DOCS.md for stable: drop <!-- edge-only --> blocks, rename the title."""
    out = re.sub(r"<!-- edge-only -->.*?<!-- /edge-only -->\n?", "", edge_docs, flags=re.S)
    if "<!-- edge-only -->" in out or "<!-- /edge-only -->" in out:
        raise PipelineError("DOCS.md has an unpaired edge-only marker")
    out = re.sub(r"^# Housemate \(edge\) *$", "# Housemate", out, count=1, flags=re.M)
    return re.sub(r"\n{3,}", "\n\n", out)


def promotion_notes(edge_changelog, stable_version, version):
    """The release notes: every edge entry since stable's version, deduplicated."""
    body = changelog_entry(edge_changelog, version)
    if body is None:
        raise PipelineError(f"edge's CHANGELOG.md has no '## {version}' entry; write it, then promote")
    if not body.strip():
        raise PipelineError(f"edge's CHANGELOG.md entry for {version} is empty; write it, then promote")
    seen, lines = set(), []
    for _, entry in entries_between(edge_changelog, stable_version, version):
        for line in entry.splitlines():
            if line.strip() and line not in seen:
                seen.add(line)
                lines.append(line)
    return "\n".join(lines)


def check_promotable(version, stable_version, edge_image_exists):
    parse(version)
    if stable_version is not None and parse(version) <= parse(stable_version):
        raise PipelineError(f"stable is already at {stable_version}; {version} is not newer")
    if not edge_image_exists(version):
        raise PipelineError(f"edge has no image for {version} on both architectures; promote a build edge has published")


# ---- command line ----------------------------------------------------------


def _out(**kv):
    lines = [f"{k}={v}" for k, v in kv.items()]
    print("\n".join(lines))
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write("\n".join(lines) + "\n")


def _read(path):
    return pathlib.Path(path).read_text()


def _git(*args):
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True).stdout


def cmd_plan(a):
    config = _read(a.config)
    current = read_version(config)
    version, bump = plan(current, lambda v: published(a.name, v, registry_exists, any_arch=True))
    if not bump:
        # A hand bump publishes without the pipeline writing anything, so its
        # changelog entry must already be there: fail closed without one.
        if changelog_entry(_read(a.changelog), version) is None:
            raise PipelineError(f"{a.changelog} has no '## {version}' entry; nothing is published without one")
    _out(version=version, bump=str(bump).lower(), current=current)


def commit_notes(path, since, until):
    """Subjects of the commits touching `path` in since..until (the build's own range).

    `since` is the previous published build's commit (its edge-<version> tag);
    without one, the last ten. Bump commits are left out.
    """
    args = ["log", "--format=%s"]
    args += [f"{since}..{until}"] if since else ["-n", "10", until]
    subjects = _git(*args, "--", path).splitlines()
    return [s for s in subjects if not re.match(r"^Bump edge to ", s)]


def cmd_bump(a):
    parse(a.version)
    cfg_path, log_path = pathlib.Path(a.config), pathlib.Path(a.changelog)
    config, log = cfg_path.read_text(), log_path.read_text()
    current = read_version(config)
    if parse(current) >= parse(a.version):
        # Main moved on (a hand bump landed meanwhile). Never go backwards.
        print(f"config.yaml is already at {current}, not older than {a.version}; nothing to bump")
        _out(bumped="false")
        return
    notes = a.note or commit_notes(a.path, a.since, a.until)
    cfg_path.write_text(set_version(config, a.version))
    if changelog_entry(log, a.version) is None:
        log_path.write_text(add_changelog_entry(log, a.version, notes))
    _out(bumped="true")


def cmd_promote_check(a):
    stable_version = None
    sc = pathlib.Path(a.stable_config)
    if sc.exists():
        stable_version = read_version(sc.read_text())
    check_promotable(a.version, stable_version, lambda v: published("housemate-edge", v, registry_exists))
    if published("housemate", a.version, registry_exists):
        raise PipelineError(f"stable already has an image tagged {a.version}; a tag is never overwritten")
    notes = promotion_notes(_read(a.edge_changelog), stable_version, a.version)
    pathlib.Path(a.notes_out).write_text(notes + "\n")
    _out(stable_version=stable_version or "", notes_file=a.notes_out)


def cmd_promote_write(a):
    """Write housemate/ from a checkout of the edge build (a.source)."""
    src, dst = pathlib.Path(a.source), pathlib.Path(a.stable_dir)
    dst.mkdir(parents=True, exist_ok=True)
    (dst / "config.yaml").write_text(stable_config((src / "config.yaml").read_text(), a.version))
    if (src / "DOCS.md").exists():
        (dst / "DOCS.md").write_text(stable_docs((src / "DOCS.md").read_text()))
    for extra in ("translations", "icon.png", "logo.png"):
        p = src / extra
        if p.is_dir():
            shutil.copytree(p, dst / extra, dirs_exist_ok=True)
        elif p.exists():
            (dst / extra).write_bytes(p.read_bytes())
    log_path = dst / "CHANGELOG.md"
    log = log_path.read_text() if log_path.exists() else ""
    notes = _read(a.notes).strip().splitlines()
    log_path.write_text(add_changelog_entry(log, a.version, notes, raw=True))


def main(argv=None):
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("plan")
    s.add_argument("--config", default="housemate_edge/config.yaml")
    s.add_argument("--changelog", default="housemate_edge/CHANGELOG.md")
    s.add_argument("--name", default="housemate-edge")
    s.set_defaults(fn=cmd_plan)

    s = sub.add_parser("bump")
    s.add_argument("--config", default="housemate_edge/config.yaml")
    s.add_argument("--changelog", default="housemate_edge/CHANGELOG.md")
    s.add_argument("--path", default="housemate_edge")
    s.add_argument("--version", required=True)
    s.add_argument("--since", default="", help="previous published build's commit or tag")
    s.add_argument("--until", default="HEAD", help="the commit that was built")
    s.add_argument("--note", action="append", help="changelog line (repeatable); default: commit subjects since the last bump")
    s.set_defaults(fn=cmd_bump)

    s = sub.add_parser("promote-check")
    s.add_argument("--version", required=True)
    s.add_argument("--stable-config", default="housemate/config.yaml")
    s.add_argument("--edge-changelog", default="housemate_edge/CHANGELOG.md")
    s.add_argument("--notes-out", required=True)
    s.set_defaults(fn=cmd_promote_check)

    s = sub.add_parser("promote-write")
    s.add_argument("--version", required=True)
    s.add_argument("--source", required=True, help="the edge add-on folder as it was when the build was published")
    s.add_argument("--stable-dir", default="housemate")
    s.add_argument("--notes", required=True)
    s.set_defaults(fn=cmd_promote_write)

    a = p.parse_args(argv)
    try:
        a.fn(a)
    except PipelineError as e:
        print(f"::error::{e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

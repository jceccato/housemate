#!/usr/bin/env python3
"""Turn a checkout of Matt Pocock's skills into Housemate's baseline skills and commands.

    vendor_skills.py <upstream checkout> <kit dir> --revision <40 hex>

Runs while the image builds (see the Dockerfile), against the revision pinned
there, and writes into the kit (/usr/share/housemate/kit), so seeding and
incoming cover the result like any other kit file.

Upstream marks the steps only a person may start with `disable-model-invocation:
true`. OpenCode ignores that flag and lists every skill to the model, so those
steps are written as OpenCode *commands* (a command is typed by the user and is
never offered to the model); the rest stay skills. The two lists below say which
is which, and the build stops if upstream's own flag disagrees, so a skill that
changes hands upstream is noticed, not shipped on the wrong side.
"""

import argparse
import pathlib
import re
import shutil
import sys

LICENSE_NOTE = "MIT, copyright (c) 2026 Matt Pocock"

# Model-invocable upstream, so they stay skills: name -> upstream folder.
SKILLS = {
    "tdd": "skills/engineering/tdd",
    "diagnosing-bugs": "skills/engineering/diagnosing-bugs",
    "codebase-design": "skills/engineering/codebase-design",
    "domain-modeling": "skills/engineering/domain-modeling",
    "grilling": "skills/productivity/grilling",
}

# User-invoked upstream, so they ship as commands: command name -> upstream folder.
COMMANDS = {
    "grill": "skills/engineering/grill-with-docs",
    "to-spec": "skills/engineering/to-spec",
    "to-tickets": "skills/engineering/to-tickets",
    "triage": "skills/engineering/triage",
    "setup-matt-pocock-skills": "skills/engineering/setup-matt-pocock-skills",
}

# Upstream names that now mean a command of another name.
RENAMES = {"grill-with-docs": "grill"}

SETUP = "setup-matt-pocock-skills"
SUPPORT = ".opencode/support"


def fail(message):
    sys.exit(f"vendor_skills: {message}")


def split_frontmatter(text, where):
    m = re.match(r"---\n(.*?)\n---\n(.*)\Z", text, re.S)
    if not m:
        fail(f"{where}: no frontmatter")
    fields = {}
    for line in m.group(1).splitlines():
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip().strip('"')
    return fields, m.group(2)


def fit(text):
    """Make upstream's prose fit this agent and this tracker."""
    for old, new in RENAMES.items():
        text = text.replace(f"/{old}", f"/{new}")
    text = text.replace("the Skill tool", "the `skill` tool")
    return text.replace(".scratch/", "tracker/")


def copy_tree(src, dest, transform=None, skip=("agents",)):
    for path in sorted(src.rglob("*")):
        rel = path.relative_to(src)
        if path.is_dir() or rel.parts[0] in skip:
            continue
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if transform and path.suffix == ".md":
            target.write_text(transform(path.read_text()))
        else:
            shutil.copy2(path, target)


def vendor_skill(upstream, kit, name, folder):
    src = upstream / folder
    skill = src / "SKILL.md"
    if not skill.is_file():
        fail(f"upstream has no {folder}/SKILL.md (needed for the skill '{name}')")
    fields, _ = split_frontmatter(skill.read_text(), str(skill))
    if fields.get("disable-model-invocation") == "true":
        fail(f"'{name}' is now user-invoked upstream; it must ship as a command, not a skill")
    copy_tree(src, kit / ".opencode/skills" / name, transform=fit)


def vendor_command(upstream, kit, name, folder):
    src = upstream / folder
    skill = src / "SKILL.md"
    if not skill.is_file():
        fail(f"upstream has no {folder}/SKILL.md (needed for the command '{name}')")
    fields, body = split_frontmatter(skill.read_text(), str(skill))
    if fields.get("disable-model-invocation") != "true":
        fail(f"'{name}' is no longer user-invoked upstream; decide whether it stays a command")
    support = f"{SUPPORT}/{name}"
    companions = [p for p in src.iterdir() if p.is_file() and p.name != "SKILL.md"]
    for companion in companions:
        # Links between a command's files point at where the companions now live.
        body = re.sub(rf"\]\((?:\./)?{re.escape(companion.name)}\)", f"]({support}/{companion.name})", body)
    description = fields.get("description", "").replace("\n", " ")
    text = f"---\ndescription: {description}\n---\n{fit(body).rstrip()}\n\nArguments from the user, if any: $ARGUMENTS\n"
    target = kit / ".opencode/commands" / f"{name}.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text)
    copy_tree(src, kit / support, transform=fit, skip=("agents", "SKILL.md"))


def preconfigure(kit):
    """What /setup-matt-pocock-skills would write for a local-markdown tracker."""
    setup = kit / SUPPORT / SETUP
    docs = kit / "docs/agents"
    docs.mkdir(parents=True, exist_ok=True)
    local = (setup / "issue-tracker-local.md").read_text()
    header = (
        "<!-- Housemate: the tracker is local markdown in this folder's `tracker/`. For GitHub Issues,\n"
        f"     run /{SETUP}; its GitHub template is in {SUPPORT}/{SETUP}/. -->\n\n"
    )
    (docs / "issue-tracker.md").write_text(header + local)
    for name in ("triage-labels.md", "domain.md"):
        shutil.copy2(setup / name, docs / name)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("upstream", type=pathlib.Path)
    parser.add_argument("kit", type=pathlib.Path)
    parser.add_argument("--revision", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9a-f]{40}", args.revision):
        fail("--revision must be a full 40-hex commit")

    for name, folder in SKILLS.items():
        vendor_skill(args.upstream, args.kit, name, folder)
    for name, folder in COMMANDS.items():
        vendor_command(args.upstream, args.kit, name, folder)
    preconfigure(args.kit)

    notice = args.kit / SUPPORT / "mattpocock-skills"
    notice.mkdir(parents=True, exist_ok=True)
    licence = args.upstream / "LICENSE"
    if not licence.is_file():
        fail("upstream has no LICENSE to carry")
    shutil.copy2(licence, notice / "LICENSE")
    (notice / "README.md").write_text(
        "# Matt Pocock's engineering skills\n\n"
        "The skills in `.opencode/skills/` (tdd, diagnosing-bugs, codebase-design, domain-modeling,\n"
        "grilling) and the commands in `.opencode/commands/` (grill, to-spec, to-tickets, triage,\n"
        f"setup-matt-pocock-skills) come from https://github.com/mattpocock/skills at commit\n{args.revision}\n"
        f"({LICENSE_NOTE}), adapted for OpenCode and for the tracker in `tracker/`. The licence is in\n"
        "`LICENSE` beside this file. Your copies are yours to edit; later versions arrive as incoming.\n"
    )


if __name__ == "__main__":
    main()

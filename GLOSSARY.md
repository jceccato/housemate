# Glossary

The words Housemate uses. Use them as defined here, in issues, code and docs.

**Built-in rules**
The image's own agent rules, shipped inside the add-on as OpenCode's global
`AGENTS.md` and updated with every release. Distinct from the **kit**: the user
does not edit them, and they never arrive as **incoming**. _Avoid_: "system
prompt", "default rules".

**Built-in skill**
A skill shipped in the image (today `incoming-review`) and replaced on every
start, like the **built-in rules**, so it works whatever the user has done to
their own kit. Not part of the **kit**.

**Edge**
The add-on "Housemate (edge)" (slug `housemate_edge`): the newest build,
published on every merge to `main`, for testers and the maintainer's own Home
Assistant. It can be installed beside **stable**. _Avoid_: "beta", "nightly",
"latest" (there is no `latest` tag).

**Incoming**
The folder (`/config/.housemate/incoming/`) where the add-on stages each **kit** file that changed
in a newer image, with release notes. The agent reviews it with the user by a
three-way comparison (what shipped before, what ships now, what the user has).
Nothing in it is applied without the user's say-so. _Avoid_: "update",
"overwrite", "sync".

**Job**
A session started by Home Assistant rather than typed in the panel, such as a
spoken request. It is created through the **kick-off** endpoint, and its
household is notified when it needs an answer or is done.

**Kick-off**
The small endpoint inside the add-on (port 8765, internal network only) that
Home Assistant calls to start a **job**. A request from a non-administrator is
put in the chat and waits for an administrator.

**Kit**
The generic starter set copied into the user's `/config` once, when the add-on first starts:
an agent rules file, a cheat sheet, a memory folder, how-tos, scripts, skills and
a local-markdown tracker. From then on it is the user's. _Avoid_: "template",
"defaults".

**Kit base**
The shipped text of every kit file, kept at `/config/.housemate/base/<path>`.
It is the third text of the three-way comparison: the next image no longer
carries the old kit, and a hash alone cannot give the text back. _Avoid_:
"backup", "original".

**Kit manifest**
`/config/.housemate/kit-manifest.json`: the kit version seeded, when, a SHA-256
per file shipped, and the files the user already had (`skipped_existing`). Its
existence is what makes seeding happen once. _Avoid_: "lockfile".

**Kit version**
A whole number in the image's `kit-version` file, raised whenever a kit file
changes and described in `kit-changelog.md`. A start whose image has a higher
kit version than the manifest stages **incoming**. Unrelated to the add-on's
own version. _Avoid_: "template version".

**Onboarding**
The agent-led first-run walk-through (and a skill that can be re-run): model
provider, `git init`, an entity and area scan that seeds the cheat sheet, the
phone to notify, the optional private remote, the voice blueprint, and a first
small automation.

**Stable**
The add-on "Housemate" (slug `housemate`): a build that **edge** has run and the
maintainer has deliberately promoted, with its changelog entry as release notes.
What most users install.

**Yolo**
The user's choice, offered for a bigger request, to skip the grilling and
planning and just have the agent do the work. The alternative is to "grill" it:
the user types the command that starts the interview. The agent never starts a
grilling on its own.

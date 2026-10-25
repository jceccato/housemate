# Glossary

The words Housemate uses. Use them as defined here, in issues, code and docs.

**Built-in rules**
The image's own agent rules, shipped inside the add-on as OpenCode's global
`AGENTS.md` and updated with every release. Distinct from the **kit**: the user
does not edit them, and they never arrive as **incoming**. _Avoid_: "system
prompt", "default rules".

**Edge**
The add-on "Housemate (edge)" (slug `housemate_edge`): the newest build,
published on every merge to `main`, for testers and the maintainer's own Home
Assistant. It can be installed beside **stable**. _Avoid_: "beta", "nightly",
"latest" (there is no `latest` tag).

**Incoming**
The folder in `/config` where the add-on stages each **kit** file that changed
in a newer image, with release notes. The agent reviews it with the user by a
three-way comparison (what shipped before, what ships now, what the user has).
Nothing in it is applied without the user's say-so. _Avoid_: "update",
"overwrite", "sync".

**Kit**
The generic starter set copied into the user's `/config` once, when the add-on first starts:
an agent rules file, a cheat sheet, a memory folder, how-tos, scripts, skills and
a local-markdown tracker. From then on it is the user's. _Avoid_: "template",
"defaults".

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

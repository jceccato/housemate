# Skill mechanics

The skill-specific branch of [`writing-for-agents`](SKILL.md): what changes when the document is a skill or a command (where it lives, the invocation choice, and router commands). Everything else about writing it is the universal reference in `SKILL.md`.

## Where they live

- A **skill** is a folder `.opencode/skills/<name>/` with a `SKILL.md` (frontmatter `name`, matching the folder, and `description`) and any files it points at.
- A **command** is a single file `.opencode/commands/<name>.md` (frontmatter `description`; the body is the prompt; `$ARGUMENTS` is what the user typed after the name). Extra files a command points at go elsewhere (for example `.opencode/support/<name>/`): every `.md` file inside `commands/` becomes a command.
- OpenCode reads both when it starts. After adding or changing one, tell the user to restart OpenCode.

## Invocation

Two choices, trading the two loads:

- A **skill** is listed to the agent with its `description`, so the agent can load it autonomously and other skills can reach it. The user can name it too. The description is the skill's top-level context pointer, always loaded: permanent context load in exchange for discoverability. A skill that is all reference is also one home for shared reference: other skills and commands can load it, so reference several of them need lives in one place. Write a model-facing description carrying the trigger branches (the pointer-writing rules in `SKILL.md` apply in full).
- A **command** is reachable only by the user typing its name: it is never listed to the agent, and no skill can start it. Zero context load, but it spends the user's memory: they must know it exists. The `description` is human-facing: a one-line summary, trigger lists stripped. **OpenCode ignores `disable-model-invocation`**, so a step only the user may start is a command, not a skill with that flag.

Choose a skill only when the agent must reach it on its own, or another skill must. If it only ever fires by hand, make it a command.

Shared reference that two commands both need can live in neither: put it in a skill the commands load, or in a plain file outside both that each points at.

## Splitting by invocation

Split off a skill when you have a distinct leading word that should trigger it on its own (a trigger word the user actually says), or another skill must reach it. You pay context load for the new always-listed description, so that independent reach has to be worth it.

## Router commands

When commands multiply past what the user can remember, a **router** cures it: one command, or a line in `AGENTS.md`, that names the others and when to reach for each. It can only hint, never start them: the agent has no way to run a command, so the hint tells the user what to type.

# Kit changelog

What changed in the starter kit, per kit version. Housemate stages this, with the
changed files, as incoming when a newer kit arrives. One `## Kit version N`
section per version, newest first, each written for the user.

## Kit version 1

The first kit, as it is first copied into `/config`:

- **Agent rules** (`AGENTS.md`): where things are, how the agent works (find
  entities through the API, prefer packages, check the configuration before a
  restart, reload rather than restart, back up before big changes, commit every
  change with a reason, secrets by name only, review its own work, script what
  it repeats) and that commands are yours to start.
- **A cheat sheet** (`docs/cheat-sheet.md`) of your entities, areas and quirks,
  which the agent grows, and **memory** (`memory/`), one fact per file.
- **How-tos** (`docs/how-to/`): write and reload an automation, test a
  template, read history, roll back with git, and update Home Assistant.
- **Scripts** (`scripts/`): `check-config.sh` and `git-init.sh`.
- **A tracker** (`tracker/`): bigger jobs as markdown files.
- **Skills** (`.opencode/skills/`): `home-assistant` (the API), `orchestrator`,
  `code-review`, `writing-for-agents`, and Matt Pocock's `tdd`,
  `diagnosing-bugs`, `codebase-design`, `domain-modeling` and `grilling`; and
  **commands** only you can start (`.opencode/commands/`: `/grill`, `/to-spec`,
  `/to-tickets`, `/triage`, `/setup-matt-pocock-skills`).
- **Questions through the question tool.** The agent asks its setup and decision
  questions (onboarding, "grill it, or yolo?", the update approvals) through
  OpenCode's `question` tool: a few options with the recommended one first, and a
  box to type your own answer. Onboarding recommends restarting Home Assistant
  right after you ask for voice, or for anything else that works only after it; a
  restart it proposes for any other reason recommends "later".
- **A name of your own for voice.** Onboarding asks what you want to call Housemate in Assist
  ("Jarvis, build me ..."); the default is "Housemate". Ask the agent to change it later;
  no restart is needed.
- **First run starts itself.** The first time the panel opens, a chat called
  "Welcome to Housemate" begins onboarding without you typing anything.

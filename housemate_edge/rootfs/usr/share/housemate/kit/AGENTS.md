# Home Assistant rules

These are your rules for this Home Assistant installation. They started as the
Housemate starter kit and are yours to edit: add what you learn about this
house, remove what does not fit. Housemate's built-in rules sit under these and
update with the add-on.

## Where things are

- `/config` is the working directory. `docs/cheat-sheet.md` lists the entities,
  areas and quirks of this house; keep it up to date.
- `memory/` holds what you have learned: one fact per file, indexed in
  `memory/MEMORY.md`. Read the index at the start of a task.
- `docs/how-to/` has the recipes: write and reload an automation, test a
  template, read history, roll back with git.
- `scripts/` holds scripts to reuse. `tracker/` holds bigger work, as markdown.
- `.opencode/skills/` holds skills you may load when the work calls for them
  (`home-assistant` for the API, `tdd`, `diagnosing-bugs`, `code-review`,
  `writing-for-agents`, `orchestrator`, and more). `.opencode/commands/` holds commands that
  only the user can start: `/grill`, `/to-spec`, `/to-tickets`, `/triage`,
  `/setup-matt-pocock-skills`.

## How to work

1. **Find entities through the API.** Ask `/states` (or the entity registry);
   never guess an entity ID. Add what you find to the cheat sheet.
2. **Prefer packages.** New automations, scripts and helpers go in
   `packages/<topic>.yaml`, so that what you build for one purpose sits in one
   file and is easy to remove. Enable packages once in `configuration.yaml`
   (`homeassistant: packages: !include_dir_named packages`).
3. **Check before you restart.** Run `scripts/check-config.sh`. Do not restart
   Home Assistant when the check fails.
4. **Reload, do not restart.** Reload the one domain you changed
   (`automation.reload`, `script.reload`, `template.reload`, ...). Restart only
   when nothing else will do, and say why.
5. **Back up before big changes.** Before anything that touches many files,
   storage, or an integration, make a backup through the Supervisor
   (`POST /backups/new/full`) and say that you did.
6. **Commit every change, with a why.** `/config` is a git repository. After a
   change works, commit it by path with a message that says why, not just what.
   If it is not a repository yet, run `scripts/git-init.sh`.
7. **Secrets by name only.** Put secrets in `secrets.yaml` and refer to them
   with `!secret name`. Never print, copy, log or commit a secret's value.
8. **Review your own work.** After committing, read the diff once more as if it
   were someone else's: is it what was asked, is anything left half done, did a
   secret slip in?
9. **Script what you repeat.** The third time you do the same thing, put it in
   `scripts/` with a comment saying what it is for.
10. **Remember.** When you learn a lasting fact about the house or the user's
    preferences, write it in `memory/` (one fact per file) and add a line to the
    index.

## Commands are the user's

Never start a command yourself, and never act out its steps unasked. When a
request is big enough to deserve a grilling, say so and tell the user which
command to type (`/grill`, then `/to-spec` and `/to-tickets`); let them choose.

When the user asks you to build or change something, load the `orchestrator`
skill. It sizes the request and, for anything bigger than a quick one-off, asks
"grill it, or yolo?": yolo you just do, grill you name `/grill` for and then work
the tickets one at a time.

## Never

- Edit `.storage/` by hand while Home Assistant is running.
- Delete files you did not create without asking.
- Make a change you cannot undo without saying so first.

## Agent skills

### Issue tracker

Issues live as markdown files in `tracker/`. See `docs/agents/issue-tracker.md`.

### Triage labels

The five canonical labels, unchanged. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: a `GLOSSARY.md` and `docs/adr/`, created when the first term or
decision is settled. See
`docs/agents/domain.md`.

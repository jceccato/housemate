# Housemate (edge)

<!-- edge-only -->
The newest Housemate build, for testers. It may change or break between
releases; the stable add-on, **Housemate**, is the one to rely on.
<!-- /edge-only -->

## What it gives you

A **Housemate** panel in the sidebar (administrators only): code-server with
your `/config` open and [OpenCode](https://opencode.ai) in its terminal. Open a
terminal in the panel and run `opencode`, or use the OpenCode button in the
editor's title bar.

## Configuration

| Option | Meaning |
| ------ | ------- |
| `provider` | `go` for OpenCode Go, `zen` for OpenCode Zen. |
| `api_key` | Your key from [opencode.ai](https://opencode.ai). Optional with Zen, whose free models need none. |

The key is written to OpenCode's provider configuration when the add-on starts.
Besides the add-on's own private options and data, it is not put in the logs,
on a command line, or in your `/config`. Restart the add-on after changing an option.

OpenCode Go limits requests to an allowlist of IP addresses. If calls start
failing after your home address changes, check the allowlist on your account.

## What persists

Everything OpenCode and code-server keep (sessions, settings, sign-in) lives in
the add-on's own data folder and survives restarts and updates.

## The starter kit

On the first start the add-on copies a starter kit into your `/config`: an
`AGENTS.md` of Home Assistant rules, a cheat sheet (`docs/cheat-sheet.md`), a
`memory/` folder, how-tos in `docs/how-to/`, a `scripts/` folder and a local
`tracker/`. They are yours from then on: the add-on never writes them again.
What it copied is recorded, with the kit version and a hash of each file, in
`/config/.housemate/kit-manifest.json`. A file you already had is never
overwritten; it is listed in that manifest as skipped. The shipped text of every
kit file is kept beside it, in `/config/.housemate/base/`, so that a later
update can tell what you changed. If you delete `/config/.housemate/`, the next
start seeds again: files you have are never overwritten, but kit files you had
deleted come back.

### When the kit changes: incoming

A newer Housemate may carry a better kit. It never overwrites your files: on the
first start with a newer kit it stages each changed, added or removed kit file in
`/config/.housemate/incoming/`, with the kit's release notes
(`RELEASE-NOTES.md`) and the text you were shipped. Nothing else is touched.
Ask the agent to review incoming (it uses the `incoming-review` skill): it
compares what you were shipped, what ships now and your file, and proposes
merges. Files you never changed go through in one batch approval; nothing is
applied without your say-so. The add-on's built-in rules are separate: they
update with every release and are not part of this.

## Git in /config

`/config/scripts/git-init.sh` puts `/config` under git (the agent runs it
during onboarding). It keeps out `secrets.yaml`, databases, logs, backups,
media and TTS caches, and all of `.storage` except the dashboard and helper
files; authentication and integration credentials are never tracked. Edit
`.gitignore` to change the policy.

## Voice kick-off

Say "Housemate, build me ..." to Assist and a job starts in Housemate's chat.
Your phone gets a notification that opens Housemate, a persistent notification
appears in Home Assistant, and there is another when the job needs an answer or
is done. A request from someone who is not a Home Assistant administrator (or
from a voice device that cannot say who is speaking) is put in the chat and
waits for an administrator; nothing runs until one continues it.

To set it up, run `housemate-voice-install` in the panel's terminal (onboarding
does this with your OK). It adds a blueprint, "Housemate voice kick-off", and a
`rest_command` that posts to the add-on, and leaves a `rest_command:` of your own
alone. Restart Home Assistant once, then create an automation from the blueprint
and give it your phone's notify service (for example `notify.mobile_app_my_phone`).

The blueprint's action talks to a small endpoint inside the add-on, on port 8765
of the add-on's hostname, reachable from Home Assistant on its internal network.
The port is not published on your network. The endpoint takes no password:
anything on Home Assistant's internal network that can reach it can start a job
as a non-administrator's request or, naming an administrator's id, as theirs.

## Protection mode

Docker access is declared but stays off while the add-on's **Protection mode**
is on, which is the default. Turn it off only if you understand that the agent
then has root-level reach into the host.

## Versions

OpenCode and code-server are pinned and never update themselves. They change
only when the add-on does.

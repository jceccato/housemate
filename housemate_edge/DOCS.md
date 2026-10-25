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
| `review_notify` | Optional. The notify service of your phone for the daily update review (for example `notify.mobile_app_my_phone`). |
| `review_time` | When the daily update review is sent, `HH:MM` in Home Assistant's time zone. Default `09:00`. |

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

### Skills and commands

The kit also puts skills and commands in `/config/.opencode/`. **Skills** are
ones the agent loads when the work calls for them: `orchestrator`, `tdd`,
`diagnosing-bugs`, `code-review`, `home-assistant` and a few more. **Commands**
are steps only you start, by typing them in OpenCode's chat: `/grill` (the agent
interviews you about a plan), `/to-spec` (writes it up), `/to-tickets` (cuts it
into tickets), `/triage` (sorts tickets) and `/setup-matt-pocock-skills` (for a GitHub
Issues tracker). The agent never starts one for you.

**Grill or yolo.** Ask for something and the agent judges whether it is a quick
one-off or a bigger job. A small thing it just does. For a bigger one it asks
"grill it, or yolo?". Yolo: it does the work and tells you. Grill: it tells you
to type `/grill`, and once you have the spec and tickets (`/to-spec`,
`/to-tickets`, kept as markdown in `/config/tracker/`) it works them one at a
time, stopping whenever a step is yours to take. Afterwards it reviews its own
work and updates its notes. Matt Pocock's skills are MIT licensed; the notice
is in `THIRD_PARTY_NOTICES.md`.

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
will offer to, and only with your OK). It adds a blueprint, "Housemate voice kick-off", and a
`rest_command` that posts to the add-on, and leaves a `rest_command:` of your own
alone. Restart Home Assistant once, then create an automation from the blueprint
and give it your phone's notify service (for example `notify.mobile_app_my_phone`).

The blueprint's action talks to a small endpoint inside the add-on, on port 8765
of the add-on's hostname, reachable from Home Assistant on its internal network.
The port is not published on your network. The endpoint takes no password:
anything on Home Assistant's internal network that can reach it can start a job
as a non-administrator's request or, naming an administrator's id, as theirs.

## Updates

Once a day (09:00 in Home Assistant's time zone, or the **Time of the daily
update review** option) Housemate looks at everything waiting: Home Assistant
Core, the operating system, the Supervisor, add-ons, HACS, Housemate itself, and
changes to your starter kit staged as incoming. If anything is, you get **one**
notification, a persistent one in Home Assistant and, when the option **Phone to
notify for the daily update review** names your phone's notify service, one on
the phone. Nothing waiting, no notification. Device firmware and other servers'
versions are listed but never updated.

Its **Review** link opens Housemate, where a chat named "Update review" is
already waiting with nothing run yet. Say go, and the agent follows the
`update-review` skill: it reads the release notes between your installed and the
target version, matches the backward-incompatible changes against the
integrations and YAML in your configuration, and tells you which apply. It then
asks you twice, with a question you can answer from the phone: **install** (after a
full backup, one update at a time with a health check after each) and **restart**
(the host reboot after an OS update, the Core update, a restart for HACS, and
Housemate's own update, which ends the chat). Give both up front ("do it all") or
leave the restart to be asked. It stops at the first failure and never rolls
back without asking. The procedure is `docs/how-to/update-home-assistant.md` in
your `/config`; edit it for your house.

## Protection mode

Docker access is declared but stays off while the add-on's **Protection mode**
is on, which is the default. Turn it off only if you understand that the agent
then has root-level reach into the host.

## Versions

OpenCode and code-server are pinned and never update themselves. They change
only when the add-on does.

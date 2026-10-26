# Housemate (edge)

<!-- edge-only -->
The newest Housemate build, for testers. It may change or break between
releases; the stable add-on, **Housemate**, is the one to rely on.
<!-- /edge-only -->

## What it gives you

A **Housemate** panel in the sidebar (administrators only): code-server with
your `/config` open and [OpenCode](https://opencode.ai) already running.

### What you see when you open the panel

OpenCode opens by itself in a large tab in the editor area, on your newest chat,
so a notification's link (a voice job, the update review) lands on the chat it
started. Opening the panel again does not start a second OpenCode. If the add-on restarts
(an update, a reboot) while the panel is open, the page reloads by itself within a few seconds of the add-on coming back, and OpenCode
reopens, on the chat a job last marked as current (a voice job, the update review;
the id is in `/config/.housemate/current-session`) or, with none, your newest chat. Visual Studio
Code's own AI chat is hidden, so Housemate's agent is the only one on screen. The editor starts in a dark theme; pick another in the settings and it stays.

On the first start the panel is switched on in the sidebar by itself. To hide it,
turn off **Show in sidebar** on the add-on's Info page; Housemate never switches it
back on.

To **start a new chat**, click **New chat** in the bar at the bottom, or open the
command palette (`F1`) and run **Housemate: Start a new chat**. To **go back to an
earlier chat**, click **Chats** (or run **Housemate: Choose another recent chat**)
and pick one; inside OpenCode, `/sessions` does the same. If you close the
OpenCode tab, run **Housemate: Open the agent (newest chat)**.

OpenCode may read Housemate's own files (`/usr/share/housemate`: its rules, skills
and how-tos) without asking. Anything else outside `/config` still asks first, and
writing is unchanged.

## Configuration

| Option | Meaning |
| ------ | ------- |
| `provider` | `go` for OpenCode Go, `zen` for OpenCode Zen, `openai-compatible` for any OpenAI-style endpoint (see [Providers](#providers)). |
| `base_url` | Only for `openai-compatible`, where it is required: the endpoint's base URL, for example `https://openrouter.ai/api/v1`. |
| `api_key` | Your key from [opencode.ai](https://opencode.ai) for Go or Zen (Zen's free models need none), or your key at the `openai-compatible` endpoint (optional for a local server). |
| `model` | Optional, except with `openai-compatible`, where it is required and is the bare model id the endpoint expects. A model as `provider/model`, for example `opencode-go/deepseek-v4.1-flash`. Empty means the provider's default: `opencode-go/deepseek-v4.1-flash` with Go, a free model with Zen. |
| `review_notify` | Optional. The notify service of your phone for the daily update review (for example `notify.mobile_app_my_phone`). |
| `review_time` | When the daily update review is sent, `HH:MM` in Home Assistant's time zone. Default `09:00`. |

The key is written to OpenCode's provider configuration when the add-on starts.
Besides the add-on's own private options and data, it is not put in the logs,
on a command line, or in your `/config`. Restart the add-on after changing an option.

### What it costs

Housemate is free. The model provider charges for the model's use:

- **OpenCode Go** is a subscription. Its default model is
  `opencode-go/deepseek-v4.1-flash`.
- **OpenCode Zen** is pay-as-you-go. It also offers some **free models**, which
  are the way to try Housemate before spending anything. They are limited-time,
  they come and go, and they have a **usage limit**: a long job can stop
  partway when one runs out. Switch provider or model, or wait, then tell the
  agent to continue.

Prices and which models are free are on [opencode.ai](https://opencode.ai) and
are not Housemate's to set.

### Providers

- **OpenCode Go** (recommended) is the tested one: Housemate's end-to-end tests and
  its maintainers use **DeepSeek V4.1 Flash on OpenCode Go**, the default model.
- **OpenCode Zen** works, with free models that have a usage limit.
- **`openai-compatible`** points OpenCode at any endpoint that speaks the OpenAI
  chat-completions API. It is **untested** against real services; Housemate's
  tests only drive it against a stand-in server. Fill three options:
  `base_url` (the part before `/chat/completions`, for example
  `https://openrouter.ai/api/v1` for OpenRouter or `http://my-server.local:8000/v1`
  for a server you run), `api_key` (empty for a local server that needs none) and
  `model` (**required**: the model id exactly as the endpoint names it, for
  example `deepseek/deepseek-chat`). Restart the add-on. If `base_url` or `model`
  is missing, the add-on stops at start and its log says which; the key is never
  printed.

To use another model on Go or Zen, set `model` to `provider/model` (for example
`opencode-go/deepseek-v4.1-flash`, or `opencode/...` for Zen). Other providers
and models are untested, and support is best-effort.

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

### Onboarding

The first time you talk to the agent on a fresh install, it welcomes you and
walks you through setup, ending with a small automation built together. It takes
about ten minutes and every step can be skipped: the model provider and key, putting `/config`
under git, a scan of your entities, areas and devices into the cheat sheet (with
the names you use for things), the phone to notify, an optional private remote
(and GitHub Issues for bigger jobs if you link one), the voice sentence
("Housemate, build me ...", installed only with your OK, and Home Assistant is
restarted only if you say so: two separate questions, and "later" leaves a note
of the pending restart) and the first automation. After the voice step it suggests
a useful request to try, built from your own house, and shows where voice jobs
appear: the panel opens on the newest chat, the **Chats** button in the status
bar lists the others, and `/sessions` in OpenCode does the same. If you
have no phone registered with Home Assistant, that step is skipped and
notifications appear in Home Assistant itself. Say "run onboarding" at any time
to repeat a step. Progress is kept in `/config/.housemate/onboarding.json`; the
scan writes between the `housemate-scan` markers of `docs/cheat-sheet.md` and
only there, so your own notes survive a re-scan. Helpers of the template or
group kind made in the Home Assistant UI are not tracked by git, because the file
that holds them also holds credentials.

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
The port is not published on your network. The endpoint takes no password and
believes the administrator's id in the request, so it answers Home Assistant
alone: it accepts connections only from Home Assistant Core (the Supervisor
network's gateway, `172.30.32.1`) and refuses every other add-on on that network.

## Who can reach the add-on

- The panel: code-server listens only inside the add-on; nginx in front of it
  accepts only the Supervisor's Ingress proxy (`172.30.32.2`), which has already
  checked that you are signed in to Home Assistant as an administrator. Other
  add-ons cannot reach it.
- OpenCode's own server listens on the add-on's loopback and nowhere else.
- The voice endpoint: Home Assistant Core only, as above.
- The panel is shown in the sidebar on the first start. If you hide it, open
  the add-on's page instead: **Open web UI**, or `/app/<slug>` (for the edge
  add-on, `/app/<repository id>_housemate_edge`).

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
leave the restart to be asked. With both given, a reboot or Housemate's own update does not
stop it: when the add-on starts again it continues the same chat by itself, and the chat is
the one the panel reopens on. It stops at the first failure and never rolls back without
asking. (The free Zen models have a usage limit: if one runs out mid-review, switch the
provider or try again later; the review resumes from where it was.) The procedure is `docs/how-to/update-home-assistant.md` in
your `/config`; edit it for your house.

## Protection mode

Docker access is declared but stays off while the add-on's **Protection mode**
is on, which is the default. Leave it on: Housemate does its work through Home
Assistant's API, the Supervisor's API and `/config`, none of which needs Docker.

Turn it off only if you want the agent to manage containers on the host, and
understand the risk. It then has root-level reach into the host through Docker:
it can read other add-ons' data and change or break anything on the machine,
far beyond your configuration, and git and backups of `/config` do not cover
that. A model can be wrong or be misled by text it reads. To change it, use the
**Protection mode** switch on the add-on's Info page and restart the add-on.

## Troubleshooting

Work down this list.

1. **Go: calls fail, or nothing answers.** OpenCode Go keys can be limited to an
   **allowlist of IP addresses**. If your home address changed, the key is
   still valid but calls from the new address are refused. Check the allowlist
   on your account at [opencode.ai](https://opencode.ai) first.
2. **The key.** It must be pasted whole into the Configuration tab, and the
   add-on restarted after saving: it is read at start.
3. **A Zen free model stops partway.** It reached its usage limit. Switch
   provider or model, or try later, then tell the agent to continue.
4. **"Cannot reconnect" after a restart.** The page reloads itself when the
   add-on is back; give it a minute.
5. **Not in the sidebar.** It was hidden. Use **Open web UI** on the add-on's
   page, or turn **Show in sidebar** back on.
6. **An "insecure context" notice from the editor.** Over plain `http` the
   editor shows it and no setting hides it. It is harmless; HTTPS (Home
   Assistant's own, or Nabu Casa's) removes it.

## What to send when something breaks

Open an issue at <https://github.com/jceccato/housemate/issues> with, redacted:

- **The add-on's log**: the **Log** tab, from the first lines after the start
  and the lines around the failure.
- **The versions**: the add-on (stable or edge, and its version, on the Info
  page), Home Assistant Core, OS and Supervisor, and your hardware (amd64 or
  aarch64; Green, Yellow, Pi, VM).
- **What you asked** the agent and what it did or said instead, and the model
  provider and model you use.

**Never paste an API key, a token or your `secrets.yaml`.** Read the log
through before posting it. A security problem goes to the repository's
`SECURITY.md` privately, not into a public issue.

## Support

Best-effort. Housemate is maintained by one person in their spare time. Issues
are read, but there is no promise of a reply time or a fix.

## Stable and edge

**Housemate** is a build that **Housemate (edge)** has run and the maintainer
has promoted, with release notes. **Housemate (edge)** is the newest build and
may change or break between releases; both can be installed side by side. Both
images are built for amd64 and aarch64 and tested on each in CI, on a runner of
that architecture. No real Green, Yellow or Raspberry Pi has run Housemate yet,
so reports from those are welcome.

## Versions

OpenCode and code-server are pinned and never update themselves. They change
only when the add-on does.

**Upstream attribution:** This is an independent Home Assistant add-on that redistributes and integrates OpenCode, © 2025 opencode, under the MIT License. It is not made by, affiliated with, or endorsed by the OpenCode team or Anomaly. See the [third-party notices](https://github.com/jceccato/housemate/blob/main/THIRD_PARTY_NOTICES.md).

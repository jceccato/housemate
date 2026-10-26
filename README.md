# Housemate

An agent that lives in Home Assistant and builds it with you.

You open **Housemate** in the Home Assistant sidebar and say what you want in
plain words: "turn the porch light on at sunset", "a dashboard for the
batteries in the house", "why did the heating come on at 3am?". The agent
([OpenCode](https://github.com/anomalyco/opencode)) writes the automation,
helper, script or dashboard in your `/config`, checks it, reloads it and tells
you what it did. `/config` is under git, so every change is a commit and
anything can be undone with a sentence.

> **Status: early.** Housemate is new and moving fast. The **edge** add-on is
> the one you can install today; **stable** appears in the store after its
> first promotion (see [Stable and edge](#stable-and-edge)). Expect rough edges
> and read [Support](#support) before you rely on it.

## What it does

- **A panel in the sidebar**, for Home Assistant administrators only: an editor
  (code-server) with your `/config` open and OpenCode's chat already running in
  it. It works from the phone app or a browser, with no extra sign-in.
- **Builds by chat**: automations, helpers, scripts, scenes, packages and
  dashboards. It finds entities through Home Assistant's API (not only the ones
  exposed to Assist), reads history and tests templates when it debugs, runs
  Home Assistant's configuration check before any restart, prefers a reload to
  a restart, and takes a backup before a big change.
- **Guarded by git**: `/config` is put under git on first use, with a commit
  per change saying why. Secrets, databases, logs, backups and the `.storage`
  files that hold sign-ins stay out of git. The agent reads `secrets.yaml` by
  name only and never prints a secret.
- **A starter kit**: agent rules, a cheat sheet of your entities that it grows,
  memory, how-tos, scripts, a small tracker for bigger jobs and a set of skills
  (including [Matt Pocock's engineering skills](https://github.com/mattpocock/skills)).
  It is copied into `/config` once and is yours from then on. Later kit changes
  arrive as **incoming** for you to review with the agent; nothing is
  overwritten.
- **Guided first run**: the agent walks you through setup the first time you
  talk to it (model, git, a scan of your house, the phone to notify, an
  optional private remote, the voice sentence, which it installs and restarts
  Home Assistant for only when you say yes to each) and builds one small
  automation with you.
- **Voice**: say "Housemate, build me ..." to Assist and a job starts in the
  chat; a notification tells you when it needs you or is done.
- **A daily update review**: one notification covers everything waiting (Home
  Assistant Core, the OS, add-ons, HACS, Housemate, kit changes). Its Review
  link opens a briefed chat that reads the release notes against your
  configuration, makes a backup and installs one update at a time, asking you
  twice (install, then restart).
- **It learns your house**: after committing work it reviews it, updates its
  notes, and turns anything it does twice into a script.

Everything is described in more detail in the add-on's **Documentation** tab
([`housemate_edge/DOCS.md`](housemate_edge/DOCS.md)).

## What it costs

Housemate is free and open source (MIT). **The model provider charges for the
model's use**, and the agent uses it every time it thinks, so the cost is
whatever you pay that provider. Housemate is **tested with DeepSeek V4.1
Flash on OpenCode Go**, its default; see [Providers](#providers) for the others.
The two from the OpenCode team:

| Provider | How it is paid | Notes |
| -------- | -------------- | ----- |
| **OpenCode Go** | A subscription | Its default model is `deepseek-v4.1-flash`, set by the `model` option (empty means the provider's default). Go keys can be locked to an IP allowlist; see [Troubleshooting](#troubleshooting). |
| **OpenCode Zen** | Pay as you go, with credit | Also offers some **free models**, which are the way to try Housemate before spending anything. They are limited-time, they come and go, and they have a **usage limit**: a long job (an update review, say) can stop partway when one runs out. Switch provider or wait, then tell the agent to continue. An update review resumes from its progress record; other jobs carry on from the chat. |

Current prices and which models are free are on [opencode.ai](https://opencode.ai)
and change; Housemate does not set or control them. Your key is written to
OpenCode's configuration when the add-on starts. Besides the add-on's own private
options and data, it is not put in a log, on a command line or in your `/config`.

## Providers

| `provider` option | Status | Notes |
| ----------------- | ------ | ----- |
| `go` (**recommended**) | **Tested.** Housemate's end-to-end tests and its maintainer use **DeepSeek V4.1 Flash on OpenCode Go**, the default model. | A subscription from [opencode.ai](https://opencode.ai). |
| `zen` | Works; free models are untested over long jobs. | Pay as you go, plus **free models** with a usage limit. |
| `openai-compatible` | **Untested** against real services. Housemate's tests drive it against a stand-in server only. | Any endpoint that speaks the OpenAI chat-completions API. |

For `openai-compatible`, fill three options in the Configuration tab:

- `base_url`: the endpoint's base URL, the part before `/chat/completions`.
  For example `https://openrouter.ai/api/v1` for OpenRouter, or
  `http://my-server.local:8000/v1` for a server you run yourself (vLLM, llama.cpp,
  Ollama's `/v1`). It must start with `http://` or `https://`.
- `api_key`: your key at that service. Leave it empty for a local server that
  needs none.
- `model`: **required**; the model id exactly as the endpoint names it, for
  example `deepseek/deepseek-chat` on OpenRouter. Housemate does not guess one.

Save, then restart the add-on. If `base_url` or `model` is missing the add-on
stops at start and its log says which. A small model, or one without good tool
calling, will do the work badly; that is the model's limit, not the add-on's.
Other providers and models are untested, and best-effort support applies.

To use a **different model on Go or Zen**, put it in the `model` option as
`provider/model`, for example `opencode-go/deepseek-v4.1-flash`
(`opencode-go/...` for Go, `opencode/...` for Zen). Empty means the provider's
default.

## Install

You need Home Assistant OS or a Supervised install (anything with the Add-on
Store). Add-ons are called **Apps** in recent Home Assistant versions; the steps
are the same.

1. In Home Assistant open **Settings > Add-ons** (**Apps**) **> Add-on Store**
   (**Install app**).
2. Open the menu (three dots, top right), choose **Repositories**, paste

   ```
   https://github.com/jceccato/housemate
   ```

   and **Add**. (Or open
   [this link](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2Fjceccato%2Fhousemate)
   and confirm.)
3. Find **Housemate (edge)** in the list (refresh the page if it is not there)
   and **Install**. This pulls a prebuilt image; it does not build on your box.
4. On the **Configuration** tab choose your **Model provider** (`go`,
   `zen` or `openai-compatible`; see [Providers](#providers)) and paste your
   **API key** (a Zen free model needs none). Save.
5. **Start** the add-on. Housemate switches itself on in the sidebar the first
   time it starts; open it from there. If you turn **Show in sidebar** off on
   the add-on's Info page, Housemate never turns it back on, and you can still
   reach the panel with **Open web UI** or at `/app/<slug>` (for the edge
   add-on `/app/<repository id>_housemate_edge`; the id is in the add-on's
   address).
6. Say hello. The agent walks you through setup; it takes about five minutes
   and every step can be skipped. OpenCode opens in a dark editor tab on your
   newest chat (or the one a job last marked current), with **New chat** and
   **Chats** buttons in the bar at the bottom. With Zen the default model is a
   free one.

You can change the provider or key later in the Configuration tab; restart the
add-on afterwards.

The editor opens in a dark theme (pick another in its settings and it stays).
Over plain `http`, code-server shows an "insecure context" notice that no
setting hides. It is harmless; HTTPS, whether Home Assistant's own or Nabu
Casa's, removes it.

## Stable and edge

One repository holds two add-ons.

- **Housemate** (stable): a build that **edge** has run, deliberately promoted,
  with release notes. The one to rely on.
- **Housemate (edge)**: the newest build, published on every change. It can
  change or break between releases. It can be installed beside stable.

Renovate watches OpenCode, code-server and the base image; CI builds and tests
each new release on both architectures, and a passing change goes to edge
automatically. Promotion to stable is by hand. **As of this writing nothing has
been promoted yet, so only edge is in the store;** this section and the install
steps change when stable is published. OpenCode and code-server are pinned and
never update themselves; they change only when the add-on does.
The pipeline is described in [docs/update-pipeline.md](docs/update-pipeline.md).

## Hardware

Prebuilt images exist for **amd64** (a mini PC, a VM) and **aarch64** (Home
Assistant Green and Yellow, Raspberry Pi). Both are built and
smoke-tested on every change in CI, each on a runner of its own architecture.
**No real Green, Yellow or Pi has run Housemate yet.** Edge users' reports will
be the evidence until one has; if you try it, please say how it went.

## Protection mode

The add-on declares Docker access, but Home Assistant withholds it while the
add-on's **Protection mode** is on, which is the default. Leave it on. Housemate
does its work (Home Assistant's API, the Supervisor's API, `/config`) without
Docker.

Turn it off only if you want the agent to manage containers on the host
itself, and understand what that gives it: root-level reach into the host
through Docker, which means it can read other add-ons' data and change or
break anything on the machine, far beyond your configuration. Git and backups
do not cover that. A model can be wrong or be tricked by text it reads, so the
risk is not hypothetical. To change it: the add-on's **Info** page, **Protection
mode** switch, then restart the add-on.

## Troubleshooting

Work down this list.

1. **Go: calls fail with an error from the provider, or nothing answers.**
   OpenCode Go keys can be restricted to an **allowlist of IP addresses**. If
   your home address changed (a new router, a provider reassigning it), the key
   is still valid but calls from the new address are refused. Check the
   allowlist on your account at [opencode.ai](https://opencode.ai) first.
2. **The key.** Check it was pasted whole into the Configuration tab and that
   you restarted the add-on after saving; the key is read at start.
3. **A Zen free model stops partway.** It hit its usage limit. Switch provider
   or model (`model` option) or try later, then tell the agent to continue.
4. **The panel shows "Cannot reconnect" after a restart.** It reloads itself
   when the add-on is back; give it a minute.
5. **Housemate is not in the sidebar.** You (or someone) hid it. Use **Open web
   UI** on the add-on's page, or turn **Show in sidebar** back on.

## What to send when something breaks

Open an [issue](../../issues) and include, redacted:

- **The add-on's log**: the add-on's **Log** tab (copy it from the first lines
  after the start, and the lines around the failure).
- **The versions**: the add-on (stable or edge, and its version, from the Info
  page), Home Assistant Core, OS and Supervisor, and your hardware
  (amd64 or aarch64; Green, Yellow, Pi, VM).
- **What you asked** the agent, and what it did or said instead; the model
  provider and model you use.

**Never paste an API key, a token or your `secrets.yaml`.** Look through the
log before posting it. A security problem goes to
[SECURITY.md](SECURITY.md), not a public issue.

## Support

Best-effort. Housemate is maintained by one person in their spare time. Issues
are welcome and read, but there is no promise of a reply time or a fix.

## Contributing and security

See [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md) and the
[Code of Conduct](CODE_OF_CONDUCT.md). The words this project uses are in
[GLOSSARY.md](GLOSSARY.md); the decisions behind it are in [docs/adr](docs/adr);
how it is tested is in [docs/testing.md](docs/testing.md).

## Credits

Housemate stands on other people's work:

- [OpenCode](https://github.com/anomalyco/opencode) (MIT), the agent.
- [code-server](https://github.com/coder/code-server) (MIT), the editor in the
  panel.
- The [hassio-addons](https://github.com/hassio-addons) base images (MIT), the
  add-on's base, and
  [Studio Code Server](https://github.com/hassio-addons/app-vscode) (MIT),
  whose add-on patterns Housemate reuses.
- [Matt Pocock's skills](https://github.com/mattpocock/skills) (MIT), the
  engineering skills in the kit.
- [`magnusoverli/opencode`](https://github.com/magnusoverli/opencode)
  (Unlicense), an existing OpenCode add-on, read for inspiration. Housemate
  shares no code with it; see [ADR 0001](docs/adr/0001-build-our-own-add-on.md).

"Home Assistant" is a trademark of Nabu Casa, Inc. Housemate is not affiliated
with or endorsed by it.

**Upstream attribution:** This is an independent Home Assistant add-on that redistributes and integrates OpenCode, © 2025 opencode, under the MIT License. It is not made by, affiliated with, or endorsed by the OpenCode team or Anomaly. See the [third-party notices](THIRD_PARTY_NOTICES.md).

## Licence

[MIT](LICENSE).

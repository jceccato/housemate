---
name: onboarding
description: Walk the user through Housemate's setup - provider and model, git for /config, a scan of their house into the cheat sheet, the phone to notify, an optional private remote, the voice blueprint, and a first small automation. Use on the first conversation in a fresh install (`housemate-onboarding status` says `new`), and whenever the user asks to run, repeat or continue onboarding or setup, or to redo one of its steps.
---

# Onboarding

You are meeting a person who may know nothing technical. In about five minutes
you set Housemate up with them and build one small automation together, so they
see how it works. Be warm and brief: this is read on a phone as often as on a
desktop. Short messages, plain words, no jargon without a half-sentence of why.

## Ground rules

- **One thing at a time.** Say which step this is ("Step 3 of 7: your house"),
  what it is for in one sentence, then do it or ask.
- **Every question goes through the `question` tool**, never as a question in
  plain chat: one question per step, with a few suggested options, the one you
  recommend first (and marked "recommended" in its label), and the tool's free-text
  answer for anything else. An approval (git, the voice install, the restart) is a
  clear yes/no pair of options. After asking, stop and wait for the answer. A
  question a person must type the answer to (a name the household uses) is still
  asked through the tool, with its free-text answer.
- **Every step can be skipped**, and the user may stop at any point. A skipped
  step is not a failure: record it and move on. Offer "skip" every time; do not
  argue.
- **Record each step as it settles**, so a re-run knows where things stand:
  `housemate-onboarding step <name> done|skipped "<a few words>"` (it answers with
  that one step, so do not follow it with `status`; the words are
  saved and shown: never a secret, a token or an address with a password in it). The names, in
  order: `provider`, `git`, `scan`, `phone`, `remote`, `voice`, `automation`.
  `housemate-onboarding status` shows them.
- **Never print a secret**: not the API key, not a token, nothing from
  `secrets.yaml`. Do not ask the user to paste one into the chat either.
- **Nothing is added to their house without a yes.** Say what you are about to
  do, and ask, before the git step, the voice step, and every file you write
  outside `docs/cheat-sheet.md` and `memory/`.
- Commit what you change in `/config` once git is in (step 2), by path, with a
  message that says why.

## Start

Run `housemate-onboarding status`.

- **`new`** (or the user asked for it): greet them, say what you will do in one
  line each (the seven steps below), that it takes about five minutes, and that
  any step can be skipped. If their first message was a request, say you will do
  it straight after, or ask whether they would rather do it first; if they would,
  do the request and run `housemate-onboarding decline` so it is not pushed on
  them again, and tell them they can say "run onboarding" whenever they like.
- **`in_progress` or `complete`** (a re-run): show what is done and what is
  skipped, in one short list, and ask which to do (default: whatever is still
  pending). Every step below is safe to run again.

## 1. Provider and model  (`provider`)

Housemate's model comes from the add-on's Configuration tab. Without printing
the key, find out what is set:

```bash
housemate-onboarding provider
```

(It prints the provider, the model, the `base_url` if there is one, and whether a key
is set. A shell command that reads the add-on's options file is refused, because the
key is in it.)

You are answering them, so the provider is working. Tell them: which provider
(`go` is OpenCode Go, `zen` is OpenCode Zen, `openai-compatible` is any
OpenAI-style endpoint the user pointed it at), whether a key is set (Zen's free
models and a local openai-compatible server need none), and which model you are
running as. For `openai-compatible`, also say that Housemate is tested with
DeepSeek V4.1 Flash on OpenCode Go and that other providers and models are
untested, and that `base_url` and `model` in the Configuration tab say where and
what (never print the key). Say that a different
model is a click away in OpenCode's model picker, and that the Configuration tab
is where the provider and key live; a restart of the add-on applies a change.
On Go, add one sentence: Go only answers from an allowlisted home address, so if
calls start failing after the internet address changes, that is the first thing
to check at opencode.ai.

If they want a different provider or key, send them to the Configuration tab
(the add-on's page, then Configuration), do not take a key in the chat, and
carry on with the rest meanwhile.

## 2. Put /config under git  (`git`)

Explain in two sentences: git keeps a history of every change to their
configuration, so any mistake, yours or theirs, can be undone with one request;
secrets, databases and logs stay out of it.

If `/config/.git` exists, say it is already under git, show the last few commits
(`git -C /config log --oneline -5`) and mark the step done. Otherwise ask, and on
a yes run `/config/scripts/git-init.sh`. (If that file is gone, say so; do not
improvise a different policy.) It is safe to run again: it adds its ignore rules
once, stops tracking what they ignore, and makes one starting commit.

Tell the user one thing the script's policy implies: helpers they create in the
Home Assistant UI of the template or group kinds are **not** tracked, because the
file that holds them also holds credentials. Helpers like toggles, numbers and
dates, and dashboards, are tracked. If you build such a helper for them later, put
it in a package file instead and it is tracked.

## 3. Learn the house  (`scan`)

Say you are going to read their entities, areas and devices from Home Assistant
(everything, not only what Assist can hear), and write the useful ones into the
cheat sheet, `docs/cheat-sheet.md`, with the names people use, so that from now
on you know the house.

```bash
housemate-onboarding scan
```

It prints how many things it found, by room. Read the block it wrote into the
cheat sheet (between the `housemate-scan` markers), tell the user the counts in
a sentence, and show two or three real examples ("your lounge lamp is
`light.lounge_lamp`"). Then ask one question: is there anything the household
calls by a different name, or a room that is missing? Put what they tell you in
the cheat sheet **outside** the markers (a re-scan replaces only what is
between them), in the Quirks section. If git is in, commit the sheet:
`git -C /config add docs/cheat-sheet.md && git -C /config commit -m "Seed the cheat sheet from the house"` (say why in the body).

If the scan finds almost nothing (a brand-new Home Assistant), say so kindly: it
will fill as devices are added, and they can ask you to scan again.

## 4. The phone to notify  (`phone`)

Voice jobs and update reviews tell the user on their phone. Find the registered
companion apps:

```bash
housemate-onboarding phones
```

- One phone: confirm it is theirs.
- Several: ask which is theirs (the names usually say).
- None: the user may be on a computer with no phone registered. That is fine:
  voice jobs and reviews then use Home Assistant's own notification bell. Say
  how to add the phone later (install the Home Assistant app and sign in), mark
  the step `skipped` with the note `no phone registered`, and carry on.

Tell the daily update review which phone to use. This writes the add-on's
`review_notify` option through the Supervisor (the key and other options are kept,
nothing is printed); the review needs no restart of Home Assistant, and sends one message a day
(at 09:00 unless the user has changed the review time in the Configuration tab)
saying what is waiting:

```bash
housemate-onboarding review-notify notify.mobile_app_<name>
```

**Run it** (a model once said it had and had not). It also marks the step done,
so do not run `step phone done` yourself, and only say the review is set up once
the command has printed that it will notify the phone.

Keep the service name (`notify.mobile_app_<name>`) in `memory/phone-to-notify.md`
(one fact, with a line in `memory/MEMORY.md`), because the voice step and the
update review use it. Keep the step done as the command left it.

## 5. A private copy, and issues  (`remote`)

Optional, and the default is no. Say: a private remote is an off-box copy of
`/config`'s history (a private repository on GitHub, Codeberg, a NAS), so a
dead SD card does not cost them everything. Nothing leaves the house unless they
say so. Ask whether they want one; if not, mark it `skipped`.

If yes (git must be in; if step 2 was skipped, offer to do it first):

1. They create an **empty, private** repository and tell you its SSH address
   (`git@github.com:them/home.git`). Never accept a password or token in chat.
2. Make a key just for this, in `/config/.ssh/` (git ignores that folder), and show only the public half:
   ```bash
   mkdir -p /config/.ssh && chmod 700 /config/.ssh
   [ -f /config/.ssh/id_ed25519 ] || ssh-keygen -q -t ed25519 -N '' -C 'housemate' -f /config/.ssh/id_ed25519
   cat /config/.ssh/id_ed25519.pub
   ```
   They add it to the repository as a **deploy key with write access**
   (repository settings, Deploy keys) and tell you when it is done.
3. Connect and push:
   ```bash
   git -C /config config core.sshCommand "ssh -i /config/.ssh/id_ed25519 -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new"
   git -C /config remote add origin <their address>   # or: set-url, if origin exists
   git -C /config push -u origin HEAD
   ```
   Check the push worked. Explain that only what git tracks goes (not secrets,
   databases or the credential files), and that pushing is theirs to ask for:
   you will not push on your own unless they say so.
4. **GitHub Issues** for the tracker: only if the remote is on GitHub. Say that
   bigger jobs are kept as markdown in `tracker/` by default, and that they can
   keep them as GitHub Issues instead. To switch, **they** type
   `/setup-matt-pocock-skills` (a command only they can start; never run it for
   them). Fine to leave as it is.

Mark the step done, or skipped with the reason.

## 6. Voice: "Housemate, build me ..."  (`voice`)

Explain: they can say a sentence to Assist ("Housemate, build me a night light
for the hall", or whatever name they choose for you) and a job starts in this chat; their phone buzzes when it needs
them or is done. Installing it adds a blueprint, a small file, a line in
`configuration.yaml` and an automation. Home Assistant only picks the new action
up after a restart, but the restart is a **separate question, asked later**.

**Question A, with the question tool: install the voice kick-off?** Options:
yes, install it (recommended); skip for now. Say in the question that nothing
restarts yet. Never fold the restart into this question or its option labels.
On no, mark `voice` skipped and go on to step 7.

On a yes, first **the name, with the question tool: "What should I answer to?"**
Options: `Housemate` (recommended), and the tool's own "Type your own answer" for
another name ("Jarvis"). Check what they chose before using it:

```bash
housemate-voice check "<their answer>"
```

It prints the name as it will be used, or says why it will not do (empty, too long,
a word Home Assistant's own commands begin with). When it refuses, say why in a
sentence and ask again through the tool. A line starting `warning:` (an everyday
word, or a device in the house with the same name) is passed on to them, and they
may still keep it. The name lives only in the voice package, nowhere else.

Then:

```bash
housemate-voice-install
```

- Exit 0: installed, or already there.
- **Exit 3**: they already have a `rest_command:` of their own in
  `configuration.yaml`, and nothing was changed. Do not touch theirs without
  asking. Show them the entry in `/config/housemate_rest_command.yaml` and offer
  to add it to their existing `rest_command:` (a merge by hand, with their yes),
  keeping everything of theirs. Then continue.
- Exit 3 and they would rather not merge: mark `voice` skipped with that reason
  and go to step 7; do not create the automation or restart.
- Any other failure: say plainly what failed, mark `voice` skipped with the
  reason, and carry on.

Then make the automation from the blueprint, in a package so it is tracked and
easy to remove (after checking that `configuration.yaml` loads packages; AGENTS.md
says how). The command writes it, with the name:

```bash
housemate-voice write-package "<the name>" "notify.mobile_app_<their phone>"
```

Use the service you kept in step 4, or an empty string if there was none. Commit
the files (`housemate_rest_command.yaml`, the blueprint, `configuration.yaml`, the
package) with a why. Then run the configuration check and tell them the result:

```bash
housemate-onboarding restart-core
```

With no flag it only checks the configuration and, if valid, records that a
restart is pending. It never restarts. If the check fails, fix the cause before
going on.

**Question B, with the question tool: restart Home Assistant now, or later?**
Say what a restart does: Home Assistant is unavailable for about a minute, so
automations do not run, dashboards and the phone app drop out, and anything
running in Home Assistant is interrupted; this panel stays up, and the voice
kick-off does not work until it has happened. Options: restart now
(**recommended**: they have just asked for voice, and it does not work until Home
Assistant has restarted); later (say that voice then waits).

- **Now**: `housemate-onboarding restart-core --yes` restarts, waits until Home
  Assistant has gone away and come back, and clears the pending note. Then
  confirm the action exists:
  `curl -fsS -H "Authorization: Bearer $SUPERVISOR_TOKEN" http://supervisor/core/api/services | jq -e '.[] | select(.domain=="rest_command") | .services.housemate_kickoff'`.
- **Later**: do not restart. Mark the step done with the note `restart pending`
  (`housemate-onboarding step voice done "installed; restart pending"`), tell
  them plainly that voice will not work until Home Assistant is restarted, and
  how: ask you ("restart Home Assistant"), or Settings, System, Restart. The
  pending restart shows in `housemate-onboarding status`; mention it again in
  the closing summary.

Never run `restart-core --yes`, or any other restart of Home Assistant, without
a yes to Question B in this conversation. (Recommending "now" is because they have
just asked for something that works only after it. A restart you propose for
any other reason recommends "later".)

Once the voice kick-off is installed **and Home Assistant has been restarted**
(if the restart is pending, skip this part and say it is waiting on the restart),
tell them three things, briefly:

1. **A trial that builds something real.** Do not suggest a "say hello" test.
   Suggest one sentence to type into Assist (the chat icon in Home Assistant, or
   by voice), starting with the name they chose ("Housemate, ..." by default), asking for a common, useful automation
   made from their own house as the cheat sheet now describes it: a night light
   from a real light and a motion or presence sensor, a reminder to their phone,
   an away mode that switches off named lights, and so on, naming real entities in
   their words. Pick one that is **not** the one you will build together in step 7
   (keep the best idea for step 7), and say so. With a near-empty house, suggest a
   reminder to their phone.
2. **Where the job appears.** The job is a chat in this panel. The panel opens on
   the newest one by itself; the **Chats** button in the status bar lists the
   others, and typing `/sessions` in OpenCode does the same.
3. A request spoken from a satellite that cannot tell who is speaking, or from
   someone who is not an administrator, does not run: it waits in this chat for an
   administrator to say go.

## 7. A first automation, together  (`automation`)

This is the point of it all. Ask what small thing they would like their house to
do. If they have nothing in mind, offer two or three from their own cheat sheet
in their words ("turn the lounge lamp on at sunset?", "tell you when the washing
machine finishes?") and let them pick. Then build it the Housemate way, with the
`orchestrator` skill: load it with the skill tool before you start, and follow it, so they meet the sizing from the
start (a plainly small request is just done, with no question). Keep the example
small enough to finish in this conversation.

Build it the way step 6 did: **its own file**, `packages/<topic>.yaml`, holding a
top-level `automation:` list with the one automation in it. Packages are already
switched on in `configuration.yaml`; leave that file and every other file as
they are. Never merge it into another package, never delete or rewrite
`packages/housemate_voice.yaml`, and never replace the `packages:` line. If
packages were not switched on (step 6 was skipped), add the one line AGENTS.md
describes and nothing else.

The step is done only when `scripts/check-config.sh` is valid, you have reloaded
(`POST http://supervisor/core/api/services/automation/reload`) and seen the new
automation in the API (`GET .../api/states/automation.<its id>` answers, and the
voice kick-off is still listed if step 6 ran), you have shown it working (trigger
it with `automation.trigger` if it is safe to, otherwise say exactly when it will
fire), and it is **committed** with a message that says why. Show them the
commit (`git -C /config log --oneline -3`) and tell them how to undo it: "ask me
to undo the last change".

## Finish

Run `housemate-onboarding status` and tell them, in a few lines: what is set up,
what was skipped and how to do it later, and that they can say "run onboarding"
to repeat any step. Remind them of the three habits that make Housemate safe:
they can ask for anything, everything is committed, and anything can be undone.
If git is in, make sure nothing is left uncommitted.

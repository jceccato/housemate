---
name: onboarding
description: Walk the user through Housemate's setup - provider and model, git for /config, a scan of their house into the cheat sheet, the phone to notify, an optional private remote, the voice blueprint, and a first small automation. Use on the first conversation in a fresh install (`housemate-onboarding status` says `new`), and whenever the user asks to run, repeat or continue onboarding or setup, or to redo one of its steps.
---

# Onboarding

You are meeting a person who may know nothing technical. In about ten minutes
you set Housemate up with them and build one small automation together, so they
see how it works. Be warm and brief: this is read on a phone as often as on a
desktop. Short messages, plain words, no jargon without a half-sentence of why.

## Ground rules

- **One thing at a time.** Say which step this is ("Step 3 of 7: your house"),
  what it is for in one sentence, then do it or ask. Use the question tool for
  choices when you have it, and plain words when you do not; give the option you
  recommend first. After a question, stop and wait for the answer.
- **Every step can be skipped**, and the user may stop at any point. A skipped
  step is not a failure: record it and move on. Offer "skip" every time; do not
  argue.
- **Record each step as it settles**, so a re-run knows where things stand:
  `housemate-onboarding step <name> done|skipped "<a few words>"`. The names, in
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
  line each (the seven steps below), that it takes about ten minutes, and that
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
jq -r '.provider' /data/options.json
jq -r '(.api_key // "") | length > 0' /data/options.json
```

You are answering them, so the provider is working. Tell them: which provider
(`go` is OpenCode Go, `zen` is OpenCode Zen), whether a key is set (Zen's free
models need none), and which model you are running as. Say that a different
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

Keep the service name (`notify.mobile_app_<name>`) in `memory/phone-to-notify.md`
(one fact, with a line in `memory/MEMORY.md`), because the voice step and the
update review use it. Mark the step done.

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
for the hall") and a job starts in this chat; their phone buzzes when it needs
them or is done. It adds an automation, a small file and a line in
`configuration.yaml`, and Home Assistant restarts once (about a minute; this
panel stays up). Ask for their OK. If no, mark `skipped`.

On a yes:

```bash
housemate-voice-install
```

- Exit 0: installed, or already there.
- **Exit 3**: they already have a `rest_command:` of their own in
  `configuration.yaml`, and nothing was changed. Do not touch theirs without
  asking. Show them the entry in `/config/housemate_rest_command.yaml` and offer
  to add it to their existing `rest_command:` (a merge by hand, with their yes),
  keeping everything of theirs. Then continue.
- Any other failure: say plainly what failed, mark `voice` skipped with the
  reason, and carry on.

Then make the automation from the blueprint, in a package so it is tracked and
easy to remove (`packages/housemate_voice.yaml`, after checking that
`configuration.yaml` loads packages; AGENTS.md says how):

```yaml
automation:
  - id: housemate_voice_kickoff
    alias: Housemate voice kick-off
    use_blueprint:
      path: housemate/voice_kickoff.yaml
      input:
        notify_service: notify.mobile_app_<their phone>   # "" if no phone
```

Use the service you kept in step 4, or an empty string if there was none. Then
`scripts/check-config.sh`; if the check fails, fix it before going further. With
the check passing, restart Home Assistant **once**, and wait for it properly: it
keeps answering for a few seconds after the request, so wait until it has gone
away and come back.

```bash
auth="Authorization: Bearer $SUPERVISOR_TOKEN"
curl -fsS -X POST -H "$auth" http://supervisor/core/restart > /dev/null
sleep 20
for i in $(seq 1 60); do
  curl -fsS -m 5 -H "$auth" http://supervisor/core/api/ > /dev/null 2>&1 && { echo back; break; }
  sleep 5
done
```

Then confirm the action exists:
`curl -fsS -H "Authorization: Bearer $SUPERVISOR_TOKEN" http://supervisor/core/api/services | jq -e '.[] | select(.domain=="rest_command") | .services.housemate_kickoff'`.
Commit the files (`housemate_rest_command.yaml`, the blueprint, `configuration.yaml`,
the package) with a why.

Tell them two things: they can try it by typing "Housemate say hello" into Assist
(the chat icon in Home Assistant), and a request spoken from a satellite that
cannot tell who is speaking, or from someone who is not an administrator, does
not run: it waits in this chat for an administrator to say go.

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

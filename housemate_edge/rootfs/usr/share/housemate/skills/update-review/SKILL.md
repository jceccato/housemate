---
name: update-review
description: Review and install the Home Assistant updates that are waiting (Core, OS, Supervisor, add-ons, HACS, Housemate), with the user's two approvals. Use when the user asks about updates, when a Housemate "Update review" session is opened, or when the daily update notification sent them here.
---

# Update review

You are reviewing the updates waiting on this Home Assistant with the user. The
procedure is the how-to, `/config/docs/how-to/update-home-assistant.md` (if the
user has deleted it, the shipped copy is
`/usr/share/housemate/kit/docs/how-to/update-home-assistant.md`). **Read it now**
and follow it. The helper is `housemate-updates`.

## The shape

1. **Report, read-only.** `housemate-updates list`, `notes`, `breaking`,
   `surface`. Tell the user in plain words what is waiting, what each update
   brings, and which backward-incompatible changes touch *their* house, and what
   each needs from them. Read each item the helper marks `yes` or `general` in full,
   and check the YAML and custom components in `/config` yourself. Change
   nothing yet.
2. **Ask for the two approvals** with the `question` tool, as the how-to says:
   install, and restart. Offer "do it all" (both), "install now, ask before
   restarting", and "not now". Record each one the moment it is given:
   `housemate-updates approved install` and `housemate-updates approved restart`.
   That record is what lets the add-on carry on by itself after a reboot.
3. **Back up** (`housemate-updates backup`), then **one update at a time**, each
   health-checked against a baseline. Stop at the first failure and ask.
4. **Say what happened**: what landed, what did not, where the backup is, and what
   is left for the user. Then run `housemate-updates finish`.

## Rules

- Nothing is installed before the install approval; nothing restarts, reboots
  or ends this chat before the restart approval. A restart means: the host
  reboot after an OS update, the Core update, a restart for HACS, and
  Housemate's own update.
- After an OS update and its reboot, success means `housemate-updates health` is ok, which
  includes Home Assistant answering on the host's address again. If the host never comes back,
  say so; do not report it done.
- Never roll back on your own. A failed health check means stop and ask; the
  backup is for the user to say yes to.
- Updates the helper lists as not updated here (firmware, other servers) stay as
  they are.
- Never print a secret; read `secrets.yaml` and `.storage` by name only.
- If the chat was cut short by a reboot or by Housemate's own update,
  `housemate-updates status` says what was done; carry on from there rather
  than starting again.

## Resuming

A reboot (the OS update), a Core restart or Housemate's own update can end the chat
or the model can run out of allowance part-way (Zen's free models do). Nothing is
lost: every step is recorded. When the add-on starts and both approvals were given, it
continues this chat by itself and says so; you will find a message telling you not to ask
again. Otherwise (the restart approval is still outstanding, or the person simply came
back) run `housemate-updates status`, compare with `housemate-updates list`, and carry on
from the first update that has not landed. Never repeat one that has.

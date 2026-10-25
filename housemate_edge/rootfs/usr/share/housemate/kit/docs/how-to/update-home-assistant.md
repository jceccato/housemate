# Update Home Assistant

How to bring everything with an update waiting up to date: the Supervisor, the
operating system, Core, add-ons, HACS integrations and cards, and Housemate
itself. The `update-review` skill runs this with the user. It is yours to edit:
add what you learn about this house (an integration that always needs a restart,
an add-on to leave alone).

Updates are where a Home Assistant gets hurt, so the rule is: **read first,
back up, one at a time, check after each, ask twice.**

## The commands

`housemate-updates` is the helper (it prints JSON; the token is already in the
environment):

| Command | What it does |
| --- | --- |
| `list` | What is waiting, in the order to install it |
| `surface` | What in this house release notes can touch: integrations in use, YAML keys, custom components, add-ons (names only) |
| `notes` | Release notes between the installed and target version of each update |
| `breaking` | Core's "Backward-incompatible changes" for every monthly release crossed, each marked against this house |
| `baseline --out F` | Versions, open Repairs, error-log signatures, unavailable entities, automations on |
| `backup` | One full backup named `pre-updates-<date>`, read back and checked |
| `install ID` | One update, then wait until it has landed |
| `reboot` | Reboot the host (after an OS update) |
| `health --baseline F` | Compare now with the baseline |
| `status` | What this review has already done today |

## 1. The read-only report

Change nothing. Report:

- what is waiting (`list`), and what is not updated at all (device firmware,
  radio firmware, other servers' versions: listed, never updated);
- for each update the release notes between installed and target (`notes`). Read
  every release crossed, not only the latest: Core can jump several months;
- Core's backward-incompatible changes (`breaking`), then **read the ones marked
  `yes` and `general` in full** and say what each needs from the user in this
  house. An item marked `no` is for an integration this house does not use.
  Also check the items against YAML in `/config` (templates, automations,
  packages) and custom components, which the marking cannot see; `surface`
  lists them. Secrets are read by name only;
- custom integrations (HACS): does a new Core still support each one? A release
  more than a year old deserves a look for an issue naming the new Core. If one
  needs a newer Core than the target, leave Core where it is and say so;
- anything that needs a decision only the user can make: stop and ask before
  that update.

## 2. The two approvals

Ask with the `question` tool, so a notification reaches the user's phone.

1. **Install**: back up, then install these updates one at a time (list them,
   with the breaking changes that apply).
2. **Restart**: anything that interrupts Home Assistant or this chat: the host
   reboot after an OS update, the Core update (Core restarts), a restart for
   HACS integrations, and Housemate's own update (this chat ends and the add-on
   starts again).

The user may give both at the start ("do it all"), or leave the restart to be
asked at the moment it comes. Never install before the first, never restart
before the second.

## 3. Back up, once

`housemate-updates backup`, before the first update. Check its answer says
`ok`: a full backup, with Home Assistant in it. Say where it is and that it is
not deleted by the review.

## 4. One update at a time

Take a baseline first (`baseline --out /config/.housemate/updates/<date>/baseline.json`).
Then, in the order `list` gives (Supervisor, operating system, Core, the
database add-on on its own, other add-ons, HACS, Housemate last), for each:

1. `install <entity_id>`; wait for it to land;
2. `health --baseline <file>`;
3. on a failure, **stop**, say what failed. Never roll back on your own: ask
   first, and offer the backup.

With only the install approval, do the updates that interrupt nothing first
(add-ons, HACS files, the Supervisor, and the OS staged but not rebooted), then
ask for the restart before the rest. The OS update takes effect only after
`reboot`. A Core update, or HACS integrations installed before it, take effect
on Core's restart: run Home Assistant's configuration check
(`scripts/check-config.sh`) before any restart you start yourself.

## 5. Finish

Housemate's own update goes last and ends this chat. Before it, write down for
the user where things stand (what landed, what is left, where the backup is);
after it the add-on starts again and the user can open a fresh chat. `status`
shows what was done today, if the review was cut short by a reboot: carry on
from there.

If kit changes are waiting as incoming, offer the `incoming-review` skill last.

## Gotchas

- GitHub allows 60 unauthenticated calls an hour per address, and Home Assistant
  shares it. `notes` is cheap, but do not run it over and over.
- The unavailable count wanders by tens between reads; the health check allows
  10.
- The log may hold errors that were there before: the health check compares to the
  baseline's set, not to zero.
- Supervisor, some add-ons and the OS may already be current if they update
  themselves.

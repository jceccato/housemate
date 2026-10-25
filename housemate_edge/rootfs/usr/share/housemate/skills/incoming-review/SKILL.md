---
name: incoming-review
description: Review kit changes that a newer Housemate staged as incoming. Use when the user asks about incoming kit changes or an update to the kit, when /config/.housemate/incoming exists, or when `housemate-incoming status` reports something pending.
---

# Incoming review

A newer Housemate carries changes to the starter kit (the user's `AGENTS.md`,
cheat sheet, how-tos, scripts, skills). They are staged in
`/config/.housemate/incoming/` and **nothing has been applied**. Your job is to
review them with the user. The user's files are theirs: change one only after
they have said yes to that change.

## Look first

```bash
housemate-incoming status
cat /config/.housemate/incoming/RELEASE-NOTES.md
jq '.files' /config/.housemate/incoming/manifest.json
```

Tell the user in plain words what the maintainer changed (the release notes),
and how many files fall in each outcome below. For each file:

- `base/<path>` is the text the user was shipped,
- `new/<path>` is the text that ships now,
- `/config/<path>` is what the user has.

## The outcomes

| outcome | meaning | what to do |
| ------- | ------- | ---------- |
| `apply` | the user never changed it (kit changed, kit added a file they have nothing at, or kit removed a file they never changed) | one batch approval |
| `merge` | the kit changed it and so did the user | three-way merge, one file at a time |
| `conflict` | the kit added a file where the user already has their own | show both, ask |
| `review` | the kit removed a file the user changed | ask whether to keep it (default: keep) |
| `user_deleted` | the kit changed a file the user deleted | tell them; restore only if they ask (default: leave it deleted) |
| `converged` | the user's file already equals the new one | nothing to do |

## 1. The batch (`apply`)

List every `apply` file with its change (changed, added, removed) and a
one-line summary of the difference (`diff base/<path> new/<path>`). Ask for **one
approval for the batch**, or let the user take files out of it. Only after a yes:

```bash
housemate-incoming apply-untouched
```

It skips, and says so, any file the user edited after the staging; handle those
as `merge`. If the user took files out of the batch, apply the rest by hand
(copy `new/<path>` over the file; delete a removed file) rather than running
the command.

## 2. The merges (`merge`, `conflict`)

For each file: `diff3`-style, compare `base/<path>`, `new/<path>` and the
user's file. Keep every edit the user made. Take the kit's change where it does
not collide, and where it collides show both versions and ask. Propose the
merged text (show the diff against their current file) and **write it only
after the user approves that file**. A user who says "skip" or "later" leaves
the file as it is.

## 3. Settle it

When every file is applied, merged, kept or deliberately skipped:

```bash
housemate-incoming finish
```

This makes the new kit the base for the next comparison, updates the manifest
and clears incoming. If the user wants to put some files off until later, run
`finish --force` only if they accept that those changes will not be offered
again (the next kit change to that file will be compared against the new base),
otherwise leave incoming in place and finish another day.

## Then

If the user's `/config` is under git, commit what changed with a why that says
which kit version it came from, e.g. `Take kit 2: cheat sheet section, merged
with my edits`. Never print a secret while merging.

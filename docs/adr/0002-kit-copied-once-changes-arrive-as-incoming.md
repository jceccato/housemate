# The kit is copied into /config once; later changes arrive as incoming, never overwriting

The kit (agent rules, cheat sheet, memory, how-tos, scripts, skills) is copied
into the user's `/config` on first open and is theirs from then on. When a later
image carries a different kit, the add-on stages each changed file in an
**incoming** folder with release notes. The agent reviews it with the user by a
three-way comparison (the base that shipped before, what ships now, what the
user has), applies untouched files in one batch approval, and applies nothing
without the user's say-so.

Users customise these files, and the agent itself grows them (the cheat sheet,
memory). Overwriting in place would destroy that work, and a merge done silently
by the add-on would change files under the user unseen. Fixes that must always
reach everyone ride separately as **built-in rules** inside the image, which
update with every release and are not the user's files.

## Considered options

- **Overwrite on update**: rejected, loses the user's edits.
- **Never update the kit**: rejected, users would miss improvements.
- **Silent automatic merge**: rejected, changes arrive unseen.
- **Incoming, reviewed with the user**: chosen.

## Consequences

The add-on must record the base of every shipped kit file, and the incoming
review (a skill) carries the one place with real branching logic.

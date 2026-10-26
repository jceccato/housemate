---
name: orchestrator
description: Size a request as a quick one-off or a bigger piece of work, ask the user "grill it, or yolo?", then do it directly (yolo) or take it through grilling, a spec and tickets in tracker/, worked one ticket at a time by sub-agents (grill). Use when the user asks you to build or change something, or to work through an existing spec and tickets.
---

Big work done carelessly goes wrong in ways a git revert does not fix, and small
work wrapped in ceremony wastes the user's time. This skill is how you tell them
apart, let the user choose, and keep a long job on the rails.

## 1. Size the request

Before building anything the user asked for, decide which it is. Do not ask the
user to size it for you.

**A one-off** is all of these: one thing (an automation, a helper, a script, a
dashboard card, a fix), its entities are known or quickly found, it is easy to
undo with git, and you can finish it in this chat without a question you cannot
answer yourself.

**Worth a grilling** is any of these: several parts that depend on each other;
requirements you would have to guess; many files, an integration or a device
the user has not set up; a change git cannot undo; work that will not fit one
sitting; or the user calls it big, a project, or says "plan".

A one-off with a small doubt is still a one-off: make the sensible choice, say
what you chose, and carry on.

## 2. Ask: grill it, or yolo?

For anything that is not plainly a one-off, ask once, with the `question` tool
(never as a question in plain chat), short enough to read on a phone:

- **Question**: "Grill it, or yolo?" with the request in your words and why it
  looks bigger than a quick job.
- **Options**: "Yolo - I just do it and tell you what I did" and "Grill it - I ask
  you the hard questions first, then we write it up and I work it in steps". Put
  the one you recommend first, labelled "(recommended)", and say why in its
  description. The tool's free-text answer covers anything else.

One question at a time. Ask only what you cannot find out yourself: look in the
cheat sheet, the API and the files first. Wait for the answer.

## 3a. Yolo

Do the work yourself, to the rules in `AGENTS.md`: find entities through the
API, build in a package, run the config check, reload, commit with a why. Then
**finish properly** (section 5). Yolo skips the interview, never the checks.

## 3b. Grill

1. **Name the command; do not run it.** Tell the user to type
   `/grill <the idea in a sentence>` themselves. The grilling, `/to-spec` and
   `/to-tickets` are commands only the user starts: never start one yourself,
   never load the `grilling` skill to hold the interview on the user's behalf,
   and never answer a grilling's questions in the user's place. (When the user
   has typed the command, the message you receive is the command's own text:
   follow it. That is the user starting it.)
2. Say up front what follows the grilling: the user types `/to-spec` (writes
   `tracker/<feature>/spec.md`) and then `/to-tickets` (writes
   `tracker/<feature>/issues/NN-<slug>.md`).
3. When they come back and say to go, or when they ask you to work an existing
   spec, **work the tickets** (section 4).

If the user declines the grilling after all, that is yolo: say so and do it.

## 4. Work the tickets, one at a time

Read the spec once. List the tickets with their `Status:` and `Blocked by:`
lines. The **frontier** is every ticket that is `ready-for-agent` or `ready-for-human`
(a gate, below), and whose blockers are `resolved`. Take the lowest number. Show the
user the order in a line or two, then start. Keep to the frontier: you hold the
spec and one line per outcome, and the sub-agents hold the detail.

For each ticket, in turn:

1. **Claim it.** Set the ticket's status line to `claimed` (keep the form the
   ticket already uses) and commit that by path.
2. **Hand it to a sub-agent**, with OpenCode's `task` tool (a general sub-agent),
   one at a time. Its brief carries: the ticket's path and the spec's path; to
   read `AGENTS.md` first; to build what the ticket's "What to build" says,
   as amended by any later comment headed **Amended brief**; to verify each
   acceptance criterion by running it, not by reading the code; to use the
   `tdd` skill where the work is code; to commit by path with a message that
   says why; to tick each criterion or give a one-line reason; to set the
   ticket's `Status:` to where it landed and write a short **Outcome** comment;
   and to stop at a gate (below) and report instead of working round it.
3. **Read its report, not its transcript.** Check the criteria and the commit
   hashes it names. If something is not done, send it back with what is missing.
4. **Review.** Once the ticket's work is committed, run the `code-review` skill
   with the parent of the ticket's first commit as the fixed point, naming the
   commits to judge. Have the sub-agent (or a new one) commit the fixes it calls
   for.
5. **Close the ticket**: status `resolved`, committed by path. Then the next.

### Gates

A **gate** is a step only the user can take: signing in to a service, a secret
only they hold, pressing a physical button, a device only they can reach, a
choice that is theirs to make. A ticket with a gate runs up to the gate, then
stops. Prepare the exact value, command or screen so the gate is a paste and a
confirmation, then ask the user with the `question` tool, as in section 2: what you
will do, what they will notice, and a clear yes/no (or the choices) to reply with. Wait. Never guess past a gate
and never do the user's part for them. A ticket whose gate is clear from the start is `ready-for-human`: still worked
up to its gate, with the user beside you.

## 5. Finish properly

After the work is committed and available, in yolo and at the end of a grilled
effort alike:

1. **Review your own work.** Read the diff as if it were someone else's: is it
   what was asked, is anything half done, did a secret slip in? In a grilled
   effort, check the spec's user stories one by one against what now exists.
2. **Update your documents for next time**: new entities and quirks into
   `docs/cheat-sheet.md`, lasting facts into `memory/` (one fact per file, with
   a line in the index), anything you worked out the hard way into
   `docs/how-to/`.
3. **Script what you repeat**, as `AGENTS.md` says: a repeated job becomes a
   script in `scripts/` or an automation.
4. **Close the spec.** Set the spec's status to done (a line at its top), with
   what was built and what was left out, and commit.
5. **Tell the user** in a few plain lines: what now works, how to undo it, and
   anything waiting on them.

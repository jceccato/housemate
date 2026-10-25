# Tracker

Bigger work is tracked here as markdown. Nothing leaves this folder unless you
link a GitHub repository and choose GitHub Issues instead (`/setup-matt-pocock-skills`).

```
tracker/<feature-slug>/spec.md                what the work is and why
tracker/<feature-slug>/issues/NN-<slug>.md    one file per ticket, numbered from 01
```

Each ticket starts with a `Status:` line (one of the triage labels in
`docs/agents/triage-labels.md`, or `claimed` and `resolved` while it is worked)
and a `Blocked by:` line, and keeps its discussion under a `## Comments`
heading at the bottom. `docs/agents/issue-tracker.md` has the full conventions.

Change the status as work moves and commit the change. For anything bigger
than a quick change, write the spec first (`/to-spec`), then the tickets
(`/to-tickets`), then do them one at a time.

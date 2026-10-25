# AGENTS.md

Housemate is a public, MIT-licensed Home Assistant add-on repository: an agent
(OpenCode in code-server, behind Ingress) that lives in Home Assistant and
builds it with the user. Read [README.md](README.md) for what it is and
[GLOSSARY.md](GLOSSARY.md) for the words used here.

## Layout

The add-on folders, kit, CI and docs arrive with later work. Today the
repository holds the community files, `GLOSSARY.md`, `docs/adr/` and
`docs/agents/`. Two add-ons will live side by side: `housemate` (stable) and
`housemate_edge` (edge).

## Rules

- **This repository is public.** Nothing in it may name a private host, address,
  person's house, or anything specific to the maintainer's own home. The kit is
  generic.
- **No secrets, ever**: no token, key, password or `secrets.yaml` content in a
  file, a commit message, an issue, a log or a transcript. Secrets are read by
  name only.
- **Commits** are short imperative sentences, with a body when the reason is not
  obvious. Commit as you go, by path; do not sweep up files you did not write.
- **Images are never overwritten.** An image tag is pushed before the version
  that names it.
- **Settled decisions** are in `docs/adr/`. If your work contradicts one, say so
  explicitly rather than overriding it.
- **Support is best-effort**; do not write a promise the project cannot keep.
- "Home Assistant" is Nabu Casa's mark: it stays out of the product name.

## Agent skills

### Issue tracker

Issues live in this repository's GitHub Issues, with a GitHub Project as the
board. See `docs/agents/issue-tracker.md`.

### Triage labels

The five canonical labels, unchanged. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `GLOSSARY.md` and `docs/adr/` at the repo root. See
`docs/agents/domain.md`.

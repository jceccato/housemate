# AGENTS.md

Housemate is a public, MIT-licensed Home Assistant add-on repository: an agent
(OpenCode in code-server, behind Ingress) that lives in Home Assistant and
builds it with the user. Read [README.md](README.md) for what it is and
[GLOSSARY.md](GLOSSARY.md) for the words used here.

## Layout

- `repository.yaml`, the add-on repository's manifest, and `housemate_edge/`,
  the edge add-on (config, `Dockerfile`, `rootfs/` services, `DOCS.md`,
  `CHANGELOG.md`).
- `tests/seam_a/`: the container tests, run from outside (see its harness).
  `HOUSEMATE_IMAGE=<image> python3 -m unittest discover -s tests/seam_a -v`.
  `test_mutants.py` breaks the image on purpose to prove the tests can fail.
- `.github/workflows/`: `tests.yml` (pull requests, and the gate the publish
  workflow calls), `publish-edge.yml` (main: build both architectures, push the
  images, then tag and bump edge's version and changelog), `promote.yml` (by
  hand: edge build to stable) and `renovate-pins.yml`. The logic they call is in
  `.github/scripts/`, tested by `tests/pipeline/`
  (`python3 -m unittest discover -s tests/pipeline`). `renovate.json` configures
  Renovate. The whole flow is in `docs/update-pipeline.md`.
- **Do not bump `version` in `housemate_edge/config.yaml` or write its
  `CHANGELOG.md` entry by hand**: the publish workflow does both after the image
  is pushed. `housemate/` (stable) is written only by the promotion workflow.
- Kit, docs and the remaining CI arrive with later work. Two add-ons live
  side by side: `housemate` (stable, from the first promotion) and
  `housemate_edge` (edge).
- `THIRD_PARTY_NOTICES.md` carries the notices for what is reused.

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

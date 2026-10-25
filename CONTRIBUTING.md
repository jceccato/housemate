# Contributing to Housemate

Thank you for helping. Housemate is early and maintained by one person, so
please keep expectations modest and changes small.

## Before you start

- Read the [README](README.md), the [glossary](GLOSSARY.md) and the
  [ADRs](docs/adr). Settled decisions are not re-argued in pull requests; if you
  think one is wrong, open an issue that says why.
- Search [existing issues](../../issues) first.
- For anything bigger than a small fix, open an issue before writing code.

## Reporting a bug or asking for a feature

Use the issue templates. For a bug, say which add-on (stable or edge), its
version, your Home Assistant version and architecture, and what you expected.
**Never paste an API key, a token or your `secrets.yaml`.** Redact logs first.

## Pull requests

1. Fork, branch from `main`, and keep the change focused.
2. Describe what changed and why; link the issue.
3. Update the docs and the glossary if you add or rename a concept.
4. Make sure CI passes. Once CI exists it builds and smoke-tests both
   architectures.
5. Do not commit secrets, tokens or anything specific to your house.

Commit messages are short imperative sentences ("Pin OpenCode 1.2.3"), with a
body when the reason is not obvious.

## Security

Report vulnerabilities privately; see [SECURITY.md](SECURITY.md).

## Conduct

Everyone taking part follows the [Code of Conduct](CODE_OF_CONDUCT.md).

## Licence

By contributing you agree that your contribution is licensed under the
[MIT licence](LICENSE).

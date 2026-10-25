# Housemate

An agent that lives in Home Assistant and builds it with you.

> **Status: not ready yet.** Housemate is being built. There is nothing to
> install today, and nothing here is stable. Watch the repository if you want
> to know when it is.

Housemate is a Home Assistant add-on. Once it is ready you will add this
repository's URL in the Add-on Store, install "Housemate", and get a panel in
the sidebar where you can ask for automations, helpers, scripts and dashboards
in plain language. The agent works in your `/config` under git, so every change
can be undone.

The plan, in short:

- A sidebar panel (code-server behind Ingress, admins only) with
  [OpenCode](https://opencode.ai) in its terminal and your `/config` open.
- A starter kit of agent rules, a cheat sheet, memory and how-tos, copied into
  `/config` once and yours from then on. Later kit changes arrive as
  **incoming** for you to review; nothing is overwritten.
- Two add-ons from one repository: **Housemate** (stable) and
  **Housemate (edge)**, the newest build, for testers.
- Amd64 and aarch64 images, so a Green, Yellow or Raspberry Pi can run it.
- Your choice of OpenCode Go or OpenCode Zen as the model provider.

## Support

Best-effort. Housemate is maintained by one person in their spare time. Issues
are welcome and read, but there is no promise of a reply time or a fix.

## Contributing and security

See [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md) and the
[Code of Conduct](CODE_OF_CONDUCT.md). The words this project uses are in
[GLOSSARY.md](GLOSSARY.md); the decisions behind it are in [docs/adr](docs/adr).

## Credits

Housemate stands on other people's work:

- [OpenCode](https://github.com/sst/opencode) (MIT), the agent.
- [code-server](https://github.com/coder/code-server) (MIT), the editor in the
  panel.
- The [hassio-addons](https://github.com/hassio-addons) base images (MIT), the
  add-on's base, and
  [Studio Code Server](https://github.com/hassio-addons/app-vscode) (MIT),
  whose add-on patterns Housemate reuses.
- [Matt Pocock's skills](https://github.com/mattpocock/skills) (MIT), the
  engineering skills in the kit.
- [`magnusoverli/opencode`](https://github.com/magnusoverli/opencode)
  (Unlicense), an existing OpenCode add-on, read for inspiration. Housemate
  shares no code with it; see [ADR 0001](docs/adr/0001-build-our-own-add-on.md).

"Home Assistant" is a trademark of Nabu Casa, Inc. Housemate is not affiliated
with or endorsed by it.

## Licence

[MIT](LICENSE).

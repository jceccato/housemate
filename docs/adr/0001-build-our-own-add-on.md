# Housemate builds its own add-on rather than adopting or forking magnusoverli/opencode

The closest existing thing, the community OpenCode add-on `magnusoverli/opencode`
(read 2026-10-23), moves fast under a single maintainer, ships no starter kit of
agent documents and skills, and offers no update path that anyone but its
maintainer can own. We build our own add-on from the start and use that one for
inspiration only.

Its licence is the Unlicense (public domain), so we are free to read it and
learn from it, and we owe it no notice; we credit it anyway in the README.
Adopting it would tie Housemate's behaviour to a moving upstream we do not
control. Forking it would give us its code without its release process, and we
would still have to build the kit, the update path and the CI ourselves.

## Considered options

- **Adopt it as-is** and layer a kit on top: rejected, since any upstream change
  could break the kit and the update path would be the upstream's.
- **Fork it**: rejected, since we would carry its code and its pace without
  owning its design.
- **Build our own, using it for inspiration**: chosen.

## Consequences

Housemate owns its image, its release channels (stable and edge) and its
Renovate-driven update flow, and takes on the maintenance that comes with them.

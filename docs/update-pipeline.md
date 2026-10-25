# The update pipeline

How a new OpenCode, code-server or base image release becomes an update on
the stable add-on, with nobody tracking releases by hand.

```
Renovate PR --> CI (Seam A, both architectures) --> merge to main
  --> publish-edge: plan a version, push both images, tag, then bump
      housemate_edge/config.yaml and CHANGELOG.md
  --> edge users see the update
  --> (by hand) Promote edge to stable: copy the images, write housemate/,
      create a GitHub Release with the notes
```

## Two add-ons, one repository

| Folder | Slug | Images | Version comes from |
| ------ | ---- | ------ | ------------------ |
| `housemate_edge/` | `housemate_edge` | `ghcr.io/jceccato/{arch}-housemate-edge:<version>` | the publish workflow, on every merge |
| `housemate/` | `housemate` | `ghcr.io/jceccato/{arch}-housemate:<version>` | the promotion workflow, when started by hand |

The Supervisor pulls the tag equal to the add-on's `version`; there is no
`latest`. `housemate/` has no Dockerfile: its image is edge's, copied. The
folder does not exist until the first promotion, so the store never lists a
stable add-on with no image behind it.

## What a merge to main does (`publish-edge.yml`)

1. **test**: the same workflow the pull request ran (`tests.yml`).
2. **plan** (`.github/scripts/release.py plan`): if the version in
   `config.yaml` already has both images, publish the next patch version that
   has none. If it has none (someone bumped it by hand), publish it as it is, and
   fail closed without its `## <version>` entry in `CHANGELOG.md`.
3. **build**: push `amd64` and `aarch64` images tagged with that version. A tag
   that exists is skipped, never overwritten.
4. **release**: tag the built commit `edge-<version>`, then write the version
   into `config.yaml` and a `## <version>` entry into `CHANGELOG.md` (the commit
   subjects since the previous build), and push to main. The commit says
   `[skip ci]`.

The image comes before the version that names it, so a store refresh never sees
a version with no image. Publishes run one at a time, so two merges cannot
choose the same version. **Do not bump edge's version or write its changelog by
hand**; merge your change and the pipeline does both. To say more than the
commit subjects do, you can edit the `## <version>` entry after the pipeline
has written it. A version bumped by hand is still published as it stands (and
fails closed without its entry), but it reaches main before its image, so
don't.

A version with an image on only one architecture (a build that failed half way)
is spent: the next publish takes the next number, so a tag is never completed
from a different commit. The half-pushed images are harmless and are never
promoted.

## Promotion (`promote.yml`)

Actions > Promote edge to stable > Run workflow. Leave the version empty for the
newest edge build, or name one. It fails, having pushed nothing, unless:

- edge has images for the version on both architectures and an `edge-<version>` tag;
- edge's `CHANGELOG.md` has a non-empty entry for it (the notes);
- the version is newer than stable's, and stable has no image with that tag.

If the run stops after the images are copied but before `housemate/` is
committed, stable has an image with no folder and a rerun is refused (a tag is
never overwritten): finish by hand.

Then it copies the images to the stable names, writes `housemate/` from the
files at the `edge-<version>` commit (name, slug and image renamed; blocks in
`DOCS.md` between `<!-- edge-only -->` and `<!-- /edge-only -->` dropped), adds
one stable changelog entry gathering every edge entry since stable's last
version, and creates the GitHub Release `v<version>` with that entry as its notes.
Stable's version number is the edge build's.

## Renovate

The Mend Renovate app (free for public repositories), configured in
`renovate.json`:

- OpenCode and code-server: an annotation comment above the Dockerfile `ARG`
  (`# renovate: datasource=github-releases depName=... extractVersion=...`).
  Any other pin gets the same comment and is picked up.
- The base image (`ARG BUILD_FROM=image:tag@digest`), the Debian packages pinned
  in the Dockerfile as `name=version`, and the workflow actions.
- A vendored repository pinned by commit: put
  `# renovate: git-refs <repo url> <branch>` above `NAME=<40 hex>` in any file under `housemate_edge/`.
- Minor, patch and digest updates automerge once the required checks pass. A
  major (OpenCode v2) is labelled `major` and waits for a person.
- Renovate cannot update the `SHA256` pins beside a version. `renovate-pins.yml`
  recomputes them from the downloads on Renovate's pull request
  (`pin_checksums.py`) and pushes to the branch; CI then runs on the corrected head.
  After changing a version by hand, run `python3 .github/scripts/pin_checksums.py housemate_edge/Dockerfile`.
- The Matt Pocock skills revision is pinned in the Dockerfile as
  `MATT_SKILLS_REVISION`, under `# renovate: git-refs https://github.com/mattpocock/skills main`,
  so Renovate proposes each new upstream commit. The build checks the shipped
  skill/command split against upstream's `disable-model-invocation` flags and fails
  if they disagree, so a bump that flips a flag stalls its automerge by design: a
  person updates the split, then merges.
- The OpenCode editor extension (`OPENCODE_EXTENSION_VERSION`) is not tracked.

## What the repository needs (the maintainer's settings)

- The Renovate app, installed on this repository only.
- **Settings > General > Pull Requests > Allow auto-merge.**
- A ruleset on `main` that requires the checks `Seam A (amd64)`,
  `Seam A (aarch64)` and `Pipeline scripts`, with the maintainer's account able
  to bypass it (whoever pushes to main directly, such as an agent, does so as that account).
- The Actions secret `RELEASE_TOKEN`: a fine-grained token on this repository
  with Contents: read and write (and Pull requests: read and write), of a user who
  can bypass the ruleset. The pipeline pushes its version bump, the promotion
  and the checksum fixes with it, and a push made with it starts the CI that
  automerge waits for. Without the secret the bump and promotion fall back to
  the workflow token, which works only while `main` is unprotected, and
  `renovate-pins.yml` stops with an error.

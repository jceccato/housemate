# Testing

## Seam A: the container tests

Seam A starts the add-on image the way the Supervisor does and asserts what a
user would see from outside. It needs Docker and `pyyaml`.

```bash
# Build the image under one tag (reusing the tag, removing the image it replaced).
old=$(docker images -q housemate-edge:dev)
docker build -t housemate-edge:dev housemate_edge
[ -z "$old" ] || [ "$old" = "$(docker images -q housemate-edge:dev)" ] || docker rmi "$old"

# Run the tests.
HOUSEMATE_IMAGE=housemate-edge:dev python3 -m unittest discover -s tests/seam_a -v
```

Other suites need no container: `tests/pipeline`, `tests/kit` and
`tests/updates`, each run with `python3 -m unittest discover -s <dir>`.

## Cleaning up

The harness removes what it creates. Every container, network, volume and
mutant image it starts carries the label `housemate.test=1` (and
`housemate.test.run=<id>`, `housemate.test.started=<epoch>`), and its names
carry the run id. A run removes its own things when the process exits, whether
the tests passed, failed or were interrupted (Ctrl-C or SIGTERM), including a
container's anonymous volumes. When a run starts it also sweeps runs more than
an hour old.

A run that is killed outright (SIGKILL, a power cut) cannot clean up after
itself. Its leftovers go at the next start, or on demand:

```bash
python3 tests/seam_a/cleanup.py                 # runs older than an hour
python3 tests/seam_a/cleanup.py --older-than 0  # every labelled run, whatever its age
python3 tests/seam_a/cleanup.py --dry-run       # list what would go
```

The sweep removes only what carries the label (and the scratch directories
named `housemate-seam-a-*` in the temp directory), so it is safe on a Docker
host shared with other projects. A run that takes more than an hour would be
swept by another run starting meanwhile.

The sweep does not touch the image you build to test, and Docker's build cache
is not labelled, so it grows with every local build; trim it with
`docker builder prune --filter until=24h`.

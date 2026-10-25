#!/usr/bin/env python3
"""Recompute the Dockerfile's release checksums after a version bump.

Renovate changes OPENCODE_VERSION or CODE_SERVER_VERSION; the SHA256 ARGs beside
them still describe the old release, so the build would fail its own check.
This downloads each pinned asset and writes its real checksum, so the pull
request that Renovate opened can pass CI. The checksum is computed from the
download and committed, which is what pinning means; it is not read from the
same server at build time.

    pin_checksums.py housemate_edge/Dockerfile
"""

import hashlib
import pathlib
import re
import sys
import urllib.request

OPENCODE = "https://github.com/anomalyco/opencode/releases/download/v{v}/{asset}"
CODE_SERVER = "https://github.com/coder/code-server/releases/download/v{v}/code-server-{v}-linux-{arch}.tar.gz"
EXTENSION = "https://open-vsx.org/api/sst-dev/opencode/{v}/file/sst-dev.opencode-{v}.vsix"

# (checksum ARG, version ARG, url template)
PINS = [
    ("OPENCODE_SHA256_AMD64", "OPENCODE_VERSION", OPENCODE.replace("{asset}", "opencode-linux-x64-baseline.tar.gz")),
    ("OPENCODE_SHA256_AARCH64", "OPENCODE_VERSION", OPENCODE.replace("{asset}", "opencode-linux-arm64.tar.gz")),
    ("CODE_SERVER_SHA256_AMD64", "CODE_SERVER_VERSION", CODE_SERVER.replace("{arch}", "amd64")),
    ("CODE_SERVER_SHA256_AARCH64", "CODE_SERVER_VERSION", CODE_SERVER.replace("{arch}", "arm64")),
    ("OPENCODE_EXTENSION_SHA256", "OPENCODE_EXTENSION_VERSION", EXTENSION),
]


def arg(text, name):
    m = re.search(rf"^ARG {name}=(\S*)$", text, re.M)
    if not m:
        sys.exit(f"::error::Dockerfile has no 'ARG {name}='; teach pin_checksums.py")
    return m.group(1)


def pin(text, sha_of):
    for sha_arg, ver_arg, template in PINS:
        arg(text, sha_arg)
        url = template.format(v=arg(text, ver_arg))
        text = re.sub(rf"^(ARG {sha_arg}=)\S*$", lambda m, s=sha_of(url): m.group(1) + s, text, flags=re.M)
    return text


def sha256_of_url(url):
    h = hashlib.sha256()
    with urllib.request.urlopen(url, timeout=300) as r:
        while chunk := r.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()


if __name__ == "__main__":
    path = pathlib.Path(sys.argv[1])
    path.write_text(pin(path.read_text(), sha256_of_url))

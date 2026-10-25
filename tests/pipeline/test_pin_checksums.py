import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / ".github" / "scripts"))

import pin_checksums  # noqa: E402

DOCKERFILE = """\
FROM x
# renovate: datasource=github-releases depName=anomalyco/opencode extractVersion=^v(?<version>.+)$
ARG OPENCODE_VERSION=1.20.0
ARG OPENCODE_SHA256_AMD64=old1
ARG OPENCODE_SHA256_AARCH64=old2
# renovate: datasource=github-releases depName=coder/code-server extractVersion=^v(?<version>.+)$
ARG CODE_SERVER_VERSION=4.150.0
ARG CODE_SERVER_SHA256_AMD64=old3
ARG CODE_SERVER_SHA256_AARCH64=old4
ARG OPENCODE_EXTENSION_VERSION=1.0.0
ARG OPENCODE_EXTENSION_SHA256=old5
"""


class Pin(unittest.TestCase):
    def test_every_checksum_is_recomputed_from_its_asset_url(self):
        seen = []

        def sha_of(url):
            seen.append(url)
            return "sha-" + url.rsplit("/", 1)[1]

        out = pin_checksums.pin(DOCKERFILE, sha_of)
        self.assertIn("ARG OPENCODE_SHA256_AMD64=sha-opencode-linux-x64-baseline.tar.gz\n", out)
        self.assertIn("ARG OPENCODE_SHA256_AARCH64=sha-opencode-linux-arm64.tar.gz\n", out)
        self.assertIn("ARG CODE_SERVER_SHA256_AMD64=sha-code-server-4.150.0-linux-amd64.tar.gz\n", out)
        self.assertIn("ARG CODE_SERVER_SHA256_AARCH64=sha-code-server-4.150.0-linux-arm64.tar.gz\n", out)
        self.assertIn("ARG OPENCODE_EXTENSION_SHA256=sha-sst-dev.opencode-1.0.0.vsix\n", out)
        self.assertIn("https://github.com/anomalyco/opencode/releases/download/v1.20.0/opencode-linux-x64-baseline.tar.gz", seen)
        # nothing else changed
        self.assertEqual(out.count("\n"), DOCKERFILE.count("\n"))
        self.assertIn("ARG OPENCODE_VERSION=1.20.0\n", out)

    def test_pinning_is_idempotent(self):
        once = pin_checksums.pin(DOCKERFILE, lambda url: "same")
        self.assertEqual(pin_checksums.pin(once, lambda url: "same"), once)

    def test_a_missing_arg_fails_rather_than_pinning_half(self):
        with self.assertRaises(SystemExit):
            pin_checksums.pin(DOCKERFILE.replace("ARG CODE_SERVER_SHA256_AARCH64=old4\n", ""), lambda u: "x")


if __name__ == "__main__":
    unittest.main()

"""The openai-compatible tests must be able to fail: break the image three ways and check they notice."""

import unittest

import harness
import test_openai_compatible
from harness import docker

INIT = "/etc/s6-overlay/s6-rc.d/init-housemate/run"


def failures_with(dockerfile_lines, test_path):
    tag = harness.build_image("oai", dockerfile_lines)
    saved = harness.IMAGE
    harness.IMAGE = tag
    try:
        result = unittest.TestResult()
        unittest.defaultTestLoader.loadTestsFromName(f"test_openai_compatible.{test_path}").run(result)
        return result.failures + result.errors
    finally:
        harness.IMAGE = saved
        docker("rmi", "-f", tag, check=False)


class Mutants(unittest.TestCase):
    def test_a_wrong_base_url_is_caught(self):
        failed = failures_with(
            [f"RUN sed -i 's|baseURL: (.base_url|baseURL: (\"http://nowhere.invalid/v1\" + .base_url|' {INIT}"],
            "WithKey.test_the_provider_config_names_the_endpoint_and_the_model")
        self.assertTrue(failed)

    def test_the_key_in_the_log_is_caught(self):
        failed = failures_with(
            [f"RUN printf '%s\\n' 'bashio::log.info \"key $(jq -r .api_key /data/options.json)\"' >> {INIT}"],
            "WithKey.test_the_key_appears_nowhere_but_the_provider_config")
        self.assertTrue(failed)

    def test_no_check_for_a_missing_model_is_caught(self):
        failed = failures_with(
            [f"RUN sed -i 's|if \\[\\[ -z \"${{model_id}}\" \\]\\]; then|if false; then|' {INIT}"],
            "MissingField.test_a_missing_model_stops_the_add_on_with_a_reason")
        self.assertTrue(failed)


if __name__ == "__main__":
    unittest.main()

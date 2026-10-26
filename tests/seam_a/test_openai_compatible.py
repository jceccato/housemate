"""Seam A: the openai-compatible provider, driven from outside the add-on.

The stand-in Supervisor's language model (fake_supervisor.py, port 8081) plays
the user's OpenAI-style endpoint. The test network is internal (no route out),
so OpenCode answering through it also proves that nothing is fetched at run
time: the provider's SDK package ships inside OpenCode.
"""

import json
import time
import unittest

import harness
from harness import docker, find_secret_everywhere
from test_voice import VoiceAddOn

KEY = "hm-test-key-oai-5c1d9e3b7a2f4086b1c3d5e70912a4c8"
MODEL = "acme/chat-model-1"
BASE_URL = "http://supervisor:8081/v1"
CONFIG = "opencode/config/opencode/opencode.json"


class EndpointAddOn(VoiceAddOn):
    """The add-on on a network with no route out, and no pre-made opencode.json."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        (self.config / "opencode.json").unlink()

    def start(self, wait=True):
        self._write_options()
        docker("network", "create", "--internal", self.network)
        docker("create", "--name", self.stub, "--network", self.network, "--network-alias", "supervisor",
               "-e", "FAKE_DIR=/fake", "-v", f"{self.tmp / 'fake'}:/fake:ro",
               "--entrypoint", "python3", harness.IMAGE, "-u", "/fake_supervisor.py")
        docker("cp", str(harness.ROOT / "tests" / "seam_a" / "fake_supervisor.py"), f"{self.stub}:/fake_supervisor.py")
        docker("start", self.stub)
        self.start_clients()
        self._run_addon()
        if wait:
            self.wait_ready()
        return self

    def model_requests(self):
        out = docker("exec", self.stub, "python3", "-c",
                     "import urllib.request;print(urllib.request.urlopen('http://127.0.0.1/_model_requests').read().decode())").stdout
        return json.loads(out)

    def ask(self, prompt="hello"):
        return self.exec(f"cd /config && timeout 120 opencode run {prompt} < /dev/null", check=False)


def options(**kw):
    return dict({"provider": "openai-compatible", "base_url": BASE_URL, "api_key": KEY, "model": MODEL}, **kw)


class WithKey(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.addon = EndpointAddOn(options(), {"configuration.yaml": "homeassistant:\n"})
        cls.addon.start()

    @classmethod
    def tearDownClass(cls):
        cls.addon.stop()

    def test_the_provider_config_names_the_endpoint_and_the_model(self):
        config = json.loads(self.addon.read_data(CONFIG))
        self.assertEqual(config["enabled_providers"], ["openai-compatible"])
        self.assertEqual(config["model"], "openai-compatible/" + MODEL)
        p = config["provider"]["openai-compatible"]
        self.assertEqual(p["npm"], "@ai-sdk/openai-compatible")
        self.assertEqual(p["options"], {"baseURL": BASE_URL, "apiKey": KEY})
        self.assertIn(MODEL, p["models"])
        self.assertEqual(self.addon.exec(f"stat -c %a /data/{CONFIG}").stdout.strip(), "600")

    def test_opencode_answers_through_the_endpoint_with_the_key(self):
        r = self.addon.ask()
        self.assertIn("Done.", r.stdout, r.stdout + r.stderr)
        seen = self.addon.model_requests()
        self.assertTrue(seen, "the endpoint was never asked")
        self.assertTrue(all(q["model"] == MODEL and q["authorization"] == f"Bearer {KEY}" for q in seen), seen)
        self.assertTrue(all(q["path"] == "/v1/chat/completions" for q in seen))

    def test_the_key_appears_nowhere_but_the_provider_config(self):
        self.addon.ask()
        self.assertEqual(find_secret_everywhere(self.addon, KEY), [])


class WithoutKey(unittest.TestCase):
    """A local server needs no key: the add-on starts, writes none, and OpenCode still answers."""

    @classmethod
    def setUpClass(cls):
        cls.addon = EndpointAddOn(options(api_key=""), {"configuration.yaml": "homeassistant:\n"})
        cls.addon.start()

    @classmethod
    def tearDownClass(cls):
        cls.addon.stop()

    def test_no_key_is_written_and_the_endpoint_still_answers(self):
        config = json.loads(self.addon.read_data(CONFIG))
        self.assertEqual(config["provider"]["openai-compatible"]["options"], {"baseURL": BASE_URL})
        self.assertIn("Done.", self.addon.ask().stdout)


class MissingField(unittest.TestCase):
    def stops_saying(self, opts, expected):
        addon = EndpointAddOn(opts, {"configuration.yaml": "homeassistant:\n"})
        try:
            addon.start(wait=False)
            for _ in range(90):
                if docker("inspect", "-f", "{{.State.Running}}", addon.name).stdout.strip() != "true":
                    break
                time.sleep(1)
            self.assertEqual(docker("inspect", "-f", "{{.State.Running}}", addon.name).stdout.strip(), "false")
            logs = addon.logs()
            self.assertIn(expected, logs)
            self.assertNotIn(KEY, logs)
        finally:
            addon.stop()

    def test_a_missing_base_url_stops_the_add_on_with_a_reason(self):
        self.stops_saying(options(base_url=""), "needs a base_url")

    def test_a_missing_model_stops_the_add_on_with_a_reason(self):
        self.stops_saying(options(model=""), "needs a model")

    def test_a_base_url_without_a_scheme_stops_the_add_on(self):
        self.stops_saying(options(base_url="supervisor:8081/v1"), "must start with http")


class GoAndZenAreUnchanged(unittest.TestCase):
    def test_go_and_zen_write_no_custom_provider(self):
        for provider, pid, model in (("go", "opencode-go", "opencode-go/deepseek-v4.1-flash"),
                                     ("zen", "opencode", "opencode/deepseek-v4.1-flash-free")):
            addon = EndpointAddOn(dict(provider=provider, api_key=KEY, base_url=BASE_URL), {"configuration.yaml": "homeassistant:\n"})
            try:
                addon.start()
                config = json.loads(addon.read_data(CONFIG))
                self.assertEqual(config["enabled_providers"], [pid])
                self.assertEqual(config["model"], model)
                self.assertEqual(config["provider"], {pid: {"options": {"apiKey": KEY}}})
            finally:
                addon.stop()


if __name__ == "__main__":
    unittest.main()

"""Seam A: the voice kick-off endpoint, driven from outside the add-on.

Home Assistant Core is played by a client container on the add-on's network,
and the Supervisor (with Core's service calls and websocket behind it) by
fake_supervisor.py. What is asserted is what Home Assistant, the household and
the network could see: the reply, OpenCode's sessions, the notifications that
were sent, and what is listening where.
"""

import json
import pathlib
import yaml
import time
import unittest

import harness
from harness import AddOn, docker, STUB_IMAGE

FAKE = pathlib.Path(__file__).with_name("fake_supervisor.py")
PORT = 8765
ADMIN = "11111111111111111111111111111111"
MEMBER = "22222222222222222222222222222222"
USERS = [
    {"id": ADMIN, "name": "Admin", "is_owner": True, "is_active": True, "system_generated": False,
     "group_ids": ["system-admin"]},
    {"id": MEMBER, "name": "Member", "is_owner": False, "is_active": True, "system_generated": False,
     "group_ids": ["system-users"]},
]
TARGET = "notify.mobile_app_test_phone"


class VoiceAddOn(AddOn):
    """The add-on with the richer Supervisor stand-in, run by the add-on's own image."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # OpenCode's Zen provider, pointed at the stand-in's language model.
        (self.config / "opencode.json").write_text(json.dumps({
            "model": "opencode/deepseek-v4.1-flash-free",
            "small_model": "opencode/deepseek-v4.1-flash-free",
            "provider": {"opencode": {"options": {"baseURL": "http://supervisor:8081/v1"}}},
        }))

    def _write_options(self):
        (self.data / "options.json").write_text(json.dumps(self.options))
        fake = self.tmp / "fake"
        fake.mkdir(exist_ok=True)
        (fake / "options.json").write_text(json.dumps(self.options))
        (fake / "users.json").write_text(json.dumps(USERS))

    def start(self, wait=True):
        self._write_options()
        docker("network", "create", self.network)
        docker("create", "--name", self.stub, "--network", self.network, "--network-alias", "supervisor",
               "-e", "FAKE_DIR=/fake", "-v", f"{self.tmp / 'fake'}:/fake:ro",
               "--entrypoint", "python3", harness.IMAGE, "-u", "/fake_supervisor.py")
        docker("cp", str(FAKE), f"{self.stub}:/fake_supervisor.py")
        docker("start", self.stub)
        self.start_clients()
        self._run_addon()
        if wait:
            self.wait_ready()
        return self


class Voice(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.addon = VoiceAddOn({"provider": "zen", "api_key": "hm-test-key-0123456789abcdef"}, {"configuration.yaml": "homeassistant:\n"})
        cls.addon.start()
        cls.wait_endpoint()
        cls.warm_up()

    @classmethod
    def tearDownClass(cls):
        cls.addon.stop()

    # -- helpers -------------------------------------------------------------------

    @classmethod
    def client(cls, *args, timeout=60):
        """Run in Core's position on the add-on's network (not the host's, and not another add-on's)."""
        return cls.addon.as_core(*args, timeout=timeout)

    @classmethod
    def warm_up(cls, timeout=300):
        """OpenCode's first model call fetches its provider package: do that before timing anything."""
        a = cls.addon
        deadline = time.time() + timeout
        while time.time() < deadline:
            r = a.exec("curl -s -m 5 -XPOST localhost:4096/session -H 'content-type: application/json' -d '{\"title\":\"warm\"}'", check=False)
            if r.stdout.startswith("{"):
                sid = json.loads(r.stdout)["id"]
                break
            time.sleep(2)
        else:
            raise RuntimeError("OpenCode's server never answered:\n" + a.logs())
        a.exec(f"curl -s -m 5 -XPOST localhost:4096/session/{sid}/prompt_async -H 'content-type: application/json' "
               "-d '{\"parts\":[{\"type\":\"text\",\"text\":\"hello\"}]}'")
        while time.time() < deadline:
            msgs = json.loads(a.exec(f"curl -s -m 5 localhost:4096/session/{sid}/message").stdout or "[]")
            if any(m["info"]["role"] == "assistant" and m["info"].get("time", {}).get("completed") for m in msgs):
                return
            time.sleep(2)
        raise RuntimeError("OpenCode never completed a first model call:\n" + a.logs()[-3000:]
                           + "\n" + json.dumps(msgs)[:3000])

    @classmethod
    def wait_endpoint(cls, timeout=60):
        deadline = time.time() + timeout
        while time.time() < deadline:
            r = cls.client("curl", "-sf", f"http://{cls.addon.name}:{PORT}/healthz")
            if r.returncode == 0:
                return
            time.sleep(1)
        raise RuntimeError("the endpoint never answered:\n" + cls.addon.logs())

    def post(self, body, path="/kickoff"):
        """POST JSON from Core's position: (status, parsed body)."""
        r = self.client(
            "curl", "-s", "-w", "\n%{http_code}", "-H", "Content-Type: application/json",
            "-d", json.dumps(body), f"http://{self.addon.name}:{PORT}{path}",
        )
        text, _, status = r.stdout.rpartition("\n")
        return int(status), json.loads(text) if text.strip() else {}

    def opencode(self, path):
        out = self.addon.exec(f"curl -s http://127.0.0.1:4096{path}").stdout
        return json.loads(out)

    def texts(self, sid):
        return [p["text"] for m in self.opencode(f"/session/{sid}/message") for p in m["parts"] if p["type"] == "text"]

    def calls(self):
        out = docker("exec", self.addon.stub, "python3", "-c",
                     "import urllib.request;print(urllib.request.urlopen('http://127.0.0.1/_calls').read().decode())").stdout
        return json.loads(out)

    def calls_for(self, service, session_id):
        return [c for c in self.calls() if c["service"] == service and session_id in json.dumps(c["data"])]

    def wait_for(self, check, timeout=90):
        deadline = time.time() + timeout
        while time.time() < deadline:
            result = check()
            if result:
                return result
            time.sleep(0.5)
        self.fail("timed out waiting; calls so far: " + json.dumps(self.calls()))

    # -- the endpoint ----------------------------------------------------------------

    def test_an_admins_request_starts_a_session_and_notifies_without_waiting(self):
        started = time.time()
        status, reply = self.post({"text": "build me a night light", "user_id": ADMIN, "notify": TARGET})
        self.assertLess(time.time() - started, 10)
        self.assertEqual(status, 202)
        sid = reply["session_id"]
        self.assertFalse(reply["waiting_for_admin"])

        session = self.opencode(f"/session/{sid}")
        self.assertIn("night light", session["title"])
        self.assertIn("build me a night light", self.wait_for(lambda: self.texts(sid)))

        phone = self.wait_for(lambda: self.calls_for("notify/mobile_app_test_phone", sid))[0]["data"]
        self.assertEqual(phone["data"]["url"], f"/app/local_housemate_edge/{sid}")  # the link names the chat
        self.assertEqual(phone["data"]["url"], phone["data"]["clickAction"])
        persistent = self.calls_for("persistent_notification/create", sid)
        self.assertIn("night light", persistent[0]["data"]["message"])
        # One notification per job: later updates replace it rather than pile up.
        self.assertEqual({c["data"]["notification_id"] for c in persistent}, {f"housemate_{sid}"})
        self.assertIn("local_housemate_edge", persistent[0]["data"]["message"])
        self.assertTrue(all(c["authorized"] for c in self.calls()))

    def test_a_non_admins_request_waits_in_the_chat(self):
        status, reply = self.post({"text": "turn everything off", "user_id": MEMBER, "notify": TARGET})
        self.assertEqual(status, 202)
        self.assertTrue(reply["waiting_for_admin"])
        sid = reply["session_id"]
        # The request is in the chat, and nothing answered it.
        self.wait_for(lambda: self.texts(sid))
        time.sleep(3)
        self.assertEqual(self.opencode("/session/status").get(sid, {"type": "idle"})["type"], "idle")
        self.assertEqual([m["info"]["role"] for m in self.opencode(f"/session/{sid}/message")], ["user"])
        phone = self.wait_for(lambda: self.calls_for("notify/mobile_app_test_phone", sid))[0]["data"]
        self.assertIn("waiting", phone["message"].lower())

    def test_a_request_from_nobody_known_waits_too(self):
        status, reply = self.post({"text": "open the garage"})
        self.assertEqual(status, 202)
        self.assertTrue(reply["waiting_for_admin"])
        status, reply = self.post({"text": "open the garage", "user_id": "33333333333333333333333333333333"})
        self.assertTrue(reply["waiting_for_admin"])

    def test_bad_requests_are_refused(self):
        self.assertEqual(self.post({"text": "   "})[0], 400)
        self.assertEqual(self.post({"nothing": 1})[0], 400)
        self.assertEqual(self.post({"text": "x" * 5000})[0], 400)
        self.assertEqual(self.post({"text": "x"}, path="/nope")[0], 404)

    def test_a_finished_job_sends_another_notification(self):
        status, reply = self.post({"text": "build me something else", "user_id": ADMIN, "notify": TARGET})
        self.assertEqual(status, 202, reply)
        sid = reply["session_id"]
        done = self.wait_for(lambda: [c for c in self.calls_for("notify/mobile_app_test_phone", sid)
                                      if "finished" in c["data"]["title"].lower()])
        self.assertEqual(done[0]["data"]["title"], "Housemate finished")
        self.assertEqual(done[0]["data"]["data"]["tag"], f"housemate_{sid}")
        self.assertTrue(self.calls_for("persistent_notification/create", sid))

    def test_a_job_that_needs_an_answer_sends_another_notification(self):
        _, reply = self.post({"text": "ask me which room the light is for", "user_id": ADMIN, "notify": TARGET})
        sid = reply["session_id"]
        needs = self.wait_for(lambda: [c for c in self.calls_for("notify/mobile_app_test_phone", sid)
                                       if "needs you" in c["data"]["title"].lower()])
        self.assertIn("Which room", needs[0]["data"]["message"])
        self.assertEqual(needs[0]["data"]["data"]["url"], f"/app/local_housemate_edge/{sid}")

    # -- the blueprint and its action -------------------------------------------------

    def install(self):
        return self.addon.exec("housemate-voice-install", check=False)

    def test_the_installer_puts_in_the_blueprint_and_its_action_once(self):
        r = self.install()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Configuration check: valid", r.stdout)
        rest = yaml.safe_load(self.addon.exec("cat /config/housemate_rest_command.yaml").stdout)
        self.assertEqual(rest["housemate_kickoff"]["url"], f"http://local-housemate-edge:{PORT}/kickoff")
        config = self.addon.exec("cat /config/configuration.yaml").stdout
        self.assertEqual(config.count("rest_command: !include housemate_rest_command.yaml"), 1)
        # Again: nothing is duplicated, and a file the user changed stays theirs.
        self.addon.exec("echo '# mine' >> /config/blueprints/automation/housemate/voice_kickoff.yaml")
        self.assertEqual(self.install().returncode, 0)
        self.assertEqual(self.addon.exec("cat /config/configuration.yaml").stdout.count("rest_command:"), 1)
        self.assertIn("# mine", self.addon.exec("cat /config/blueprints/automation/housemate/voice_kickoff.yaml").stdout)

    def test_the_blueprint_listens_for_the_sentence_and_calls_the_action(self):
        class Loader(yaml.SafeLoader):
            pass

        Loader.add_constructor("!input", lambda loader, node: "input:" + loader.construct_scalar(node))
        self.install()
        bp = yaml.load(self.addon.exec("cat /config/blueprints/automation/housemate/voice_kickoff.yaml").stdout, Loader)
        self.assertEqual(bp["blueprint"]["domain"], "automation")
        self.assertIn("notify_service", bp["blueprint"]["input"])
        trigger = bp["triggers"][0]
        self.assertEqual(trigger["trigger"], "conversation")
        self.assertEqual(trigger["command"], "input:phrases")  # the sentences are the automation's, so the name can change
        default = bp["blueprint"]["input"]["phrases"]["default"]
        self.assertTrue(any(c.lower().startswith("housemate ") and "{request}" in c for c in default))
        call = bp["actions"][0]
        self.assertEqual(call["action"], "rest_command.housemate_kickoff")
        self.assertEqual(call["data"]["notify"], "input:notify_service")
        self.assertIn("user_id", call["data"])

    def test_the_voice_name_is_written_into_a_package_that_uses_the_blueprint_and_can_be_renamed(self):
        a = self.addon
        a.exec("rm -f /config/packages/housemate_voice.yaml")
        self.assertIn("Wrote", a.exec("housemate-voice write-package Jarvis notify.mobile_app_test_phone").stdout)
        package = yaml.safe_load(a.exec("cat /config/packages/housemate_voice.yaml").stdout)
        entry = package["automation"][0]
        self.assertEqual(entry["use_blueprint"]["path"], "housemate/voice_kickoff.yaml")
        self.assertEqual(entry["use_blueprint"]["input"]["phrases"], ["Jarvis {request}", "Hey Jarvis {request}"])
        self.assertEqual(entry["use_blueprint"]["input"]["notify_service"], "notify.mobile_app_test_phone")
        self.assertEqual(a.exec("housemate-voice name").stdout.strip(), "Jarvis")
        r = a.exec("housemate-voice check Turn", check=False)
        self.assertEqual(r.returncode, 1)
        self.assertIn("start with", r.stderr)

    def test_the_installer_leaves_a_users_own_rest_command_alone(self):
        addon = VoiceAddOn({"provider": "zen", "api_key": "k"}, {"configuration.yaml": "rest_command:\n  mine:\n    url: http://x\n"})
        self.addCleanup(addon.stop)
        addon.start()
        r = addon.exec("housemate-voice-install", check=False)
        self.assertEqual(r.returncode, 3)
        self.assertEqual(addon.exec("cat /config/configuration.yaml").stdout, "rest_command:\n  mine:\n    url: http://x\n")

    # -- who can reach it --------------------------------------------------------------

    def test_nothing_is_published_on_the_host(self):
        self.assertEqual(docker("port", self.addon.name).stdout.strip(), "")
        config = (pathlib.Path(__file__).resolve().parents[2] / "housemate_edge" / "config.yaml").read_text()
        self.assertNotIn("\nports:", config)

    def test_core_reaches_the_endpoint_and_another_add_on_does_not(self):
        ip = self.addon.ip
        self.assertEqual(self.client("curl", "-sf", f"http://{ip}:{PORT}/healthz").returncode, 0)
        # Its connection is closed unanswered; by name or by address.
        for host in (self.addon.name, ip):
            r = self.addon.other("wget", "-qO-", "-T", "3", f"http://{host}:{PORT}/healthz")
            self.assertNotEqual(r.returncode, 0, host)
            self.assertEqual(r.stdout, "")
        # Nor can it start a job, whatever it claims to be.
        r = self.addon.other("wget", "-qO-", "-T", "3", "--header=Content-Type: application/json",
                             f"--post-data={json.dumps({'text': 'unlock the door', 'user_id': ADMIN})}",
                             f"http://{ip}:{PORT}/kickoff")
        self.assertNotEqual(r.returncode, 0)
        self.assertNotIn("unlock the door", json.dumps(self.opencode("/session")))
        self.assertIn("refused a connection", self.addon.logs())

    def test_the_endpoint_inside_the_add_on_still_answers(self):
        loopback = self.addon.exec(f"curl -s -o /dev/null -w '%{{http_code}}' http://127.0.0.1:{PORT}/healthz").stdout
        self.assertEqual(loopback, "200")

    def test_opencodes_server_is_not_on_the_network(self):
        ip = self.addon.ip
        for who in (self.addon.other, self.addon.as_core):
            if who == self.addon.other:
                r = who("wget", "-qO-", "-T", "3", f"http://{ip}:4096/session")
            else:
                r = who("curl", "-s", "-m", "3", f"http://{ip}:4096/session")
            self.assertNotEqual(r.returncode, 0)
        listening = self.addon.listening()
        self.assertIn("127.0.0.1:4096", listening)
        self.assertNotIn("0.0.0.0:4096", listening)

    def test_the_supervisor_token_is_not_logged(self):
        logs = self.addon.logs()
        self.assertNotIn(self.addon.supervisor_token, logs)


if __name__ == "__main__":
    unittest.main()

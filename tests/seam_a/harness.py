"""Seam A harness: start the add-on image the way the Supervisor does.

The Supervisor gives an add-on four things, and this harness provides each:

* a `/config` (Home Assistant's configuration) and a `/data` (the add-on's own
  state, holding `options.json`), as bind-mounted directories;
* a host named `supervisor`, answering the Supervisor API the base image reads
  its options from (a static file server standing in for it);
* a `SUPERVISOR_TOKEN` in the environment;
* an Ingress port (1337), which the harness publishes on loopback only so the
  tests can reach it.

Everything a test asserts is what a user or the Supervisor could see from
outside the container: files, logs, processes, and what the services answer.
"""

import json
import os
import pathlib
import shutil
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
import uuid

ROOT = pathlib.Path(__file__).resolve().parents[2]
ADDON_DIR = ROOT / "housemate_edge"
IMAGE = os.environ.get("HOUSEMATE_IMAGE", "housemate-edge:dev")
STUB_IMAGE = "busybox:stable"
INGRESS_PORT = 1337


def docker(*args, check=True, input=None, timeout=300):
    """Run a docker command; returns the CompletedProcess (text mode)."""
    return subprocess.run(
        ["docker", *args],
        check=check,
        input=input,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


class AddOn:
    """One add-on instance with its fixture `/config` and `/data`."""

    def __init__(self, options, config_files=None):
        self.id = uuid.uuid4().hex[:10]
        self.options = options
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="housemate-seam-a-"))
        self.config = self.tmp / "config"
        self.data = self.tmp / "data"
        self.www = self.tmp / "www"
        self.network = f"hm-seam-a-{self.id}"
        self.stub = f"hm-supervisor-{self.id}"
        self.name = f"hm-addon-{self.id}"
        self.supervisor_token = f"supervisor-token-{uuid.uuid4().hex}"
        self.config.mkdir()
        self.data.mkdir()
        for name, text in (config_files or {}).items():
            path = self.config / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)

    # -- the Supervisor's side ------------------------------------------------

    def _write_options(self):
        (self.data / "options.json").write_text(json.dumps(self.options))
        served = self.www / "addons" / "self" / "options"
        served.mkdir(parents=True, exist_ok=True)
        (served / "config").write_text(json.dumps({"result": "ok", "data": self.options}))

    def set_options(self, options):
        """Change the options, as the Configuration tab does (restart to apply)."""
        self.options = options
        self._write_options()

    # -- lifecycle ------------------------------------------------------------

    def start(self, wait=True):
        self._write_options()
        docker("network", "create", self.network)
        docker(
            "run", "-d", "--name", self.stub, "--network", self.network,
            "--network-alias", "supervisor",
            "-v", f"{self.www}:/www:ro",
            STUB_IMAGE, "httpd", "-f", "-p", "80", "-h", "/www",
        )
        self._run_addon()
        if wait:
            self.wait_ready()
        return self

    def _run_addon(self):
        docker(
            "run", "-d", "--name", self.name, "--network", self.network,
            "-e", f"SUPERVISOR_TOKEN={self.supervisor_token}",
            "-v", f"{self.config}:/config",
            "-v", f"{self.data}:/data",
            "-p", f"127.0.0.1::{INGRESS_PORT}",
            IMAGE,
        )

    def restart(self):
        """What the Supervisor does on a restart: a new container, same /data."""
        self.logs_before = getattr(self, "logs_before", "") + self.logs()
        docker("stop", "-t", "20", self.name)
        docker("rm", self.name)
        self._run_addon()
        self.wait_ready()

    def stop(self):
        for name in (self.name, self.stub):
            docker("rm", "-f", name, check=False)
        docker("network", "rm", self.network, check=False)
        # Files written by the container are root-owned: remove them from inside.
        docker("run", "--rm", "-v", f"{self.tmp}:/x", STUB_IMAGE, "rm", "-rf", "/x/config", "/x/data", "/x/www", check=False)
        shutil.rmtree(self.tmp, ignore_errors=True)

    # -- what a user or the Supervisor can observe ---------------------------------

    @property
    def port(self):
        out = docker("port", self.name, f"{INGRESS_PORT}/tcp").stdout.split()[0]
        return int(out.rsplit(":", 1)[1])

    def get(self, path, follow=False):
        """GET on the Ingress port: (status, headers, body). No redirects followed unless asked."""
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *a, **k):
                return None

        opener = urllib.request.build_opener() if follow else urllib.request.build_opener(NoRedirect)
        try:
            with opener.open(f"http://127.0.0.1:{self.port}{path}", timeout=10) as r:
                return r.status, dict(r.headers), r.read().decode(errors="replace")
        except urllib.error.HTTPError as e:
            return e.code, dict(e.headers), e.read().decode(errors="replace")

    def wait_ready(self, timeout=120):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if docker("inspect", "-f", "{{.State.Running}}", self.name).stdout.strip() != "true":
                raise RuntimeError("add-on container stopped while starting:\n" + self.logs())
            try:
                if self.get("/healthz")[0] == 200:
                    return
            except (OSError, urllib.error.URLError):
                pass
            time.sleep(1)
        raise RuntimeError("code-server never answered on the Ingress port:\n" + self.logs())

    def logs(self):
        r = docker("logs", self.name, check=False)
        return r.stdout + r.stderr

    def all_logs(self):
        """Logs of every container of this add-on so far, restarts included."""
        return getattr(self, "logs_before", "") + self.logs()

    def exec(self, script, input=None, check=True):
        """Run a bash script in the add-on container, with the service environment."""
        return docker("exec", "-i", self.name, "bash", "-c", script, check=check, input=input)

    def read_data(self, rel):
        """A file under /data, read from inside (it is root's, mode 600 or 700)."""
        return self.exec(f"cat /data/{rel}").stdout

    def data_exists(self, rel):
        return self.exec(f"test -e /data/{rel}", check=False).returncode == 0


def find_secret_everywhere(addon, secret):
    """Where does `secret` appear, other than where it is allowed to?

    Returns a list of human-readable places. The secret is passed to the
    scanners on stdin so that the scan itself leaves it in no command line.
    Allowed places are `/data/options.json` (the Supervisor's own copy of the
    options) and OpenCode's provider config; the harness's Supervisor stand-in
    holds the options too, but it is not part of the add-on.
    """
    allowed = {
        "/data/options.json",
        "/data/opencode/config/opencode/opencode.json",
    }
    found = []

    # 1. Every file the add-on could have written: all of the container's
    # filesystem except the pseudo filesystems and the pristine program
    # directories (/usr/local/lib/code-server, /package), which hold no state.
    r = addon.exec(
        "grep -rlaF -f - /data /config /root /tmp /var /etc /run /home /srv /mnt /opt "
        "/usr/share /usr/local/bin 2>/dev/null; true",
        input=secret + "\n",
    )
    for path in r.stdout.split():
        if path not in allowed:
            found.append(f"file {path}")

    # 2. Every process's command line and environment.
    r = addon.exec(
        "tr '\\0' '\\n' < <(cat /proc/[0-9]*/cmdline /proc/[0-9]*/environ 2>/dev/null) > /tmp/.proc-scan; "
        "grep -c -F -f - /tmp/.proc-scan; rm -f /tmp/.proc-scan; true",
        input=secret + "\n",
    )
    if r.stdout.strip() not in ("", "0"):
        found.append("a process command line or environment")

    # 3. The logs, every start of them.
    if secret in addon.all_logs():
        found.append("the container logs")

    return sorted(set(found))

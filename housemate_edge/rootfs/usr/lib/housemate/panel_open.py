"""Which chat the panel should open in front of the person, when a window starts.

The link in a notification ("Open Housemate") can only open the panel: Home
Assistant gives an app link no room to name a chat. So a job that wants the person
in its chat marks it (kickoff.mark_current), and the panel's launcher asks here,
as the window starts:

  1. a chat marked since the panel last took it: that chat, once;
  2. else, on a first run (onboarding not begun, not declined) and the welcome chat
     not made yet: a chat called "Welcome to Housemate", asked to start onboarding;
  3. else nothing, and the launcher opens its usual chat.

    panel_open.py take      prints the chat id to open, or nothing
"""

import json
import os
import subprocess
import sys
import urllib.request

OPENCODE = os.environ.get("HOUSEMATE_OPENCODE_URL", "http://127.0.0.1:4096")
CONFIG = os.environ.get("HOUSEMATE_CONFIG", "/config")
DATA = os.environ.get("HOUSEMATE_DATA", "/data")
MARK = os.path.join(CONFIG, ".housemate", "current-session")
WELCOME = os.path.join(CONFIG, ".housemate", "welcome-session")
SEEN = os.path.join(DATA, "panel-seen-mark")
TITLE = "Welcome to Housemate"
FIRST_MESSAGE = (
    "Hello! This is the first time I have opened Housemate. Please start the setup "
    "with me now: load the onboarding skill and begin with its first step."
)


def call(path, method="GET", body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(OPENCODE + path, data=data, method=method, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as r:
        text = r.read().decode()
    return json.loads(text) if text else None


def read(path):
    try:
        with open(path) as f:
            return f.readline().strip()
    except OSError:
        return ""


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        f.write(text + "\n")
    os.replace(tmp, path)


def onboarding_status():
    r = subprocess.run(["/usr/local/bin/housemate-onboarding", "status"], capture_output=True, text=True, timeout=30)
    first = r.stdout.splitlines()[0] if r.stdout else ""
    return first.replace("onboarding:", "").strip()


def take(status=onboarding_status):
    ids = {s["id"] for s in (call("/session") or [])}
    marked = read(MARK)
    if marked in ids:
        stamp = f"{marked}@{os.stat(MARK).st_mtime_ns}"
        if read(SEEN) != stamp:
            write(SEEN, stamp)
            return marked
    if status() == "new":
        if read(WELCOME) in ids:
            return ""  # already made; the launcher's usual chat (the newest) is it
        sid = call("/session", "POST", {"title": TITLE})["id"]
        write(WELCOME, sid)
        call(f"/session/{sid}/prompt_async", "POST", {"parts": [{"type": "text", "text": FIRST_MESSAGE}]})
        return sid
    return ""


def main(argv):
    if argv[1:] != ["take"]:
        print(__doc__)
        return 2
    try:
        print(take())
    except Exception as e:  # noqa: BLE001 - the launcher opens its usual chat
        print(f"panel_open: {e}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

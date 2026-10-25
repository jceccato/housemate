#!/usr/bin/env python3
"""Housemate's update review: what is waiting, the daily summary, and the helpers
the update-review skill drives.

    housemate-updates list                what is waiting, in the order to install it
    housemate-updates summary             the daily summary, as it would be sent (read-only)
    housemate-updates daily               send the summary and prepare the briefed session
    housemate-updates serve               run `daily` once a day (the add-on's service)
    housemate-updates surface             what in this house release notes can touch (names only)
    housemate-updates notes               release notes between installed and target, per update
    housemate-updates breaking            Core's backward-incompatible changes, matched to this house
    housemate-updates baseline [--out F]  versions, Repairs, error signatures, counts
    housemate-updates backup              one full backup, named pre-updates-<date>, checked
    housemate-updates install ID          install one update and wait for it to land
    housemate-updates restart-core        configuration check, then one Core restart (for HACS)
    housemate-updates reboot              reboot the host (after an OS update)
    housemate-updates health --baseline F compare now with a baseline
    housemate-updates status              what this review has done so far today

Every command prints one JSON document. Exit 0 ok, 1 a check failed, 2 could not
talk to Home Assistant. Standard library only. The Supervisor token is in the
environment and goes to the Supervisor, nowhere else.
"""

import glob
import hashlib
import html
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kickoff  # noqa: E402  - the notification and websocket helpers live there

SUP = kickoff.SUPERVISOR
CORE = kickoff.CORE
OPTIONS = os.environ.get("HOUSEMATE_OPTIONS", "/data/options.json")
STATE_DIR = os.environ.get("HOUSEMATE_REVIEW_STATE", "/data/update-review")
WORK_DIR = os.environ.get("HOUSEMATE_REVIEW_WORK", "/config/.housemate/updates")
KICKOFF = os.environ.get("HOUSEMATE_KICKOFF_LOCAL", "http://127.0.0.1:" + str(kickoff.LISTEN[1]))
DEFAULT_TIME = "09:00"
USER_AGENT = "housemate-update-review"

# The order to install in: the Supervisor, the OS, Core, add-ons (the database
# one first, on its own), HACS, and Housemate last, because its own update ends
# the chat that is doing the work.
ORDER = {"supervisor": 0, "os": 1, "core": 2, "addon": 3, "hacs": 4, "housemate": 5, "other": 9}
KIND_NAME = {"supervisor": "Supervisor", "os": "Operating System", "core": "Home Assistant Core",
             "addon": "Add-on", "hacs": "HACS", "housemate": "Housemate", "other": "Not updated by Housemate"}
DATABASE_ADDONS = {"core_mariadb", "a0d7b954_mariadb", "core_postgres"}


# -- what is waiting -------------------------------------------------------------------------

def classify(entity_id, platform, own_slug, slug):
    if entity_id == "update.home_assistant_core_update":
        return "core"
    if entity_id == "update.home_assistant_operating_system_update":
        return "os"
    if entity_id == "update.home_assistant_supervisor_update":
        return "supervisor"
    if platform == "hassio":
        return "housemate" if slug and slug == own_slug else "addon"
    if platform == "hacs":
        return "hacs"
    return "other"  # device firmware, other servers' versions: listed, never updated


def is_prerelease(version):
    """2026.11.0b2, 1.2.0-rc1, 3.0.dev1: yes. A commit hash that happens to end in 'b': no."""
    return bool(re.fullmatch(r"(?i)v?\d+(\.\d+)*[.-]?(a|b|rc|alpha|beta|dev|pr)[.-]?\d*", str(version)))


def pending_from(states, registry, own_slug):
    out = []
    for s in states:
        eid = s["entity_id"]
        if not eid.startswith("update.") or s.get("state") != "on":
            continue
        a = s.get("attributes", {})
        platform = (registry.get(eid) or {}).get("platform", "")
        m = re.search(r"/addons/([^/]+)/", a.get("entity_picture") or "")
        slug = m.group(1) if m else ""
        kind = classify(eid, platform, own_slug, slug)
        latest = str(a.get("latest_version"))
        out.append({
            "entity_id": eid, "kind": kind, "platform": platform, "slug": slug,
            "title": a.get("title") or a.get("friendly_name") or eid,
            "installed": a.get("installed_version"), "latest": a.get("latest_version"),
            "release_url": a.get("release_url"),
            "prerelease": is_prerelease(latest),
        })
    out.sort(key=lambda u: (ORDER[u["kind"]], 0 if u["slug"] in DATABASE_ADDONS else 1, u["title"].lower()))
    return out


def kit_files(incoming):
    return sum((incoming.get("counts") or {}).values()) if incoming and incoming.get("pending") else 0


def summarise(found, incoming):
    """The daily summary as {title, short, text, count}, or None when nothing is waiting."""
    todo = [u for u in found if u["kind"] != "other"]
    other = [u for u in found if u["kind"] == "other"]
    kit = kit_files(incoming)
    if not todo and not kit:
        return None
    lines = []
    for u in todo:
        name = KIND_NAME[u["kind"]] if u["kind"] in ("core", "os", "supervisor", "housemate") else u["title"]
        if u["kind"] == "addon":
            name = f"Add-on {u['title']}"
        elif u["kind"] == "hacs":
            name = f"HACS {u['title']}"
        lines.append(f"{name}: {u['installed']} to {u['latest']}")
    if kit:
        lines.append(f"Housemate kit changes: {kit} kit file{'s' if kit != 1 else ''} staged as incoming "
                     f"(kit version {incoming.get('from_kit_version')} to {incoming.get('kit_version')})")
    if other:
        lines.append("Not updated by Housemate, only listed: " + ", ".join(u["entity_id"] for u in other))
    n = len(todo)
    parts = []
    if n:
        parts.append(f"{n} update{'s' if n != 1 else ''}")
    if kit:
        parts.append(f"{kit} kit file{'s' if kit != 1 else ''}")
    short = " and ".join(parts) + " waiting"
    return {"title": "Housemate: " + short, "short": short, "count": n, "kit_files": kit,
            "lines": lines, "text": "\n".join("- " + l for l in lines)}


def digest(found, incoming):
    parts = sorted(f"{u['entity_id']}={u['installed']}>{u['latest']}" for u in found)
    parts.append(f"kit={kit_files(incoming)}:{(incoming or {}).get('kit_version')}")
    return hashlib.sha256("\n".join(parts).encode()).hexdigest()[:16]


def brief(summary):
    return (
        "Housemate prepared this update review. Nothing has been changed and nothing has been run: "
        "it waits here for the person to say go.\n\n"
        "When they reply, load the `update-review` skill and follow it: start with the read-only report "
        "(what is waiting, the release notes between each installed and target version, the breaking "
        "changes matched against this house's configuration), then ask for the two approvals it describes. "
        "Do not install or restart anything before they are given.\n\n"
        "Waiting now:\n" + summary["text"]
    )


# -- the schedule ------------------------------------------------------------------------------

def review_time(options):
    value = str(options.get("review_time") or "")
    return value if re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", value) else DEFAULT_TIME


def due(now_hhmm, today, last_date, hhmm):
    return last_date != today and now_hhmm >= hhmm


# -- health ----------------------------------------------------------------------------------------

def compare(base, now, running, allow):
    problems = []
    if not running:
        problems.append("Home Assistant is not RUNNING")
    new_repairs = sorted(r for r in set(now["repairs"]) - set(base["repairs"]) if not any(a in r for a in allow))
    if new_repairs:
        problems.append(f"new Repairs: {new_repairs}")
    new_errors = sorted(set(now["error_signatures"]) - set(base["error_signatures"]))
    if new_errors:
        problems.append(f"new errors in the log: {new_errors[:10]}")
    if now["unavailable"] > base["unavailable"] + 10:
        problems.append(f"unavailable entities {base['unavailable']} -> {now['unavailable']}")
    if now["automations_on"] < base["automations_on"]:
        problems.append(f"automations on {base['automations_on']} -> {now['automations_on']}")
    return problems


# -- Core's release notes ------------------------------------------------------------------------------

def version_key(v):
    return [int(x) for x in re.findall(r"\d+", str(v))]


def core_months(installed, latest):
    """The monthly Core releases crossed going from `installed` to `latest` ('2026.10')."""
    (y, m), (hy, hm) = version_key(installed)[:2], version_key(latest)[:2]
    out = []
    while (y, m) < (hy, hm):
        m += 1
        if m > 12:
            y, m = y + 1, 1
        out.append(f"{y}.{m}")
    return out


def release_post_url(index_html, month):
    year, mon = month.split(".")
    m = re.search(rf'href="(/blog/{year}/\d\d/\d\d/release-{year}{int(mon)}/)"', index_html)
    return "https://www.home-assistant.io" + m.group(1) if m else None


class _Text(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("svg", "script", "style"):
            self.skip += 1
        if tag in ("p", "li", "br", "div", "h2", "h3"):
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("svg", "script", "style"):
            self.skip = max(0, self.skip - 1)

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def plain_text(fragment):
    p = _Text()
    p.feed(fragment)
    return re.sub(r"\n\s*\n+", "\n", re.sub(r"[ \t]+", " ", "".join(p.parts))).strip()


def breaking_items(post_html):
    """The items of a release post's 'Backward-incompatible changes' section."""
    start = re.search(r"<h2[^>]*>\s*Backward-incompatible changes", post_html)
    if not start:
        return []
    rest = post_html[start.end():]
    end = re.search(r"<h2[ >]", rest)
    section = rest[:end.start()] if end else rest
    items = []
    for block in re.findall(r"<details.*?</details>", section, flags=re.S):
        title = re.search(r"<summary.*?<span>(.*?)</span>", block, flags=re.S)
        body = re.search(r'<div class="details-block-content"[^>]*>(.*)</div>\s*</details>', block, flags=re.S)
        link = re.search(r'href="/integrations/([a-z0-9_]+)/', block)
        items.append({
            "title": html.unescape(plain_text(title.group(1))) if title else "",
            "integration": link.group(1) if link else None,
            "text": plain_text(body.group(1)) if body else plain_text(block),
        })
    return items


def match_items(items, surface):
    """Mark each item: `yes` (its integration is set up or used in YAML here), `no`
    (an integration this house does not use) or `general` (not about one integration)."""
    here = set(surface.get("integrations", [])) | set(surface.get("yaml_keys", [])) | set(surface.get("custom_components", []))
    out = []
    for i in items:
        applies = "general" if not i["integration"] else ("yes" if i["integration"] in here else "no")
        out.append(dict(i, applies=applies))
    return out


# -- HTTP ----------------------------------------------------------------------------------------------

def token():
    return os.environ.get("SUPERVISOR_TOKEN", "")


def http(url, method="GET", data=None, timeout=60, raw=False, headers=None, auth=True):
    hdr = {"User-Agent": USER_AGENT}
    if auth and url.startswith(SUP):  # the token goes to the Supervisor only, whatever a redirect says
        hdr["Authorization"] = "Bearer " + token()
    if data is not None:
        hdr["Content-Type"] = "application/json"
    hdr.update(headers or {})
    req = urllib.request.Request(url, method=method, data=None if data is None else json.dumps(data).encode(), headers=hdr)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body = r.read().decode(errors="replace")
    if raw:
        return body
    try:
        return json.loads(body) if body else None
    except ValueError:
        return body


def sup(path, method="GET", data=None, timeout=60):
    out = http(SUP + path, method, data, timeout)
    return out.get("data", out) if isinstance(out, dict) else out


def open_web(url, timeout=30):
    return http(url, raw=True, timeout=timeout, auth=False)


def github(path):
    return http("https://api.github.com" + path, auth=False, timeout=30, headers={"Accept": "application/vnd.github+json"})


def options():
    try:
        with open(OPTIONS) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


# -- reading Home Assistant -----------------------------------------------------------------------------

def own_slug():
    return kickoff.addon_slug()


def pending():
    states = http(CORE + "/api/states")
    registry = {e["entity_id"]: e for e in kickoff.websocket_call({"type": "config/entity_registry/list"})}
    return pending_from(states, registry, own_slug())


def incoming_status():
    try:
        r = subprocess.run(["housemate-incoming", "status", "--json"], capture_output=True, text=True, timeout=30)
        return json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else None
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


def running():
    try:
        return http(CORE + "/api/config", timeout=10).get("state") == "RUNNING"
    except Exception:  # noqa: BLE001
        return False


def counts():
    states = http(CORE + "/api/states")
    return {"unavailable": sum(s["state"] == "unavailable" for s in states),
            "automations_on": sum(s["entity_id"].startswith("automation.") and s["state"] == "on" for s in states)}


def repairs():
    r = kickoff.websocket_call({"type": "repairs/list_issues"}) or {}
    return sorted(f"{i['domain']}/{i['issue_id']}" for i in r.get("issues", []) if not i.get("ignored"))


def error_signatures(hours=24):
    """ERROR and CRITICAL entries of the last `hours` hours as signatures (logger and message,
    digits squashed), so the same fault logged again compares equal."""
    try:
        now = datetime.fromisoformat(http(CORE + "/api/template", "POST", {"template": "{{ now().isoformat() }}"}, raw=True).strip().strip('"')[:19])
        log = http(SUP + "/core/logs", raw=True, timeout=120, headers={"Accept": "text/plain", "Range": "entries=:-20000:20000"})
    except Exception:  # noqa: BLE001 - a host with no readable log has no signatures to compare
        return {}
    log = re.sub(r"\x1b\[[0-9;]*m", "", log)
    sigs = {}
    for line in log.splitlines():
        m = re.match(r"(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)\.\d+ (ERROR|CRITICAL) \(.*?\) \[(.*?)\] ?(.*)", line)
        if m and datetime.fromisoformat(m.group(1)) >= now - timedelta(hours=hours):
            sig = f"{m.group(2)} {m.group(3)} | {re.sub(r'[0-9]+', 'N', m.group(4))[:160]}"
            sigs[sig] = sigs.get(sig, 0) + 1
    return sigs


def versions():
    out = {"core": sup("/core/info")["version"], "os": sup("/os/info").get("version"),
           "supervisor": sup("/supervisor/info")["version"], "addons": {}}
    for a in sup("/addons")["addons"]:
        out["addons"][a["slug"]] = {"name": a["name"], "version": a["version"], "latest": a.get("version_latest")}
    return out


def baseline():
    b = {"taken": datetime.now().isoformat(timespec="seconds"), "versions": versions(),
         "repairs": repairs(), "error_signatures": error_signatures(), **counts()}
    b["error_entries"] = sum(b["error_signatures"].values())
    return b


def surface():
    """What in this house a release note can touch. Names only: no option values, no secrets."""
    entries = http(CORE + "/api/config/config_entries/entry")
    integrations = sorted({e["domain"] for e in entries})
    yaml_keys, custom = set(), []
    for pattern in ("/config/*.yaml", "/config/packages/*.yaml", "/config/packages/**/*.yaml"):
        for path in glob.glob(pattern, recursive=True):
            if os.path.basename(path) == "secrets.yaml":
                continue
            try:
                with open(path, errors="replace") as f:
                    for line in f:
                        m = re.match(r"^([a-z_][a-z0-9_ ]*?)(?: [a-z0-9_]+)?:", line)
                        if m:
                            yaml_keys.add(m.group(1).split()[0])
            except OSError:
                pass
    cc = "/config/custom_components"
    if os.path.isdir(cc):
        custom = sorted(d for d in os.listdir(cc) if os.path.isdir(os.path.join(cc, d)))
    addons = [{"slug": a["slug"], "name": a["name"], "version": a["version"]} for a in sup("/addons")["addons"]]
    return {"integrations": integrations, "yaml_keys": sorted(yaml_keys), "custom_components": custom, "addons": addons}


# -- release notes --------------------------------------------------------------------------------------------

def notes(max_chars=2500):
    out = []
    for u in pending():
        if u["kind"] == "other":
            continue
        rec = {"entity_id": u["entity_id"], "kind": u["kind"], "title": u["title"], "installed": u["installed"],
               "latest": u["latest"], "release_url": u["release_url"], "notes": []}
        gh = re.match(r"https://github\.com/([^/]+/[^/]+)/", u["release_url"] or "")
        if u["kind"] == "core":
            rec["months_to_read"] = core_months(u["installed"], u["latest"])
            rec["see"] = "housemate-updates breaking"
        elif gh:
            try:
                for r in sorted(github(f"/repos/{gh.group(1)}/releases?per_page=100"), key=lambda r: version_key(r["tag_name"])):
                    if not r["prerelease"] and version_key(u["installed"]) < version_key(r["tag_name"]) <= version_key(u["latest"]):
                        rec["notes"].append({"tag": r["tag_name"], "date": r["published_at"][:10], "body": (r["body"] or "")[:max_chars]})
            except Exception as e:  # noqa: BLE001
                rec["notes_error"] = str(e)
        elif u["kind"] in ("addon", "housemate"):
            try:
                rec["notes"].append({"tag": u["latest"], "body": http(f"{SUP}/addons/{u['slug']}/changelog", raw=True)[:max_chars]})
            except Exception as e:  # noqa: BLE001
                rec["notes_error"] = str(e)
        out.append(rec)
    return out


def breaking():
    """Core's backward-incompatible changes for every monthly release crossed, matched to this house."""
    core = next((u for u in pending() if u["kind"] == "core"), None)
    if not core:
        return {"core": None, "releases": []}
    here = surface()
    result = {"core": {"installed": core["installed"], "latest": core["latest"]}, "releases": []}
    try:
        index = open_web("https://www.home-assistant.io/blog/categories/release-notes/")
    except Exception as e:  # noqa: BLE001
        return dict(result, error=f"could not read the release index: {e}")
    for month in core_months(core["installed"], core["latest"]):
        url = release_post_url(index, month)
        rec = {"release": month, "url": url, "items": []}
        if not url:
            rec["error"] = "no release post found; read the notes by hand"
        else:
            try:
                rec["items"] = match_items(breaking_items(open_web(url, timeout=60)), here)
            except Exception as e:  # noqa: BLE001
                rec["error"] = str(e)
        result["releases"].append(rec)
    return result


# -- backing up and installing ------------------------------------------------------------------------------------

def backup(timeout=1800):
    name = "pre-updates-" + datetime.now().strftime("%Y-%m-%d")
    before = {b["slug"] for b in sup("/backups")["backups"]}
    sup("/backups/new/full", "POST", {"name": name, "background": True})
    deadline = time.time() + timeout
    while time.time() < deadline:
        made = [b for b in sup("/backups")["backups"] if b["slug"] not in before and b.get("name") == name]
        if made:
            info = sup(f"/backups/{made[0]['slug']}/info")
            included = {a["slug"] for a in info.get("addons", [])}
            installed = {a["slug"] for a in sup("/addons")["addons"]}
            missing = sorted((installed & DATABASE_ADDONS) - included)
            ok = info.get("type") == "full" and bool(info.get("homeassistant")) and (info.get("size") or 0) > 0 and not missing
            return {"ok": ok, "name": name, "slug": info["slug"], "size_mb": info.get("size"),
                    "addons": len(included), "type": info.get("type"), "database_addons_missing": missing,
                    "locations": info.get("locations") or [info.get("location")]}
        time.sleep(5)
    return {"ok": False, "name": name, "error": "the backup did not appear in time"}


def wait_for_core(version=None, timeout=900):
    t0 = time.time()
    time.sleep(15)
    while time.time() - t0 < timeout:
        try:
            cfg = http(CORE + "/api/config", timeout=10)
            if cfg.get("state") == "RUNNING" and (version is None or cfg.get("version") == version):
                prev = None
                for _ in range(12):  # integrations load: the unavailable count must hold still
                    cur = counts()["unavailable"]
                    if prev is not None and abs(cur - prev) <= 2:
                        return {"up": True, "version": cfg["version"], "unavailable": cur, "waited_s": int(time.time() - t0)}
                    prev = cur
                    time.sleep(20)
                return {"up": True, "version": cfg["version"], "unavailable": prev, "settled": False, "waited_s": int(time.time() - t0)}
        except Exception:  # noqa: BLE001
            pass
        time.sleep(10)
    return {"up": False, "waited_s": int(time.time() - t0)}


def progress_file():
    return os.path.join(WORK_DIR, "progress-" + datetime.now().strftime("%Y-%m-%d") + ".json")


def record(step):
    os.makedirs(WORK_DIR, exist_ok=True)
    path = progress_file()
    try:
        with open(path) as f:
            steps = json.load(f)
    except (OSError, ValueError):
        steps = []
    steps.append(dict(step, at=datetime.now().isoformat(timespec="seconds")))
    with open(path, "w") as f:
        json.dump(steps, f, indent=1)
    return path


def install(entity_id, timeout=1500):
    """Install one update (without the Supervisor's own backup: the review made one) and wait
    for it to land. The OS is only staged: reboot afterwards. Housemate's own update ends this process."""
    found = {u["entity_id"]: u for u in pending()}
    if entity_id not in found:
        return {"ok": False, "entity_id": entity_id, "error": "that update is not waiting"}
    u = found[entity_id]
    if u["kind"] == "other":
        return {"ok": False, "entity_id": entity_id, "error": "firmware and other servers are never updated here"}
    if u["prerelease"]:
        return {"ok": False, "entity_id": entity_id, "error": f"{u['latest']} is a pre-release; stable updates only"}
    if u["kind"] == "supervisor" and sup("/supervisor/info").get("channel") != "stable":
        return {"ok": False, "entity_id": entity_id, "error": "the Supervisor is not on the stable channel; stable updates only"}
    record({"entity_id": entity_id, "kind": u["kind"], "from": u["installed"], "to": u["latest"], "step": "started"})
    was = sup(f"/addons/{u['slug']}/info")["state"] if u["kind"] in ("addon", "housemate") else None
    body = {"entity_id": entity_id}
    if u["kind"] != "hacs":
        body["backup"] = False
    err = None
    try:
        http(CORE + "/api/services/update/install", "POST", body, timeout=timeout)
    except (urllib.error.URLError, ConnectionError, TimeoutError, OSError) as e:
        err = str(e)  # Core going down mid-call is how a Core update looks
    t0, done = time.time(), False
    while time.time() - t0 < timeout:
        try:
            if u["kind"] == "core":
                done = wait_for_core(u["latest"], timeout)["up"]
                break
            if u["kind"] == "supervisor":
                done = sup("/supervisor/info")["version"] == u["latest"]
            elif u["kind"] == "os":
                done = True  # staged in the other slot; the reboot is a separate approval
            elif u["kind"] in ("addon", "housemate"):
                info = sup(f"/addons/{u['slug']}/info")
                done = info["version"] == u["latest"] and info["state"] == was
            else:
                done = http(CORE + "/api/states/" + entity_id)["state"] == "off"
        except Exception:  # noqa: BLE001
            done = False
        if done:
            break
        time.sleep(10)
    record({"entity_id": entity_id, "kind": u["kind"], "step": "landed" if done else "not landed"})
    return {"entity_id": entity_id, "kind": u["kind"], "ok": done, "call_error": err, "waited_s": int(time.time() - t0),
            "next": "reboot the host to finish the OS update" if u["kind"] == "os" and done else None}


def restart_core(timeout=900):
    """Home Assistant's configuration check, then one Core restart (HACS integrations take
    effect on it), then wait until Core is back and settled."""
    check = http(CORE + "/api/config/core/check_config", "POST", {})
    if check.get("result") != "valid":
        return {"ok": False, "error": "the configuration check failed; not restarting", "check": check}
    record({"step": "core restart"})
    try:
        http(CORE + "/api/services/homeassistant/restart", "POST", {}, timeout=60)
    except (urllib.error.URLError, ConnectionError, TimeoutError, OSError):
        pass  # Core going down mid-call is how a restart looks
    waited = wait_for_core(None, timeout)
    return {"ok": waited["up"], **waited}


def reboot():
    record({"step": "host reboot"})
    sup("/host/reboot", "POST")
    return {"ok": True, "note": "the host is rebooting; this add-on starts again with it"}


def health(base_file, allow=()):
    with open(base_file) as f:
        base = json.load(f)
    now = {"repairs": repairs(), "error_signatures": error_signatures(), **counts()}
    problems = compare(base, now, running(), allow)
    keys = ("unavailable", "automations_on", "repairs")
    return {"ok": not problems, "problems": problems, "now": {k: now[k] for k in keys}, "baseline": {k: base[k] for k in keys}}


def status():
    out = {"waiting": [u["entity_id"] for u in pending()], "progress": []}
    try:
        with open(progress_file()) as f:
            out["progress"] = json.load(f)
    except (OSError, ValueError):
        pass
    return out


# -- the daily summary --------------------------------------------------------------------------------------------------

def state_file():
    return os.path.join(STATE_DIR, "state.json")


def load_state():
    try:
        with open(state_file()) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_state(state):
    os.makedirs(STATE_DIR, mode=0o700, exist_ok=True)
    with open(state_file() + ".tmp", "w") as f:
        json.dump(state, f)
    os.replace(state_file() + ".tmp", state_file())


def session_exists(sid):
    try:
        return bool(sid) and bool(kickoff.call("GET", f"{kickoff.OPENCODE}/session/{sid}", timeout=10))
    except Exception:  # noqa: BLE001
        return False


def prepare_session(summary, target):
    reply = kickoff.call("POST", KICKOFF + "/kickoff", {
        "text": brief(summary), "title": "Update review: " + summary["short"], "notify": target, "prepare": True,
    }, timeout=90)
    return reply["session_id"]


def daily():
    """Send the one summary a day. Returns what was done; raises when Home Assistant is not reachable."""
    found = pending()
    incoming = incoming_status()
    summary = summarise(found, incoming)
    if not summary:
        return {"sent": False, "reason": "nothing is waiting"}
    state = load_state()
    key = digest(found, incoming)
    target = kickoff.normalise_target(options().get("review_notify"))
    sid = state.get("session_id") if state.get("digest") == key else None
    if not session_exists(sid):
        sid = prepare_session(summary, target)
    url = kickoff.panel_url()
    message = (f"{summary['text']}\n\nA review is ready in Housemate: open it and say go. It reads the release notes "
               "against your configuration, makes a backup, and asks twice (install, then restart) before it changes anything.")
    delivered = []
    if target:
        delivered.append(kickoff.service("notify", target, {
            "title": summary["title"],
            "message": summary["short"].capitalize() + ". Review opens Housemate.",
            "data": {"url": url, "clickAction": url, "tag": "housemate_update_review",
                     "actions": [{"action": "URI", "title": "Review", "uri": url}]},
        }))
    delivered.append(kickoff.service("persistent_notification", "create", {
        "title": summary["title"],
        "message": f"{message}\n\n[Review]({url}) (session `{sid}`)",
        "notification_id": "housemate_update_review",
    }))
    if not all(delivered):  # tomorrow's run, or the next minute's, tries again
        return {"sent": False, "reason": "a notification could not be delivered", "session_id": sid}
    save_state(dict(state, digest=key, session_id=sid, last_sent=datetime.now().isoformat(timespec="seconds")))
    return {"sent": True, "session_id": sid, "title": summary["title"], "url": url, "companion": bool(target)}


def local_now():
    try:
        from zoneinfo import ZoneInfo
        zone = http(CORE + "/api/config", timeout=10)["time_zone"]
        return datetime.now(ZoneInfo(zone))
    except Exception:  # noqa: BLE001 - the container's own clock is the fallback
        return datetime.now(timezone.utc).astimezone()


def serve():
    kickoff.log("update review: waiting for the daily time")
    while True:
        try:
            now = local_now()
            state = load_state()
            if due(now.strftime("%H:%M"), now.strftime("%Y-%m-%d"), state.get("last_date"), review_time(options())):
                result = daily()
                kickoff.log(f"update review: {json.dumps(result)}")
                if result["sent"] or result.get("reason") == "nothing is waiting":
                    save_state(dict(load_state(), last_date=now.strftime("%Y-%m-%d")))
        except Exception as e:  # noqa: BLE001 - Home Assistant may still be starting; try again next minute
            kickoff.log(f"update review: {e}")
        time.sleep(60)


# -- the command line -----------------------------------------------------------------------------------------------------------

def main(argv):
    cmd = argv[1] if len(argv) > 1 else ""
    arg = lambda flag, default=None: argv[argv.index(flag) + 1] if flag in argv else default  # noqa: E731
    try:
        if cmd == "list":
            out = pending()
        elif cmd == "summary":
            out = summarise(pending(), incoming_status()) or {"text": "", "count": 0}
        elif cmd == "daily":
            out = daily()
        elif cmd == "serve":
            serve()
            return 0
        elif cmd == "surface":
            out = surface()
        elif cmd == "notes":
            out = notes()
        elif cmd == "breaking":
            out = breaking()
        elif cmd == "baseline":
            out = baseline()
            if arg("--out"):
                os.makedirs(os.path.dirname(arg("--out")) or ".", exist_ok=True)
                with open(arg("--out"), "w") as f:
                    json.dump(out, f, indent=1, sort_keys=True)
        elif cmd == "backup":
            out = backup()
            print(json.dumps(out))
            return 0 if out["ok"] else 1
        elif cmd == "install" and len(argv) > 2:
            out = install(argv[2], int(arg("--timeout", 1500)))
            print(json.dumps(out))
            return 0 if out["ok"] else 1
        elif cmd == "restart-core":
            out = restart_core()
            print(json.dumps(out))
            return 0 if out["ok"] else 1
        elif cmd == "reboot":
            out = reboot()
        elif cmd == "health" and arg("--baseline"):
            out = health(arg("--baseline"), [argv[i + 1] for i, a in enumerate(argv) if a == "--allow-repair"])
            print(json.dumps(out))
            return 0 if out["ok"] else 1
        elif cmd == "status":
            out = status()
        else:
            print(__doc__)
            return 2
    except Exception as e:  # noqa: BLE001
        print(json.dumps({"error": f"{type(e).__name__}: {e}"}))
        return 2
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

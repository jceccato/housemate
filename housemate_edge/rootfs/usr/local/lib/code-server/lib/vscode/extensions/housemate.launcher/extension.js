// Housemate's launcher: the panel opens straight into OpenCode.
//
// On every start of a window it opens OpenCode in a terminal tab in the editor
// area (not the bottom panel), resuming the newest chat, unless that tab is
// already there: opening the panel twice never stacks a second OpenCode. The
// exception is a chat that something wants the person in (a job's question, the
// first-run welcome): that gets a tab of its own, in front.
// It also adds two commands (and status bar buttons) so that a person need not
// know OpenCode's own: start a new chat, and choose another recent one.
//
// Plain JavaScript with no dependencies. The terminal runs housemate-agent
// (OpenCode in a tmux session of its own), which is what keeps it to one
// instance; tests/seam_a/test_panel.py drives this file in the editor's node.

const NAME = "OpenCode";
// A link that names a chat (deeplink.js, via the add-on) leaves its id here.
const OPEN_REQUEST = "/config/.housemate/open-request";
const REQUEST_POLL_MS = 1000;
// A request this young when the window starts was made by the link that opened it.
const FRESH_MS = 60000;
const CWD = "/config";
// How long to wait for a restored terminal to show up before deciding there is
// none: after a reload the editor revives the previous tab a moment later.
const SETTLE_MS = 2500;

// OpenCode's `session list --format json`: newest first, as items for a pick list.
function sessionItems(json) {
  let list;
  try { list = JSON.parse(json); } catch { return []; }
  if (!Array.isArray(list)) return [];
  return list
    .filter((s) => s && typeof s.id === "string")
    .map((s) => {
      const updated = s.updated || (s.time && s.time.updated);
      return {
        label: (s.title && String(s.title).trim()) || s.id,
        description: updated ? new Date(updated).toLocaleString() : "",
        id: s.id,
      };
    });
}

function findOpenCode(terminals) {
  return terminals.find((t) => t.name === NAME);
}

function activate(context) {
  const vscode = require("vscode");
  const cp = require("child_process");

  const fs = require("fs");
  const tabs = new Map(); // chat id -> its terminal

  const open = (openCodeArgs) =>
    vscode.window.createTerminal({
      name: NAME,
      cwd: CWD,
      shellPath: "/usr/local/bin/housemate-agent",
      shellArgs: openCodeArgs,
      location: { viewColumn: vscode.ViewColumn.Active },
      isTransient: false,
    });

  const closeBottomPanel = () => vscode.commands.executeCommand("workbench.action.closePanel");

  function openAgent() {
    const existing = findOpenCode(vscode.window.terminals);
    // A tab whose process has ended (the add-on restarted under it) is not an open OpenCode.
    if (existing && existing.exitStatus === undefined) { existing.show(); return; }
    if (existing) existing.dispose();
    open([]).show();
    closeBottomPanel();
  }

  // A chat a job marked since the panel last looked, or the welcome chat on a first
  // run (panel_open.py): it gets a tab of its own, in front. Otherwise the usual chat.
  function takeChat() {
    return new Promise((resolve) => {
      cp.execFile("python3", ["/usr/lib/housemate/panel_open.py", "take"],
        { cwd: CWD, timeout: 20000 }, (err, stdout) => resolve(err ? "" : String(stdout).trim()));
    });
  }

  // The chat's tab in front: the one already open for it, else a new one.
  function showChat(id) {
    const tab = tabs.get(id);
    if (tab && tab.exitStatus === undefined) { tab.show(); return; }
    const t = open(["--session", id]);
    tabs.set(id, t);
    t.show();
  }

  async function openPanel() {
    const id = await takeChat();
    if (!/^[A-Za-z0-9_-]+$/.test(id)) { openAgent(); return; }
    const existing = findOpenCode(vscode.window.terminals);
    if (existing && existing.exitStatus !== undefined) existing.dispose();
    showChat(id);
    closeBottomPanel();
  }

  // A link that names a chat: bring its tab to the front, whether the panel was
  // just opened by the link or was open already.
  function watchRequests() {
    let handled = 0;
    const stat = () => { try { return fs.statSync(OPEN_REQUEST); } catch { return null; } };
    const first = stat();
    if (first && Date.now() - first.mtimeMs > FRESH_MS) handled = first.mtimeMs;
    setInterval(() => {
      const st = stat();
      if (!st || st.mtimeMs <= handled) return;
      handled = st.mtimeMs;
      let id = "";
      try { id = fs.readFileSync(OPEN_REQUEST, "utf8").trim(); } catch { return; }
      if (/^ses_[A-Za-z0-9]+$/.test(id)) { showChat(id); closeBottomPanel(); }
    }, REQUEST_POLL_MS);
  }

  function newChat() {
    // A new chat is a new tab beside the one running; the old one stays.
    open(["--new"]).show();
  }

  async function sessions() {
    const picked = await new Promise((resolve) => {
      cp.execFile("opencode", ["session", "list", "--format", "json", "-n", "30"],
        { cwd: CWD, timeout: 20000 }, (err, stdout) => resolve(err ? null : sessionItems(stdout)));
    });
    if (!picked || picked.length === 0) {
      vscode.window.showInformationMessage("There are no earlier chats yet. Use “Housemate: Start a new chat”.");
      return;
    }
    const choice = await vscode.window.showQuickPick(picked, { placeHolder: "Choose a chat to continue" });
    if (choice) showChat(choice.id);
  }

  context.subscriptions.push(
    vscode.commands.registerCommand("housemate.openAgent", openAgent),
    vscode.commands.registerCommand("housemate.newChat", newChat),
    vscode.commands.registerCommand("housemate.sessions", sessions),
  );

  for (const [text, command, tip, priority] of [
    ["$(comment-discussion) New chat", "housemate.newChat", "Start a new Housemate chat", 101],
    ["$(history) Chats", "housemate.sessions", "Choose another recent chat", 100],
  ]) {
    const item = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, priority);
    item.text = text; item.command = command; item.tooltip = tip; item.show();
    context.subscriptions.push(item);
  }

  // On start of a window (a fresh open, a reload, a reconnect after the add-on
  // restarted): wait for a revived tab, then open the agent only if none came back.
  // The link's request is looked at after that, so its chat ends up in front.
  setTimeout(async () => { await openPanel(); watchRequests(); }, SETTLE_MS);
}

function deactivate() {}

module.exports = { activate, deactivate };

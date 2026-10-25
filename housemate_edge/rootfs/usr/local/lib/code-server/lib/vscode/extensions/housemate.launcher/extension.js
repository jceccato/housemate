// Housemate's launcher: the panel opens straight into OpenCode.
//
// On every start of a window it opens OpenCode in a terminal tab in the editor
// area (not the bottom panel), resuming the newest chat, unless that tab is
// already there: opening the panel twice never stacks a second OpenCode.
// It also adds two commands (and status bar buttons) so that a person need not
// know OpenCode's own: start a new chat, and choose another recent one.
//
// Plain JavaScript with no dependencies. The terminal runs housemate-agent
// (OpenCode in a tmux session of its own), which is what keeps it to one
// instance; tests/seam_a/test_panel.py drives this file in the editor's node.

const NAME = "OpenCode";
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
    if (existing) { existing.show(); return; }
    open([]).show();
    closeBottomPanel();
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
    if (choice) open(["--session", choice.id]).show();
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

  // On start: wait for a revived tab, then open the agent only if none came back.
  setTimeout(() => { openAgent(); }, SETTLE_MS);
}

function deactivate() {}

module.exports = { activate, deactivate };

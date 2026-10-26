"""Show a pending question to a panel that opened after it was asked.

OpenCode 1.19.4 shows a question only to a client that is attached when it is
asked; a client that attaches later is not told (the question stays pending on
the server, and the chat just says "Asked 1 question"). A job started by voice
or by the update review runs with no client, so a question it asks before the
person opens the panel would never be seen.

The launcher (housemate-agent) calls this once the panel is attached: if the
chat has a question pending, it is dismissed and the agent is asked to put it
again, which the attached panel shows. Nothing else is touched.

    reopen_question.py <opencode url> <session id>
"""

import json
import sys
import urllib.request

ASK_AGAIN = (
    "The person has just opened this chat. Ask your question again now, with the "
    "question tool, exactly as before, and wait for the answer."
)


def call(url, method="GET", body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as r:
        text = r.read().decode()
    return json.loads(text) if text else None


def pending(base, session):
    return [q for q in (call(base + "/question") or []) if q.get("sessionID") == session]


def reopen(base, session):
    """Dismiss the chat's pending question and ask the agent to ask again. Returns how many."""
    found = pending(base, session)
    if not found:
        return 0
    for q in found:
        call(f"{base}/question/{q['id']}/reject", "POST", {})
    call(f"{base}/session/{session}/prompt_async", "POST", {"parts": [{"type": "text", "text": ASK_AGAIN}]})
    return len(found)


def main(argv):
    if len(argv) != 3:
        print(__doc__)
        return 2
    try:
        n = reopen(argv[1].rstrip("/"), argv[2])
    except Exception as e:  # noqa: BLE001 - the panel works without this
        print(f"reopen_question: {e}", file=sys.stderr)
        return 1
    if n:
        print(f"reopen_question: asked again ({n} pending)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

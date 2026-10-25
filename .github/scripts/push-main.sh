#!/usr/bin/env bash
# Push HEAD to main; when main has moved, rebase onto it and try again.
# A conflict is not resolved here: it stops the run, loudly.
set -euo pipefail
for attempt in 1 2 3 4 5; do
  if git push origin HEAD:main; then
    exit 0
  fi
  echo "push refused (attempt ${attempt}); rebasing onto main"
  git pull --rebase origin main || { git rebase --abort || true; echo "::error::rebase onto main conflicted"; exit 1; }
done
echo "::error::main kept moving; gave up after 5 attempts"
exit 1

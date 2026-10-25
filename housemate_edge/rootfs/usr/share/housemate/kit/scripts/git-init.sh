#!/usr/bin/env bash
# Put /config under git with Housemate's ignore policy, and commit what is there.
# Safe to run again: it leaves an existing repository and .gitignore alone.
set -o errexit -o nounset -o pipefail

cd "${1:-/config}"

# The policy is written to .gitignore, or appended to one that is already there
# (a repository from another tool), once: the marker line says it is in.
if ! grep -qxF '# Housemate ignore policy' .gitignore 2>/dev/null; then
    cat >> .gitignore <<'EOF'
# Housemate ignore policy
# Secrets, credentials and bulk data stay out of git.

# Secrets
secrets.yaml
*.pem
*.key
ssl/
.ssh/
ip_bans.yaml
.esphome/
zigbee2mqtt/
*.token
*.pickle

# Databases, logs
*.db
*.db-shm
*.db-wal
*.log
*.log.*
OZW_Log.txt

# Backups, media, caches
backups/
media/
tts/
www/tts/
deps/
.cloud/
.uuid
.ha_run.lock
__pycache__/
*.pyc

# The add-on's own record of what it shipped
.housemate/

# .storage holds authentication and integration credentials, so it is ignored
# wholesale, except the files that are only dashboards and helpers.
.storage/*
!.storage/lovelace
!.storage/lovelace.*
!.storage/lovelace_dashboards
!.storage/lovelace_resources
!.storage/input_boolean
!.storage/input_button
!.storage/input_datetime
!.storage/input_number
!.storage/input_select
!.storage/input_text
!.storage/counter
!.storage/timer
!.storage/schedule
EOF
fi

existing=false
if [[ -d .git ]] && git rev-parse --verify --quiet HEAD >/dev/null; then
    existing=true
fi
if [[ ! -d .git ]]; then
    git init --quiet --initial-branch=main
fi

git config user.name >/dev/null || git config user.name "Housemate"
git config user.email >/dev/null || git config user.email "housemate@localhost"

if [[ "${existing}" == true ]]; then
    # A repository with history, and perhaps work in progress in it. Apply the policy and
    # commit only that: the .gitignore, and the removal of what the policy ignores. Everything
    # else the user has changed or staged stays exactly as it is. The commit is made in a
    # scratch copy of the index, built from HEAD, so nothing of theirs can ride along.
    scratch=$(mktemp -d)
    trap 'rm -rf "${scratch}"' EXIT
    export GIT_INDEX_FILE="${scratch}/index"
    git read-tree HEAD
    git ls-files -z --cached --ignored --exclude-standard | xargs -0 -r git rm --cached --quiet --
    git add .gitignore
    if ! git diff --cached --quiet HEAD; then
        git commit --quiet -m "Apply Housemate's ignore policy to /config"
    fi
    unset GIT_INDEX_FILE
    # The real index: the same changes, and nothing else touched.
    git ls-files -z --cached --ignored --exclude-standard | xargs -0 -r git rm --cached --quiet --
    git add .gitignore
else
    # Stop tracking anything the policy ignores that an earlier repository tracked.
    git ls-files -z --cached --ignored --exclude-standard | xargs -0 -r git rm --cached --quiet --
    git add -A
    if ! git diff --cached --quiet; then
        git commit --quiet -m "Start tracking /config: the configuration as it was"
    fi
fi
echo "/config is under git."

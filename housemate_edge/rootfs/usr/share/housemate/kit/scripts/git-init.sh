#!/usr/bin/env bash
# Put /config under git with Housemate's ignore policy, and commit what is there.
# Safe to run again: it leaves an existing repository and .gitignore alone.
set -o errexit -o nounset -o pipefail

cd "${1:-/config}"

if [[ ! -f .gitignore ]]; then
    cat > .gitignore <<'EOF'
# Housemate's ignore policy. Secrets, credentials and bulk data stay out of git.

# Secrets
secrets.yaml
*.pem
*.key
ssl/

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

if [[ ! -d .git ]]; then
    git init --quiet --initial-branch=main
fi

git config user.name >/dev/null || git config user.name "Housemate"
git config user.email >/dev/null || git config user.email "housemate@localhost"

git add -A
if ! git diff --cached --quiet; then
    git commit --quiet -m "Start tracking /config: the configuration as it was"
fi
echo "/config is under git."

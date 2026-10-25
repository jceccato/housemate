#!/usr/bin/env bash
# Run Home Assistant's configuration check; exit 0 only when it is valid.
set -o errexit -o nounset -o pipefail
reply=$(curl -s -X POST -H "Authorization: Bearer ${SUPERVISOR_TOKEN}" \
    http://supervisor/core/api/config/core/check_config)
echo "${reply}" | jq .
[[ $(echo "${reply}" | jq -r .result) == "valid" ]]

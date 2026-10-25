# Write and reload an automation

1. Find the entities: `curl -s -H "Authorization: Bearer $SUPERVISOR_TOKEN" http://supervisor/core/api/states`, filtered with `jq`.
2. Put the automation in `packages/<topic>.yaml` under `automation:` with an
   `id`, an `alias` and a `description` that says why it exists.
3. Run `scripts/check-config.sh`. Fix anything it reports.
4. Reload only automations:
   `curl -s -X POST -H "Authorization: Bearer $SUPERVISOR_TOKEN" http://supervisor/core/api/services/automation/reload`
5. Confirm it loaded: the state of `automation.<id>` exists and is `on`.
6. Commit it with a message that says why.

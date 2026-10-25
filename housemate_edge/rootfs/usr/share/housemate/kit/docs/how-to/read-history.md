# Read history

- Changes of one entity since a time:
  `GET /core/api/history/period/<ISO time>?filter_entity_id=<entity>&minimal_response`
- Logbook: `GET /core/api/logbook/<ISO time>?entity=<entity>`
- Home Assistant's log: `GET /core/api/error_log`, or `ha core logs` where the
  `ha` command exists.

All take the header `Authorization: Bearer $SUPERVISOR_TOKEN` at
`http://supervisor/core/api/...`. Keep the time window small; history is big.

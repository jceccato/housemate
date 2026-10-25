---
name: home-assistant
description: Use when you need to read or change live Home Assistant state through its API - finding entities, areas and devices (not only those exposed to Assist), calling services, testing a template, reading history, logbook or statistics, or checking what an entity or automation depends on.
---

# Home Assistant API

Two interfaces reach the running Home Assistant: **REST** for simple calls and **websocket** for the registries, rendered templates, history and anything REST lacks. Both authenticate with a bearer token you never print.

## Connecting

Inside the Housemate add-on the token is already in your environment and nothing else is needed:

| | URL | Token |
|---|---|---|
| REST | `http://supervisor/core/api/...` | header `Authorization: Bearer $SUPERVISOR_TOKEN` |
| Websocket | `ws://supervisor/core/websocket` | `SUPERVISOR_TOKEN`, used by `ha_ws.py` below |
| Supervisor | `http://supervisor/...` | the same header (backups, add-ons, the host) |

Outside the add-on use the instance's own URL (`http://<host>:8123/api/...`, `ws://<host>:8123/api/websocket`) and a long-lived token (Profile, Security, Long-lived access tokens). Keep the token in an environment variable and pass it by variable in the header; never write its value into a file, a command you echo, or the answer.

A 401 means the token is wrong or expired. A 404 under `/api/...` usually means the integration behind it is not set up. An error body says why; read it before retrying.

## REST, the common calls

```bash
api=http://supervisor/core/api; auth="Authorization: Bearer $SUPERVISOR_TOKEN"
curl -s -H "$auth" $api/states                    # every entity's state
curl -s -H "$auth" $api/states/light.kitchen      # one entity
curl -s -H "$auth" $api/services                  # every service and its fields
curl -s -H "$auth" $api/config                    # version, location, unit system, components
curl -s -H "$auth" -H 'Content-Type: application/json' \
  -d '{"entity_id": "light.kitchen"}' $api/services/light/turn_on
curl -s -H "$auth" $api/error_log                 # the log, as text
```

A service call returns the states it changed. Add `?return_response` to get a reply from services that return data (such as `weather.get_forecasts`).

## Finding entities

`/states` lists everything with a state, **whether or not it is exposed to Assist**: batteries, power meters and leak sensors included. Filter it instead of reading all of it:

```bash
curl -s -H "$auth" $api/states | jq -r '.[] | select(.attributes.device_class == "battery") | "\(.entity_id)\t\(.state)\t\(.attributes.friendly_name)"'
```

`/states` has no areas, devices or disabled entities. For those use the websocket registries with `ha_ws.py` (see "Websocket" below; under /config it is `.opencode/skills/home-assistant/ha_ws.py`):

| Question | Command |
|---|---|
| Every entity, with its area, device, platform, disabled state and spoken aliases | `config/entity_registry/list` |
| Areas (and their aliases) | `config/area_registry/list` |
| Devices (model, manufacturer, area) | `config/device_registry/list` |
| Floors | `config/floor_registry/list` |
| Which entities Assist may see | `homeassistant/expose_entity/list` |
| What an entity, device or area is connected to (automations, scripts, scenes) | `search/related` with `item_type` and `item_id` |

An entity's area is its own `area_id`, or else its device's: resolve both when listing by area. Templates do this for you (next section): `area_entities('kitchen')`, `device_entities(id)`, `integration_entities('hue')`, `area_name('light.kitchen')`.

Write what you learn into the cheat sheet (`docs/cheat-sheet.md`): entity IDs and the names people use for them.

## Testing a template

Render before you put a template in a file. REST:

```bash
curl -s -H "$auth" -H 'Content-Type: application/json' -d '{"template": "{{ states(\"sun.sun\") }}"}' $api/template
```

Websocket (the result comes as an event, with the entities the template listens to):

```bash
python3 ha_ws.py '{"type": "render_template", "template": "{{ states.light | selectattr(\"state\", \"eq\", \"on\") | map(attribute=\"entity_id\") | list }}"}' --events 1
```

The reply is `{"result": ..., "listeners": ...}`. A template error comes back as text or an error object: read it, fix the template, render again. Test with the real entity IDs, and fake the value a trigger would see with `{% set x = ... %}`.

## History, logbook and statistics

Keep the time window small; history is large. REST:

```bash
curl -s -H "$auth" "$api/history/period/2026-01-31T00:00:00Z?filter_entity_id=sensor.hall_temp&minimal_response&no_attributes"
curl -s -H "$auth" "$api/logbook/2026-01-31T00:00:00Z?entity=light.kitchen"
```

Websocket equivalents, which take several entities:

```bash
python3 ha_ws.py '{"type": "history/history_during_period", "start_time": "2026-01-31T00:00:00Z", "entity_ids": ["sensor.hall_temp"], "minimal_response": true, "no_attributes": true}'
python3 ha_ws.py '{"type": "logbook/get_events", "start_time": "2026-01-31T00:00:00Z", "entity_ids": ["light.kitchen"]}'
python3 ha_ws.py '{"type": "recorder/statistics_during_period", "start_time": "2026-01-01T00:00:00Z", "statistic_ids": ["sensor.energy"], "period": "day", "types": ["sum", "mean"]}'
```

Times are ISO 8601 in UTC. An empty `[]` or `{}` means no recorded change in that window (or the entity is excluded from the recorder), not an error. To see why an automation did or did not run, read its trace: `{"type": "trace/list", "domain": "automation", "item_id": "<automation id>"}`, then `trace/get` with the `run_id`.

## Websocket

`ha_ws.py` sits beside this file. It needs only `python3`, reads `SUPERVISOR_TOKEN` (or `HA_TOKEN` and `HA_WS_URL` outside the add-on), sends each JSON command you give it, and prints one line of JSON per result. A refused command prints `{"error": {...}}` and the exit status is 1. `--events N` waits for N events after a subscribing command (`render_template`, `subscribe_events`).

Other commands worth knowing: `get_states`, `get_services`, `get_config`, `call_service` (with `domain`, `service`, `service_data`, `target`), `config/entity_registry/update` (rename, move to an area, disable), `lovelace/config` (the default dashboard). The full list is in Home Assistant's developer documentation, "WebSocket API".

## Before you change anything

- Reading is free; changing is not. Say what you will call, on which entity, before a service that moves something physical (locks, covers, alarms, climate, valves).
- Check the configuration (`scripts/check-config.sh`) before a restart; reload one domain instead (`automation.reload`, `script.reload`, `template.reload`) when you can.
- Do not call `homeassistant.restart` or `homeassistant.stop` without the user's say.

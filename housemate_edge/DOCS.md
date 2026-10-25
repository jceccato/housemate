# Housemate (edge)

<!-- edge-only -->
The newest Housemate build, for testers. It may change or break between
releases; the stable add-on, **Housemate**, is the one to rely on.
<!-- /edge-only -->

## What it gives you

A **Housemate** panel in the sidebar (administrators only): code-server with
your `/config` open and [OpenCode](https://opencode.ai) in its terminal. Open a
terminal in the panel and run `opencode`, or use the OpenCode button in the
editor's title bar.

## Configuration

| Option | Meaning |
| ------ | ------- |
| `provider` | `go` for OpenCode Go, `zen` for OpenCode Zen. |
| `api_key` | Your key from [opencode.ai](https://opencode.ai). Optional with Zen, whose free models need none. |

The key is written to OpenCode's provider configuration when the add-on starts.
Besides the add-on's own private options and data, it is not put in the logs,
on a command line, or in your `/config`. Restart the add-on after changing an option.

OpenCode Go limits requests to an allowlist of IP addresses. If calls start
failing after your home address changes, check the allowlist on your account.

## What persists

Everything OpenCode and code-server keep (sessions, settings, sign-in) lives in
the add-on's own data folder and survives restarts and updates.

## Protection mode

Docker access is declared but stays off while the add-on's **Protection mode**
is on, which is the default. Turn it off only if you understand that the agent
then has root-level reach into the host.

## Versions

OpenCode and code-server are pinned and never update themselves. They change
only when the add-on does.

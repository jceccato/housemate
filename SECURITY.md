# Security policy

Housemate gives an AI agent access to a Home Assistant installation, so
security reports matter.

## Reporting a vulnerability

Please do **not** open a public issue. Use GitHub's private vulnerability
reporting: the **Security** tab of this repository, then **Report a
vulnerability**.

Include what you found, how to reproduce it, which add-on (stable or edge) and
version, and what an attacker gains. Do not include real credentials.

This is a one-person project with best-effort support. You will get an
acknowledgement when the maintainer can give one, and credit in the fix if you
want it.

## Supported versions

Only the current **stable** release and the current **edge** build get fixes.
Nothing has been released yet.

## What is in scope

The add-on's image, its start-up scripts, the kit it ships, and the workflows in
this repository. Vulnerabilities in OpenCode, code-server, Home Assistant or the
model providers belong with those projects.

## Things to know

The agent runs with Home Assistant API access and read-write access to
`/config`. Docker access exists but stays behind Home Assistant's protection
mode until the user turns it off. Treat the panel like an administrator's
terminal.

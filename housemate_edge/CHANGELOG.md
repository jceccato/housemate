# Changelog

## 0.1.13

- Update dependency coder/code-server to v4.143.1 (#13)

## 0.1.12

- Staged: pin code-server 4.141.1 so Renovate has a real minor bump to propose (#12)

## 0.1.11

- Open Housemate from notifications at /app/<slug>, the frontend route that exists
- Changelog: each build lists only the commits since the previous published build

## 0.1.10

- Orchestrator review fixes: gated tickets stay on the frontier, name the next commands up front, one script rule
- Orchestrator: follow a command the user has typed; keep the ticket's own status form
- Add the orchestrator skill: size a request, grill or yolo, work tickets through sub-agents
- Edge's panel is titled Housemate (edge); document the skills pin
- Stage a changed kit even when the kit version was not bumped

## 0.1.9

- Edge's panel is titled Housemate (edge); document the skills pin
- Stage a changed kit even when the kit version was not bumped

## 0.1.8

- Review fixes: name no lab in the notice, keep the kit's domain-docs line generic

## 0.1.7

- Refuse to stage without a kit directory; ignore staged paths outside /config
- Stage newer kit files as incoming, never overwriting, with an incoming-review skill

## 0.1.6

- Ship baseline skills and commands in the kit

## 0.1.5

- Voice review fixes: send a request once, tell once when done, honest reply

## 0.1.4

- Ignore Home Assistant's run lock; seen tracked on the test VM

## 0.1.3

- Note in the kick-off service that its callers are to be narrowed
- Tell the household when a job stops on an error
- Give OpenCode time to start in CI: wait for its server, longer waits for notifications
- Track a kick-off job before sending its request; restart test uses the add-on's own OpenCode server
- Kit review fixes: keep the shipped text as the compare base, honour an existing .gitignore
- Add the voice kick-off endpoint, blueprint and installer
- Add the starter kit, seeded once with a manifest, and git-init for /config

## 0.1.1

- Add the update pipeline: auto version bump after publish, promotion, Renovate
- Review fixes: test session survival for real, tighten claims and checks
- Publish per-architecture images, not a generic manifest
- Add the edge add-on, its image, Seam A tests and CI

## 0.1.0

- First edge build: code-server behind Ingress with OpenCode, your `/config`
  as the workspace, and the provider (OpenCode Go or Zen) set from the
  Configuration tab.

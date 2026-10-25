# Changelog

## 0.1.8

- Review fixes: name no lab in the notice, keep the kit's domain-docs line generic
- Refuse to stage without a kit directory; ignore staged paths outside /config
- Stage newer kit files as incoming, never overwriting, with an incoming-review skill

## 0.1.7

- Refuse to stage without a kit directory; ignore staged paths outside /config
- Stage newer kit files as incoming, never overwriting, with an incoming-review skill
- Ship baseline skills and commands in the kit

## 0.1.6

- Ship baseline skills and commands in the kit
- Voice review fixes: send a request once, tell once when done, honest reply

## 0.1.5

- Voice review fixes: send a request once, tell once when done, honest reply

## 0.1.4

- Ignore Home Assistant's run lock; seen tracked on the test VM
- Note in the kick-off service that its callers are to be narrowed
- Tell the household when a job stops on an error
- Give OpenCode time to start in CI: wait for its server, longer waits for notifications
- Track a kick-off job before sending its request; restart test uses the add-on's own OpenCode server
- Kit review fixes: keep the shipped text as the compare base, honour an existing .gitignore
- Add the voice kick-off endpoint, blueprint and installer
- Add the starter kit, seeded once with a manifest, and git-init for /config

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

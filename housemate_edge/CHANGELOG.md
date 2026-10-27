# Changelog

## 0.1.41

- Rules: never print the add-on's own info or options (they carry the key) (#44)

## 0.1.40

- Notification links name their chat; the panel opens it in front (#43)

## 0.1.39

- Update https://github.com/mattpocock/skills digest to 59db609 (#41)

## 0.1.38

- Open the marked chat in front; start onboarding by itself on the first open (#40)

## 0.1.37

- The panel re-asks a waiting question when chats are switched; restart recommendation (#39)

## 0.1.36

- The panel attaches to the add-on's OpenCode server and has a waiting question asked again (#38)

## 0.1.35

- Onboarding: five minutes, questions through the question tool, restart recommends now (#37)

## 0.1.34

- Small fixes: trim api_key and base_url, Zen needs no key, atomic progress write (#35)

## 0.1.33

- Kit changelog: describe kit version 1 as shipped (#36)

## 0.1.32

- Any OpenAI-compatible provider; Providers docs; upstream attribution (#34)

## 0.1.31

- Docs: onboarding's two voice questions, the real trial and the chats
- Onboarding: a real voice trial, where the chats are, and one status line per step
- Onboarding: ask to install voice and to restart as two questions

## 0.1.30

- Write the README and Docs tab for strangers; make the resume test deterministic (#32)

## 0.1.29

- DOCS: say how soon the panel reloads after a restart (#31)
- Reload the panel when the add-on has started afresh, not after a count of failures (#30)

## 0.1.28

- Load the reconnect helper from the Ingress prefix (#29)

## 0.1.27

- Update review: approvals do not outlive a stop or a quiet day; one progress file per review (#27)

## 0.1.26

- Update review: carry on by itself after a restart; current-session pointer (#26)

## 0.1.25

- Reopen OpenCode after an add-on restart, on the chat a job marked (#25)

## 0.1.24

- git-init: on a repository with history, commit only the ignore policy

## 0.1.23

- Open the panel straight into OpenCode (#23)

## 0.1.22

- Make the daily review's phone take effect without a restart

## 0.1.21

- Onboarding: the review-notify command marks the phone step done

## 0.1.20

- Onboarding: the phone step also sets review_notify for the daily update review

## 0.1.19

- Find an add-on's slug from the entity registry, not its picture (#19)

## 0.1.18

- Drop ingress_panel: the Supervisor ignores it in config.yaml; the docs say how to show the panel (#18)

## 0.1.17

- Review fixes: Core restart step, stable-channel and database-backup checks, honest delivery (#17)

## 0.1.16

- Onboarding: build the first automation in its own package and verify it; wait out the restart
- Add onboarding: a built-in skill, a first-open rule, and a scan that seeds the cheat sheet

## 0.1.15

- Reach the panel only through Ingress and the voice endpoint only from Core (#16)

## 0.1.14

- Add the daily update review: one summary, a briefed chat, two approvals (#15)

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

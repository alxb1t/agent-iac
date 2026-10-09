---
version: v0.3
---

# 0003-the-knowledge-base — the agent keeps a knowledge base the client reads in Obsidian

A box clones the deployment's private KB repo, the agent writes it and pushes every turn, and Hermes Desktop reaches
the box over the tailnet. Proven by the validators and template tests; the acceptance by hand comes later.

Read [design](design.md) for the decisions (`D1`–`D12`) and the files; the `box-contracts`, `box-apply` and `box-knowledge-base` deltas under `specs/`; [tasks](tasks.md)
for the phases.

## Why

v0.2 runs an agent whose knowledge stays in its own volume, where neither the client nor the operator can read it. A
knowledge base in a git repo the client owns fixes that: the agent writes it, git keeps its history off the box, and
Obsidian shows it on the client's Mac and phone. Hermes Desktop, the second way in beside Telegram, needs a port the
box does not publish yet.

## What Changes

- **The runtime manifest grows to six fields**: `environment:`, fixed non-secret variables, and `ports:`, published
  on the host's tailnet address only, per [D1](design.md#d1) and [D6](design.md#d6). The Hermes manifest's `env`
  gains the dashboard login, per [D2](design.md#d2).
- **`box.yaml` gains an optional `kb:`**, a GitHub SSH URL; when set, `KB_DEPLOY_KEY` is a required secret, per
  [D3](design.md#d3).
- **The deploy key reaches the agent as a Podman secret**, mounted as a file; git uses it with GitHub's pinned host
  keys and commits under the box's name, per [D4](design.md#d4) and [D5](design.md#d5).
- **Apply clones the KB once** into `/opt/data/kb`, per [D7](design.md#d7).
- **`git-hook` is vendored** at `a7303c8` into the base blueprint and enabled there; a test pins each file's hash,
  per [D8](design.md#d8). The base `SOUL.md` names the KB, per [D9](design.md#d9).
- **The docs change**: `docs/kb.md` for the client's Obsidian and the operator's KB repo; `README.md`,
  `docs/architecture.md` and `CLAUDE.md` say six fields, `kb:` and the dashboard, per [D11](design.md#d11).
- **The collection is `0.3.0`**, and the example pins `v0.3.0`, per [D12](design.md#d12).

## Capabilities

### New Capabilities

- `box-knowledge-base`: the one-time clone, the deploy key as a mounted file, the agent's commit identity, and the
  vendored sync plugin.

### Modified Capabilities

- `box-contracts`: `box.yaml` may carry `kb:`; the manifest holds six fields; `KB_DEPLOY_KEY` is required when `kb:`
  is set.
- `box-apply`: the service sets the manifest's environment and publishes its ports on the tailnet address only.

Each requirement the deltas touch:

- `box-contracts` · *box.yaml holds five fields* → removed; *box.yaml holds five fields and an optional kb* added.
- `box-contracts` · *A runtime manifest holds four fields* → removed; *A runtime manifest holds six fields* added.
- `box-contracts` · *Secrets are read only from the encrypted file* → modified: `KB_DEPLOY_KEY` when `kb:` is set.
- `box-apply` · *The agent runs rootless as a systemd user service* → modified: environment set, ports published on
  the tailnet address, instead of no port.
- `box-knowledge-base` · *The knowledge base is cloned once*, *The deploy key reaches the agent only as a mounted
  file*, *The agent commits under the box's name*, *The sync plugin ships with the base blueprint* → added.

## Impact

- New: `blueprints/base/plugins/git-hook/`, `blueprints/base/.ssh/kb_known_hosts`, `docs/kb.md`,
  `tests/test_vendored.py`.
- Edited: `plugins/module_utils/box_schema.py`, `plugins/action/box_load.py`, `runtimes/hermes.yaml`,
  `roles/box/tasks/host.yml`, `roles/box/tasks/box.yml`, `roles/box/templates/box.container.j2`,
  `blueprints/base/config.yaml`, `blueprints/base/SOUL.md`, `examples/box/`, `.ansible-lint`, `galaxy.yml`,
  `tests/conftest.py`, `tests/test_box_schema.py`, `tests/test_templates.py`, `README.md`,
  `docs/architecture.md`, `CLAUDE.md`.
- Dependencies: `hermes-git-hook` vendored at one commit, listed in [design](design.md#dependencies).

## Not in this change

Each item names the trigger that brings it in, never a date.

- **Acceptance by hand** — the version that accepts all of v1 at once.
- **A backup of the KB** — never by the box: its git remote, with its history, is the backup.
- **A KB seed or schema** — when a trade's blueprint needs one; it lives in that client's `blueprint/`.
- **A KB host other than GitHub** — when a client's KB lives elsewhere; its host keys come with it.
- **Obsidian Sync, Syncthing** — when a minute of git latency feels broken.
- **The command, uid and state mounts in the manifest** (backlog 0002·R10) — when a second runtime is added.
- **The client's bucket, the age key per client, the onboarding checklist** — when a box leaves the operator's hands.
- **The fence** — when v1 is in use.

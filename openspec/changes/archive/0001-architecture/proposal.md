---
version: v0.1
---

# 0001-architecture — the product on paper

agent-iac becomes readable: one architecture page, the repo's invariants and vocabulary, and the backlog of what
is deliberately left out. No code.

Read [design](design.md) for the decisions (`D1`–`D12`) and the text to place; [tasks](tasks.md) for the phases.

## Why

The repo is a bootstrapped skeleton with a one-line `README.md`. Nothing in it says what agent-iac is, what a box
is, what an agent must declare to run in one, or what the repo refuses to do. The next change writes the first
Ansible role; it needs those contracts fixed first, in the repo, where the build reads them.

## What Changes

- `CLAUDE.md` gains an `## Invariants` section (the rules every change holds) and a `## Vocabulary` section (the
  five words), per [D10](design.md#d10).
- `docs/architecture.md` is created: the essence, the box diagram, the host, the two tiers, the `box.yaml`
  contract, the runtime manifest with the Hermes manifest written out, the repos and the sync of the knowledge
  base, per [D1](design.md#d1)–[D9](design.md#d9).
- `.minions/backlog.md` is written with the cards this change defers, each with its trigger, per
  [D11](design.md#d11). The file is gitignored by the line's convention; the same items are listed below.

## Capabilities

### New Capabilities

None. This change is documentation; `.openspec.yaml` declares `skip_specs: true`, per [D12](design.md#d12).

### Modified Capabilities

None.

## Impact

- `CLAUDE.md` — two sections appended; the template text above them stays byte for byte.
- `docs/architecture.md` — new.
- `.minions/backlog.md` — new, untracked.
- The gate (`openspec validate`) is unaffected: no spec, no code.

## Not in this change

Each item names the trigger that brings it in, never a date.

- **A role, a playbook, a Makefile target** — the next change, which turns a Raspberry Pi into a box.
- **The fence** (an egress proxy, nftables outbound, `tier` and `egress` in `box.yaml`) — when a box runs.
- **A client's bucket, prune, `make login`, node sharing** — when a box leaves the operator's hands.
- **The knowledge base in the blueprint** (`llm-wiki`, the `obsidian` skill, `git-hook`, the KB clone) — when a
  box is fenced and handed over.
- **A second runtime** (Claude Code as a job; `run` in the manifest) — when a second runtime is wanted.
- **`healthcheck` in the manifest, a dead-man ping, alerts** — when a box must be watched.
- **An LLM gateway with budgeted keys** — when a bill runs away, or a client has no provider-side cap.
- **A team runtime (Paperclip), per-container limits** — when someone wants a team on one box.
- **A CLI** — when the Make targets stop moving.
- **A VPS target** (`contrib/hetzner-alpine.sh`) — when the first VPS box is wanted.
- **The sealed tier** (logs off-box, read-only root, approval outside the model) — the first high-risk client.
- **The base blueprint as its own repo and Hermes distribution** — when someone wants it without agent-iac.
- **`fleet-index` and `apply-all`** — the fourth box.
- **Tailscale ACL tags · a WireGuard overlay · LUKS on a Pi · another systemd-free host OS · the Airgap reader as a
  skill · Syncthing as the KB sync** — each with its trigger in the backlog.
- **`memory-diff` · `operator-root` · `image-provenance`** — the threat model's three priorities, triggered by the
  first live KB, the first client box, and the first upgrade that breaks a box.
- **`README.md`** — stays one line; it gets its pitch when there is something to run.

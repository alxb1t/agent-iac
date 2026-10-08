---
version: v0.2
---

# 0002-the-box — one `make apply` makes a Pi a box

The first code: an Ansible collection whose one role turns a Raspberry Pi OS host on the tailnet into a box running
the official Hermes image rootless under a quadlet, with secrets from sops, a nightly restic backup and a one-step
restore. Proven by lint and template tests; the acceptance by hand comes later.

Read [design](design.md) for the decisions (`D1`–`D16`) and the files; the four deltas under `specs/`; [tasks](tasks.md)
for the phases.

## Why

v0.1 put the product on paper. Nothing runs. The next versions (the fence, the host, the knowledge base) each add
to a role that must exist first, and a client's Pi waits on it. This change writes that role and the tooling around
it, as small as the paper allows.

## What Changes

- **A collection** `alxb1t.agent_iac` with one role `box`, the playbooks `apply`, `status`, `backup`, `restore` and
  `restore_drill`, the Hermes runtime manifest, the base blueprint, an example box repo and
  `contrib/bootstrap-pi.sh`, per [D1](design.md#d1)–[D3](design.md#d3).
- **The host side of the role**: apt packages, `unattended-upgrades`, the box user with linger and subuids,
  Tailscale ensured up, an nftables ruleset closed to the tailnet, the backup on cron, per [D4](design.md#d4)–[D6](design.md#d6).
- **The box side**: the env file decrypted from sops, the named volume, the blueprint copied in (base, then the
  deployment's overlay), one quadlet running the pinned image as a systemd user service, per
  [D7](design.md#d7)–[D10](design.md#d10).
- **Backup and restore**: stop, `restic backup`, start, on cron at 04:00; a one-step restore; a restore drill;
  `status`, per [D11](design.md#d11)–[D12](design.md#d12).
- **The gate grows**: `yamllint`, `ansible-lint`, `ansible-playbook --syntax-check`, `pytest` over every template,
  the `box.yaml` validator and a sops round-trip, per [D13](design.md#d13)–[D14](design.md#d14).
- **The docs change** — `pre_backup` leaves the runtime manifest, now four fields; the host is Raspberry Pi OS;
  `docs/architecture.md`, `CLAUDE.md`'s invariants and vocabulary follow; `README.md` gets its pitch and the setup
  steps; `docs/host.md` is the "a host exists" checklist, per [D15](design.md#d15)–[D16](design.md#d16).

## Capabilities

### New Capabilities

- `box-contracts`: what `box.yaml` and a runtime manifest declare, and how an invalid one is refused.
- `box-apply`: what `apply` guarantees on the host and in the container, and that a second apply changes nothing.
- `box-backup`: the nightly snapshot, the one-step restore, the drill, and `status`.
- `pi-bootstrap`: what the hand-run bootstrap script leaves on a freshly flashed Pi.

### Modified Capabilities

None. `openspec/specs/` is empty.

## Impact

- New: `galaxy.yml`, `pyproject.toml`, `requirements.yml`, `roles/box/`, `playbooks/`, `plugins/`,
  `runtimes/hermes.yaml`, `blueprints/base/`, `examples/box/`, `contrib/bootstrap-pi.sh`, `tests/`, `docs/host.md`.
- Edited: `Makefile` (the gate recipe), `.gitignore`, `docs/architecture.md`, `CLAUDE.md` (two lines), `README.md`.
- Dependencies: Python packages and Ansible collections listed in [design](design.md#dependencies); `sops`, `age`
  and `restic` binaries on the operator's machine.

## Not in this change

Each item names the trigger that brings it in, never a date.

- **Acceptance by hand** — the version that accepts all of v1 at once.
- **The fence** (an egress proxy, nftables outbound, `tier` and `egress` in `box.yaml`) — when a box runs.
- **A client's bucket with a no-delete key, prune, `make login`, node sharing** — when a box leaves the operator's
  hands.
- **`llm-wiki`, the `obsidian` skill, `git-hook`, the knowledge-base clone** — when the box is fenced and handed over.
- **Any published port**, the API server, the dashboard — when a client needs Hermes Desktop.
- **`healthcheck` in the manifest** — when a box must be watched.
- **Alpine as the host** — when a headless install a client can do alone is proven.
- **Tailscale SSH in place of sshd** — a second operator.
- **A bind mount with `:U` instead of the named volume** — when the `podman unshare` path bites.

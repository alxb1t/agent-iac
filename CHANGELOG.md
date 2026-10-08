# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0/).

## [Unreleased]

### Added

- The collection `alxb1t.agent_iac` skeleton, the `uv` tooling, `box_load` and the `box.yaml` and manifest validators, so a bad `box.yaml` is refused before any connection.
- `make gate` runs yamllint, ansible-lint, a playbook syntax check and pytest after the spec check.
- The host side of the `box` role: packages, unattended upgrades, the box user with linger and subuids, Tailscale ensured up, then an inbound ruleset closed to the tailnet, and the backup cron line.
- The box side: the env file from sops, the volume, the base blueprint overlaid by the deployment's, the pinned image as a rootless quadlet, and `apply` running the role; a sops round-trip test with a throwaway age key.
- Backup by stop, snapshot, start at 04:00, with the start in a `trap`; `restore`, `restore_drill` and `status`; `apply` initialises the restic repository and names the SFTP key to authorise.
- `examples/box/`, `contrib/bootstrap-pi.sh` and `docs/host.md`: a deployment repo to copy and the one page a Pi's holder follows.

### Changed

- The host is Raspberry Pi OS with the agent as a quadlet user service; the runtime manifest drops `pre_backup` and has four fields. `docs/architecture.md`, `CLAUDE.md` and `README.md` say so.

### Fixed

- `restore` restores only the volume, into the volume, so its `--delete` no longer empties the box user's home.
- `apply` reloads systemd on every run, so an apply that failed after writing the quadlet no longer leaves the next one unable to start the service.
- The blueprint sync copies the staged entries without directory times, so the agent's own writes no longer restart it on every apply.
- `community.sops` and `community.general` are pinned to one exact version each, not ranges.
- Task 5.6's halt check reads the names it refuses from a file kept out of the repo, instead of spelling them out.

## [0.1.0] - 2026-10-07

### Added

- `CLAUDE.md`: the invariants every change holds and the vocabulary (box, target, runtime, tier, blueprint).
- `docs/architecture.md`: the architecture page — the essence, the box, the host, the `runtimes/hermes.yaml` and `box.yaml` contracts, secrets and backups, the tiers, the repos.
- The items deferred from the architecture are listed with their triggers in the `0001-architecture` proposal.

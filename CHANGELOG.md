# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0/).

## [Unreleased]

## [0.3.0] - 2026-10-09

### Added

- `box.yaml` takes an optional `kb:`, a GitHub SSH URL; with it, `KB_DEPLOY_KEY` is a required secret, so a KB without its key is refused before any connection.
- The quadlet sets the manifest's environment and publishes its ports on the host's tailnet address only, read by `tailscale ip -4` at each apply. With `kb:` it mounts the deploy key as a Podman secret, and git trusts only GitHub's host keys, pinned in `blueprints/base/.ssh/kb_known_hosts`, and commits under the box's name. The base blueprint's `.ssh/config` names the same key and pin, so the `git-hook` plugin's pulls and pushes, which set their own `GIT_SSH_COMMAND`, use them too.
- With `kb:`, `apply` stores the deploy key as the box user's Podman secret, replaced only when its hash changes, and clones the KB into `/opt/data/kb` as the agent's user once; an existing clone is never touched. A running box restarts on its new quadlet before the clone, so adding `kb:` to it clones with the key mounted.
- `docs/kb.md`: the operator's KB repo, its deploy key and a ruleset blocking force-pushes and deletion, the client's Obsidian, and Hermes Desktop on `<target>:9119`. It warns that a deployment's own `config.yaml` or `SOUL.md` must keep `git-hook` and the KB paragraph, and that an existing `/opt/data/kb` must be moved aside before adding `kb:`. The example's `SOUL.md` names the KB.
- The base blueprint vendors the `git-hook` Hermes plugin at `a7303c8` and enables it, so the agent's KB edits are pushed each turn; `tests/test_vendored.py` pins every file by hash. The base `SOUL.md` names the KB.

### Changed

- The runtime manifest has six fields: `environment` and `ports` join it, so a runtime declares its fixed variables and ports. The Hermes manifest sets the KB paths and the dashboard, and requires the dashboard login.
- The collection is `0.3.0`; the example pins `v0.3.0`, sets `kb:` and holds every secret it now needs. `README.md`, `docs/architecture.md` and `CLAUDE.md` say six fields, `kb:` and the dashboard.

## [0.2.0] - 2026-10-08

### Added

- The collection `alxb1t.agent_iac` skeleton, the `uv` tooling, `box_load` and the `box.yaml` and manifest validators, so a bad `box.yaml` is refused before any connection.
- `make gate` runs yamllint, ansible-lint, a playbook syntax check and pytest after the spec check.
- The host side of the `box` role: packages, unattended upgrades, the box user with linger and subuids, Tailscale ensured up, then an inbound ruleset closed to the tailnet, and the backup cron line.
- The box side: the env file from sops, the volume, the base blueprint overlaid by the deployment's, the pinned image as a rootless quadlet, and `apply` running the role; a sops round-trip test with a throwaway age key.
- Backup by stop, snapshot, start at 04:00, with the start in a `trap`; `restore`, `restore_drill` and `status`; `apply` initialises the restic repository and names the SFTP key to authorise.
- `examples/box/`, `contrib/bootstrap-pi.sh` and `docs/host.md`: a deployment repo to copy and the one page a Pi's holder follows.

### Changed

- The host is Raspberry Pi OS with the agent as a quadlet user service; the runtime manifest drops `pre_backup` and has four fields. `docs/architecture.md`, `CLAUDE.md` and `README.md` say so.

### Removed

- The `community.sops` collection dependency: `box_load` runs the `sops` binary itself.

### Fixed

- `restore` restores only the volume, into the volume, so its `--delete` no longer empties the box user's home.
- `apply` reloads systemd on every run, so an apply that failed after writing the quadlet no longer leaves the next one unable to start the service.
- The blueprint sync copies the staged entries without directory times, so the agent's own writes no longer restart it on every apply.
- `community.general` is pinned to one exact version, not a range.
- Task 5.6's halt check reads the names it refuses from a gitignored file, instead of spelling them out, and fails when that file is missing or empty.
- A backup whose closing start fails now exits non-zero, so cron and the playbook no longer report success with the agent down.
- Reloading the ruleset replaces only its own `inet filter` table, so Tailscale's own chains survive it.
- The quadlet reads its env file from `box_config`, the same path the env file is written to.
- The blueprint sync hands rsync each entry as `./<entry>`, so a name with a colon is never read as a remote host.
- The Tailscale auth key reaches `tailscale up` in a root-only file, never on a command line; `docs/host.md` reads it at a prompt, out of the shell's history.
- `contrib/bootstrap-pi.sh` installs Tailscale from its apt repository behind the signing key pinned by SHA-256, not by piping the vendor's install script into a root shell.
- `docs/architecture.md` says the box's SFTP key can delete its snapshots in this version, and its diagram drops the gateway port the box does not publish.

## [0.1.0] - 2026-10-07

### Added

- `CLAUDE.md`: the invariants every change holds and the vocabulary (box, target, runtime, tier, blueprint).
- `docs/architecture.md`: the architecture page — the essence, the box, the host, the `runtimes/hermes.yaml` and `box.yaml` contracts, secrets and backups, the tiers, the repos.
- The items deferred from the architecture are listed with their triggers in the `0001-architecture` proposal.

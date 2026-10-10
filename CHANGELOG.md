# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0/).

## [Unreleased]

## [0.4.0] - 2026-10-10

### Added

- `docs/host.md` opens with the onboarding: the client's R2 bucket, its four-day lock rule and a bucket-scoped token; the client's age key beside the operator's; a `tag:box` auth key and a tailnet policy under which the box reaches nothing; then the node's share and a terminal provider login. `examples/box/RESTORE.md` shows the client `make restore` and the restore by hand with `age -d` and `hermes import`.

### Changed

- The runtime manifest has eight fields: `backup` and `restore` join it, each a command line holding `{archive}` once, so a runtime declares how it archives and restores itself. `box.yaml`'s `backup` is an R2 bucket, `r2:<account-id>/<bucket>`; the R2 key pair replaces `RESTIC_PASSWORD` among the required secrets.
- `box_load` reads the age recipients of `.sops.yaml` beside `box.yaml` and refuses a file naming none, so the archives go to the same keys as the secrets.
- The nightly backup no longer stops the agent: `box-backup` runs the manifest's `backup` in the container, pipes the zip through `age` to the recipients and `rclone rcat`s it to R2, then keeps the newest five; a delete the bucket's lock refuses is a warning, not a failure.
- The host carries `age` and `rclone` instead of `restic`; `apply` writes the rclone env and the recipients, and removes the restic env file with its password.
- `restore` and `restore-drill` fetch and decrypt the archive on the machine running `make`, so the box never holds a private key. `restore` stops the service, imports the archive in a one-off container and starts it again on every exit; with `kb:`, it then clones the KB afresh through the role's new `kb.yml`. `-e box_archive=<file>` picks an archive.
- `restore-drill` imports into a scratch volume and checks `state.db`'s integrity, its `sessions` table and `config.yaml`, printing the session count, instead of diffing against a live state that has moved on. `status`'s third line names the newest archive.
- `bootstrap-pi.sh` takes only the operator's SSH public key and reads the Tailscale auth key from the terminal without echo, so the key is on no command line and `curl … | sudo sh -s -- "<key>"` still works. Tailscale's signing key downloads to a temporary file and reaches the keyring path only after its hash checks.
- The collection is `0.4.0`; the example pins `v0.4.0`, gains `make restore`, backs up to an R2 bucket, and encrypts its secrets to an operator's and a client's throwaway key. `docs/kb.md` says to set the ruleset **Active**. `README.md` and `docs/architecture.md` say eight fields, R2 and the client's key; `CLAUDE.md` says eight fields.

### Fixed

- A box lists its archives as `<name>-<timestamp>.zip.age` with the timestamp's shape spelt out, so the keep-five, `restore`, `restore-drill` and `status` of `example` never touch or pick the archives of a box named `example-two` in the same bucket.
- `restore` and `restore-drill` reach the box before decrypting, and remove the decrypted archive from the machine running them as soon as it is copied to the box, even when the box drops during the copy.
- `restore` and `restore-drill` stop with "no age identity" when neither `SOPS_AGE_KEY_FILE` nor sops' default key file exists, instead of failing later at the decrypt.
- `restore` and `restore-drill` name the archive they picked, and stop on a newest archive dated in the future, which a compromised box could have planted; `RESTORE.md` and `docs/host.md` say to rotate the R2 token and name an archive from before the compromise.
- `box_load` refuses a box not named `example` whose `.sops.yaml` keeps a throwaway key of `tests/keys/`, whose private half is public, so a copied example never encrypts secrets and archives to it.
- `box-backup` logs an error when the rclone env file is missing or unreadable, instead of exiting with no line in the system log.
- `apply` removes the SFTP key, the ssh `config` and the `known_hosts` that v0.3's backup left in the box user's `~/.ssh`. On upgrading a v0.3 box, also remove its key, `<name>-backup`, from the old backup host's `authorized_keys`.
- The onboarding's tailnet policy admits the client the node is shared with, `autogroup:shared`, to the box's dashboard and SSH; the hand-over adds the client's SSH public key to root's, so the client can run `make restore` alone, as `RESTORE.md` says.
- `docs/kb.md` says `make restore` clones the KB afresh, so unpushed KB files are not restored; `docs/architecture.md` says the restore drill gates the acceptance by hand, not a release; the `box-backup` spec's purpose names the encrypted archive, not a snapshot.

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

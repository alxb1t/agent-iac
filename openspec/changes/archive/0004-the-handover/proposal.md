---
version: v0.4
backlog: [0002·S8, 0002·R15, 0002·R16, 0003·R5, 0003·S3, 0002·R11, 0002·R17]
---

# 0004-the-handover — a client restores and applies without the operator

A box's backups land in the client's own R2 bucket, encrypted so the client or the operator can open them, and the
client can restore alone. restic leaves; the runtime's own backup command, `age` and `rclone` replace it. Proven by
the validators and script tests; the acceptance by hand comes later.

Read [design](design.md) for the decisions (`D1`–`D15`) and the files; the `box-contracts`, `box-apply`,
`box-backup` and `pi-bootstrap` deltas under `specs/`; [tasks](tasks.md) for the phases.

## Why

v0.3's backup is a restic repository on a host the operator runs, pruned by hand from the operator's Mac: a client
cannot restore without the operator, and a prune nobody remembers never runs. Self-contained archives in the client's
bucket, encrypted to the client's key and the operator's, trimmed by the box and locked by the bucket, need no
chore and no operator. This is the last step before a client gets a box.

## What Changes

- **BREAKING** **restic leaves.** Nightly cron runs the manifest's `backup` command with the agent up, encrypts the
  archive with `age` to the deployment's recipients, uploads it with `rclone` to R2, and keeps the newest five, per
  [D5](design.md#d5)–[D7](design.md#d7). A `box.yaml` `backup:` is now `r2:<account-id>/<bucket>`, per
  [D2](design.md#d2).
- **The manifest grows to eight fields**: `backup` and `restore`, the runtime's own command lines, per
  [D1](design.md#d1).
- **The recipients come from the deployment's `.sops.yaml`**, the same keys its secrets are encrypted to, per
  [D3](design.md#d3). The R2 key pair replaces `RESTIC_PASSWORD` among the required secrets, per [D2](design.md#d2).
- **Restore runs from the operator's or the client's machine**: fetch the newest archive, decrypt it there, import
  it into the stopped volume, re-clone the KB, per [D8](design.md#d8) and [D9](design.md#d9). The drill imports into
  a scratch volume and checks the database, per [D10](design.md#d10). `status` names the newest archive, per
  [D11](design.md#d11).
- **The bootstrap reads the Tailscale auth key from the terminal**, never an argument, and checks the keyring before
  apt trusts it, per [D12](design.md#d12).
- **The docs change**: `docs/host.md` gains the onboarding checklist — the client's Cloudflare bucket, lock rule and
  token, the client's age key, the tagged auth key, the Tailscale ACL, the shared node, terminal logins — and links
  `docs/kb.md`; `examples/box/RESTORE.md` is the client's restore; `README.md`, `docs/architecture.md` and
  `CLAUDE.md` follow, per [D13](design.md#d13).
- **The collection is `0.4.0`**, per [D14](design.md#d14).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `box-contracts`: `backup` is an R2 URL; the manifest holds eight fields; the R2 key pair is required; the
  recipients are read from `.sops.yaml`.
- `box-apply`: the host carries `age` and `rclone`, not `restic`.
- `box-backup`: archive, encrypt and upload replace stop-snapshot-start; the box keeps five; restore and the drill
  import an archive.
- `pi-bootstrap`: the auth key is read from the terminal.

Each requirement the deltas touch:

- `box-contracts` · *box.yaml holds five fields and an optional kb* → modified: `backup` is `r2:<account-id>/<bucket>`.
- `box-contracts` · *A runtime manifest holds six fields* → removed; *A runtime manifest holds eight fields* added.
- `box-contracts` · *Secrets are read only from the encrypted file* → modified: `R2_ACCESS_KEY_ID` and
  `R2_SECRET_ACCESS_KEY` instead of `RESTIC_PASSWORD`.
- `box-contracts` · *The backup recipients are the secrets' recipients* → added.
- `box-apply` · *Apply converges the host* → modified: `age` and `rclone` instead of `restic`.
- `box-backup` · *Nightly backup by stop, snapshot, start* → removed; *Nightly backup by archive, encrypt, upload*
  added.
- `box-backup` · *The box keeps the newest five archives* → added.
- `box-backup` · *Restore is one step* → modified: the newest archive, decrypted off the box, imported, the KB
  re-cloned.
- `box-backup` · *The restore drill proves a snapshot* → removed; *The restore drill proves an archive* added.
- `box-backup` · *Status is three lines* → modified: the newest archive's time.
- `pi-bootstrap` · *The bootstrap script joins the tailnet and admits the operator* → modified: the auth key from the
  terminal.

## Impact

- New: `examples/box/RESTORE.md`, `roles/box/tasks/kb.yml`, `roles/box/templates/rclone.env.j2`,
  `tests/keys/example-client.age`, `tests/test_bootstrap.py`.
- Removed: `roles/box/templates/restic.env.j2`.
- Edited: `plugins/module_utils/box_schema.py`, `plugins/action/box_load.py`, `runtimes/hermes.yaml`,
  `roles/box/defaults/main.yml`, `roles/box/tasks/box.yml`, `roles/box/tasks/backup.yml`,
  `roles/box/templates/box-backup.sh.j2`, `playbooks/backup.yml`, `playbooks/restore.yml`,
  `playbooks/restore_drill.yml`, `playbooks/status.yml`, `contrib/bootstrap-pi.sh`, `examples/box/`, `galaxy.yml`,
  `tests/conftest.py`, `tests/test_box_schema.py`, `tests/test_templates.py`, `tests/test_plays.py`,
  `docs/host.md`, `docs/kb.md`, `docs/architecture.md`, `README.md`, `CLAUDE.md`.
- Dependencies: `age` and `rclone` from apt on the host; `age` and `rclone` on the operator's machine; `restic`
  dropped. Listed in [design](design.md#dependencies).

## Not in this change

Each item names the trigger that brings it in, never a date.

- **Acceptance by hand** — the version that accepts all of v1 at once.
- **A backup of the KB** — never by the box: its git remote, with its history, is the backup.
- **Automating Cloudflare or Tailscale** (OpenTofu, Tailscale as code) — a second operator, or the hand-written ACL
  drifts.
- **The box on the client's own tailnet** — a client who wants to own it.
- **`make login`** — dropped: a terminal-login provider gets one documented line.
- **The command, uid and state mounts in the manifest** (backlog 0002·R10) — a second runtime.
- **The subuid range** (backlog 0002·R7) — a second user on the host running rootless containers.
- **The fence** — when v1 is in use.

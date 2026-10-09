# 0004-the-handover — design

How a box backs up to the client's bucket without stopping, how the client or the operator restores alone, and how
the gate proves it without a host. Verdict: build it phase by phase, as [tasks](tasks.md) orders; nothing by hand.

## Context

The backup today is restic: `restic` among `box_packages` (`roles/box/defaults/main.yml:11`), `box-backup` stops the
service and runs `podman unshare restic backup` (`roles/box/templates/box-backup.sh.j2:12-17`), `backup.yml`
initialises the repository behind an SFTP key (`roles/box/tasks/backup.yml:20-70`). `box.yaml`'s `backup` must be a
restic URL and `RESTIC_PASSWORD` is required (`plugins/module_utils/box_schema.py:17,22,58`); `restore.yml`,
`restore_drill.yml` and `status.yml` read restic through `box_restic_env`.

Facts read at the cut:
- **The image** sets `HERMES_HOME=/opt/data`, puts `hermes` on `PATH`, and its `state.db` has a `sessions` table.
  `hermes backup -o <zip>` is safe while the gateway runs; it leaves out `.git` and its own `backups/` folder.
  `hermes import --force <zip>` refuses a database a live process holds, so it runs with the service stopped.
- **R2** lock rules block delete and overwrite by age and win over lifecycle rules; only an *Admin* token edits
  bucket configuration. An R2 API token is a key pair: an access key id and a secret.
- **rclone 1.60.1** and `age` are in Trixie for arm64.
- **The KB clone** runs only into an empty folder (`roles/box/tasks/box.yml:173-189`), and an archive holds `kb/`
  without `.git`.

## Goals / Non-Goals

**Goals:**
- No chore: the box trims its own archives, the bucket locks the newest.
- The client restores from their repo with their own key, or by hand with `age` and `hermes import`.
- Every script and validator tested on the operator's machine.

**Non-Goals:**
- Running a backup against a real bucket in the gate.
- Creating the bucket, the lock rule, the token or the ACL: they are hand steps in `docs/host.md`.

## Decisions

### D1 — The manifest grows to eight fields

| id | decision | because | rejected |
|---|---|---|---|
| D1 | `MANIFEST_KEYS` gains `backup` and `restore`; each a non-empty list of strings holding `{archive}` exactly once; `validate_manifest` refuses anything else, naming the field | the role stays generic: a runtime declares how it archives and restores itself | a shell string (quoting); a `pre_backup` hook (gone in v0.2) |

```yaml
# runtimes/hermes.yaml — the lines this change adds
backup: [hermes, backup, -o, "{archive}"]
restore: [hermes, import, --force, "{archive}"]
```

### D2 — `backup:` and the R2 secrets

| id | decision | because | rejected |
|---|---|---|---|
| D2 | `backup` must match `^r2:[0-9a-f]{32}/[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$` (`RESTIC_URL` goes); `HOST_SECRETS` becomes `TAILSCALE_AUTH_KEY · R2_ACCESS_KEY_ID · R2_SECRET_ACCESS_KEY` | the account id names the endpoint; an R2 token is a key pair | any S3 URL (one provider is tested); keeping restic URLs beside it |

### D3 — The recipients

| id | decision | because | rejected |
|---|---|---|---|
| D3 | a pure `read_recipients(sops_config) -> (list[str], list[str])` in `box_schema.py` returns the age keys of `.sops.yaml`'s first creation rule — a comma-separated string or a list — and the errors: none, or one not matching `^age1[0-9a-z]{58}$`; `box_load` reads `.sops.yaml` beside `box.yaml`, fails on an error naming `.sops.yaml`, and passes `box_recipients`; `backup.yml` writes them one per line to `<box_config>/<name>.recipients`, mode `0644` | one list of keys for the secrets and the archives; at least one, so the operator's own box needs no client | a `recipients` field in `box.yaml` (a second list to drift) |

### D4 — The host side

| id | decision | because | rejected |
|---|---|---|---|
| D4 | `box_packages`: `restic` → `age`, `rclone`; `box_restic_env` → `box_rclone_env: <box_config>/<name>.rclone.env`, rendered from the new `rclone.env.j2` (mode `0600`, `no_log`) as `RCLONE_CONFIG_R2_TYPE=s3`, `…_PROVIDER=Cloudflare`, `…_ACCESS_KEY_ID`, `…_SECRET_ACCESS_KEY`, `…_ENDPOINT=https://<account-id>.r2.cloudflarestorage.com`, `…_NO_CHECK_BUCKET=true`; `restic.env.j2` is deleted; `backup.yml` drops the SFTP key, `restic init` and the SFTP `ssh` config, and removes `<name>.restic.env` | rclone reads a remote wholly from env, so no config file holds a key; the token cannot create buckets, so rclone must not try | `aws` CLI (heavier); `curl` with SigV4 by hand |

### D5 — The nightly script

```
/usr/local/bin/box-backup <name>   (bash, set -euo pipefail; root, from /etc/cron.d/box-<name> at 04:00)
  su - box:
    podman exec --user 10000 <name> <backup argv, {archive} = <blueprint_mount>/backups/agent-iac.zip>
    podman unshare cat <volume>/backups/agent-iac.zip | age -R <name>.recipients | rclone rcat r2:<bucket>/<name>-<ts>.zip.age
    trap: podman exec --user 10000 <name> rm -f <blueprint_mount>/backups/agent-iac.zip
  keep five: rclone lsf --files-only --include '<name>-*.zip.age' r2:<bucket> | sort | head -n -5
             → rclone deletefile each; a refused delete → logger -p user.warning, carry on
  any other failure → logger -p user.err, exit 1
```

| id | decision | because | rejected |
|---|---|---|---|
| D5 | the script above; `<ts>` is `date -u +%Y%m%dT%H%M%SZ`, so names sort by time; the plaintext zip exists only in the volume, inside `backups/` which `hermes backup` skips, and is removed on every exit | no stop: `hermes backup` copies SQLite safely; no plaintext on the host disk; a dead box deletes nothing | stopping the service (v0.2's way); trimming by a lifecycle rule (it outlives a dead box) |

### D6 — The lock

| id | decision | because | rejected |
|---|---|---|---|
| D6 | the onboarding sets one bucket lock rule, no prefix, 4 days; the box's token is *Object Read & Write* scoped to the bucket | the newest four nights survive a compromised box; the box cannot lift the lock | a lock longer than five nights (every keep-five delete would be refused) |

### D7 — Where decryption happens

| id | decision | because | rejected |
|---|---|---|---|
| D7 | `restore` and `restore-drill` fetch and decrypt on the machine running `make`, in a `0700` temp folder removed in an `always:`: `rclone` with the R2 secrets as task `environment` (`no_log`), then `age -d -i <identity>`; the identity is `$SOPS_AGE_KEY_FILE`, else `~/Library/Application Support/sops/age/keys.txt`, else `~/.config/sops/age/keys.txt` — the file sops already uses | the box holds public keys only; the client's machine and the operator's both hold one private key | decrypting on the box (a stolen Pi could read every archive) |

### D8 — Restore

| id | decision | because | rejected |
|---|---|---|---|
| D8 | the zip is copied to `<box_config>/<name>/restore.zip` (mode `0644` in the `0700` folder); the service is stopped; the import runs in a one-off container: `podman run --rm --user 10000 --entrypoint <restore[0]> -v <name>-data:<blueprint_mount> -v <zip>:/tmp/agent-iac-restore.zip:ro <image>:<version> <restore[1:], {archive} = /tmp/agent-iac-restore.zip>`; then, with `kb`, `podman unshare rm -rf <volume>/kb`; the start and the zip's removal are in an `always:`; then the clone of [D9](#d9); `-e box_archive=<name>` picks one archive | a stopped service holds no database; `--user 10000` keeps file ownership; the KB comes back with its history | `podman exec` (the service must be stopped); keeping the archive's `kb/` (no `.git`, and the clone refuses a full folder) |

### D9 — The KB clone, shared

| id | decision | because | rejected |
|---|---|---|---|
| D9 | the *Clone the KB once* block moves from `box.yml` to `roles/box/tasks/kb.yml`; `box.yml` imports it after the handler flush; `restore.yml` includes it with `include_role: {name: alxb1t.agent_iac.box, tasks_from: kb.yml}` after the start | one clone, one guard, used by apply and restore | a second copy of the tasks |

### D10 — The drill

| id | decision | because | rejected |
|---|---|---|---|
| D10 | fetch and decrypt per [D7](#d7); on the box, `podman volume create <name>-drill`, the import of [D8](#d8) into it, then `podman run --rm --user 10000 --entrypoint python3 -v <name>-drill:<blueprint_mount> <image>` with a check that `PRAGMA integrity_check` returns `ok`, a `sessions` table exists and `config.yaml` exists, printing `sessions: <n>` and exiting non-zero naming the failed check; `podman volume rm -f <name>-drill` and the zips' removal in an `always:` | it proves the archive, not a diff against a state that moved (0002·R11); an unused box passes | requiring sessions above zero (a fresh box fails) |

### D11 — Status

| id | decision | because | rejected |
|---|---|---|---|
| D11 | the third line is `archive: <newest name>` from `rclone lsf … \| sort \| tail -n 1` as the box user with its rclone env, or `archive: none` | the SFTP key line goes with SFTP | a size or count line |

### D12 — The bootstrap

| id | decision | because | rejected |
|---|---|---|---|
| D12 | `bootstrap-pi.sh` takes one argument, the operator's SSH public key; it reads the auth key with `stty -echo` from `/dev/tty`, so `curl … \| sudo sh -s -- "<key>"` still prompts; the keyring downloads to a `mktemp` file, its hash is checked, and only then is it `install`ed to the keyring path | the key never shows on a command line (0002·R16) and the bootstrap is one command again (0002·R15); a cut-short download never reaches the path apt trusts (0002·S8) | rewording the released changelog |

### D13 — The docs

| id | decision | because | rejected |
|---|---|---|---|
| D13 | `docs/host.md`: an onboarding section before the Pi — the client's Cloudflare account, a bucket, the lock rule of [D6](#d6), an *Object Read & Write* token scoped to it, the account id into `backup:`, the key pair into sops; the client's key by `age-keygen`, its public half beside the operator's in `.sops.yaml`, `sops updatekeys secrets.sops.yaml`, the private half in the client's password manager; a tagged, single-use, pre-approved auth key and the ACL `{"tagOwners": {"tag:box": ["autogroup:admin"]}, "acls": [{"action": "accept", "src": ["autogroup:member"], "dst": ["*:*"]}]}` (a `tag:box` node is no member, so it reaches nothing); the KB steps by a link to `docs/kb.md`; after the bootstrap, *Share* the node with the client's email; a terminal-login provider: `podman exec -it <name> hermes auth add <provider>` as the box user. The bootstrap is one command, at `v0.4.0`. `docs/kb.md` step 3 says to set **Enforcement status** to **Active** (0003·R5). `examples/box/RESTORE.md`: `make restore`, and by hand — download from the Cloudflare dashboard, `age -d -i <key> -o backup.zip <file>`, `hermes import backup.zip`. `README.md`, `docs/architecture.md` (the diagram, *Secrets and backups*, the manifest block, `box.yaml`'s `backup`, a five-target `Makefile`) and `CLAUDE.md` ("eight-field manifest") follow | a decision in force is edited where it lives | Tailscale or Cloudflare as code (parked) |

### D14 — The version and the example

| id | decision | because | rejected |
|---|---|---|---|
| D14 | `galaxy.yml` `0.4.0`; `examples/box/requirements.yml` pins `v0.4.0`; `examples/box/Makefile` gains `restore`; `examples/box/box.yaml` `backup: r2:0123456789abcdef0123456789abcdef/example-backups`; a second throwaway key `tests/keys/example-client.age` by `age-keygen`; `examples/box/.sops.yaml` names both public keys; `examples/box/secrets.sops.yaml` re-encrypted to both, every required name a placeholder | the example shows a client box as built | one recipient in the example |

### D15 — The tests

| file | what it asserts |
|---|---|
| `tests/test_box_schema.py` | an R2 `backup` accepted, a restic URL refused; the R2 names required, `RESTIC_PASSWORD` not; `backup`/`restore` without `{archive}` refused; `read_recipients` on a string, a list, none and a bad key |
| `tests/test_templates.py` | `rclone.env.j2` needles; `box-backup.sh.j2` with stub `podman`, `age`, `rclone`, `logger`: seven listed archives → the oldest two deleted; a refused delete → a warning and exit `0`; a failed upload → exit non-zero and the in-volume zip removed; no `systemctl … stop` |
| `tests/test_plays.py` | restore: stop before the import, the import in `podman run --rm --user 10000`, the start in `always:`, `rm -rf` of `kb` only under `box.kb is defined`, `age -d` only in a `localhost` play; drill: the scratch volume removed in `always:`; the KB tests read `roles/box/tasks/kb.yml`, and `box.yml` flushes handlers before importing it |
| `tests/test_bootstrap.py` | no argument → usage and exit `1`; the script never assigns `$1` to the auth key; the keyring `curl` writes to a `mktemp` path |
| `tests/test_sops.py` | unchanged |

## Dependencies

- `age` — Debian Trixie package on the host, Homebrew `age` on the operator's and the client's machine, any 1.x.
- `rclone` — Debian Trixie package `1.60.1+dfsg-4` or later on the host, Homebrew `rclone` on the operator's and
  the client's machine, 1.60 or later (the Cloudflare provider).
- `restic` — removed from the host and from the operator's machine.

No new Python package or collection.

## Risks / Trade-offs

- [`hermes import --force` leaves files the archive lacks] → `state.db`, config and memories are replaced; a stray
  newer file under `sessions/` may stay. Accepted; the acceptance restores onto a re-flashed Pi.
- [A full copy each night] → a Hermes state is small; five copies fit R2's free tier.
- [`/dev/tty` absent, e.g. a script piped from a non-interactive shell] → the bootstrap stops with a message; the
  documented path is an interactive SSH session.
- [A manual `make backup` several times a day] → the extra archives are locked and kept until a later night.
- [The ACL replaces the tailnet's default "allow all"] → the operator's own devices are members and keep their
  access; the acceptance checks the share still reaches `<target>:9119`.

## Verdict

Build the contracts, the backup, restore and the drill, the bootstrap, then the docs; no hand step. The
`box-contracts`, `box-apply`, `box-backup` and `pi-bootstrap` deltas, restic gone, and no chore left to remember.

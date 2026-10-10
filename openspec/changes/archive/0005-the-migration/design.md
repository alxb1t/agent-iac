# 0005-the-migration — design

How `restore` takes a local archive through the path it already has, and drops a hand-installed Hermes's `.env`. Verdict:
build it phase by phase, as [tasks](tasks.md) orders; nothing by hand.

## Context

`roles/box/tasks/fetch.yml` runs on the machine running `make`: it finds the age identity, makes the private folder
`box_tmp`, lists the bucket, picks an archive (`box_archive` names one), refuses one dated in the future, downloads
it and decrypts it to `<box_tmp>/restore.zip`. `playbooks/restore.yml` then hands the zip to the box through
`roles/box/tasks/send.yml`, which removes the whole local folder (`roles/box/tasks/send.yml:22-28`), stops the
service, imports in a one-off container, removes the archive's `kb/` with `kb:` (`playbooks/restore.yml:71-83`),
starts it and re-clones the KB. Hermes reads `/opt/data/.env` over the process env ("`~/.hermes/.env` overrides
stale shell exports", Hermes `hermes_cli/env_loader.py:461`).

## Goals / Non-Goals

**Goals:**
- A `hermes backup` zip from anywhere becomes a box's state through `restore`.
- The user's file is never touched.

**Non-Goals:**
- Converting the old install's config or KB.
- Running against a real host in the gate.

## Decisions

### D1 — The local archive in the fetch

```
fetch.yml
  box_archive_file given? ── no ──▶ as today: identity, list, pick, future check, download, decrypt
          │ yes
          ├─ refuse: box_archive also given · not an absolute path · not a file · not .zip / .zip.age
          ├─ make box_tmp; box_pick = the file's basename; print "archive: <basename>"
          ├─ .zip.age → identity (as today), age -d -o <box_tmp>/restore.zip <file>
          └─ .zip     → copy to <box_tmp>/restore.zip (no identity needed)
```

| id | decision | because | rejected |
|---|---|---|---|
| D1 | the branch above in `roles/box/tasks/fetch.yml`; the identity tasks run only when an archive is decrypted; the refusals are `assert`s before the private folder is made, each naming its problem | one restore path after the fetch; `send.yml` removes only `box_tmp`, never the user's file | reading the file in place (send would delete it); a second playbook |

### D2 — `.env` after a local import

| id | decision | because | rejected |
|---|---|---|---|
| D2 | in `playbooks/restore.yml`, the play's `box_migrates` is true when `box_archive_file` names a plain `.zip`; *Read the volume's path* moves before *Import the archive* and runs when `box.kb is defined or box_migrates`; a new *Remove the old install's env*, first in the block's `always:` before *Start the box*, runs `podman unshare rm -f <volume>/.env` when `box_migrates` and the volume's path was read; Hermes seeds a template at the next start; `auth.json` stays | an imported `.env` would shadow the sops secrets and leave the old ones on the volume; in `always:`, an import that wrote `.env` and then failed does not start the agent on it, and a run that failed before the stop has no path, so leaves the volume alone; provider logins migrate | removing `.env` on every restore, or on a local `.zip.age` (a box's own archive, whose `.env` holds keys `hermes auth add` wrote); the removal after the import in `block:` (a failed import starts on the old `.env`) |

### D3 — `make migrate`

```makefile
migrate:        ; $(if $(ZIP),,$(error usage: make migrate ZIP=<path to the zip>))$(if $(word 2,$(ZIP)),$(error ZIP=$(ZIP) has a space; rename the file or its folder)) ansible-playbook alxb1t.agent_iac.restore -e box_file=$(CURDIR)/box.yaml -e box_archive_file=$(abspath $(ZIP))
```

| id | decision | because | rejected |
|---|---|---|---|
| D3 | `examples/box/Makefile` gains the line above | `make restore -e …` hands `-e` to make, not Ansible; `abspath` makes a relative `ZIP` safe; make splits a value on its spaces, so a `ZIP` with one is refused by name | the raw `ansible-playbook` line in the docs only; quoting the value (`abspath` has already split it) |

### D4 — The docs

| id | decision | because | rejected |
|---|---|---|---|
| D4 | `docs/host.md` gains *7 — Migrating a hand-installed Hermes*: move the old `.env` values into `secrets.sops.yaml`; `hermes update` a much older install; on the old machine `hermes backup -o migrate.zip`, then stop its gateway, since a bot token is polled by one gateway at a time; copy the zip to the operator's machine; `make migrate ZIP=migrate.zip`; delete the zip, which holds secrets. `examples/box/RESTORE.md` gains a line: an archive already on your machine, `.zip` or `.zip.age`, restores with `make migrate ZIP=<path>`. `README.md`'s *After that* and `docs/architecture.md`'s restore bullet name the local archive | the first client box is a migration; the steps are the operator's | a separate migration page |

### D5 — The version

| id | decision | because | rejected |
|---|---|---|---|
| D5 | `galaxy.yml` `0.5.0`; `examples/box/requirements.yml` pins `v0.5.0`; `docs/host.md`'s bootstrap URL stays at `v0.4.0` | `contrib/bootstrap-pi.sh` does not change | bumping the URL |

### D6 — The tests

| file | what it asserts |
|---|---|
| `tests/test_plays.py` | `run_fetch` takes extra vars; a local `.zip`: no `rclone` and no `age` call, no identity needed, `restore.zip` equals the file, the file still exists; a local `.zip.age`: `age -d` on the file, no `rclone`; `migrate.tar`, a relative path and `box_archive` with `box_archive_file` each refused before the private folder; *Remove the old install's env* runs `rm -f` on `.env` for a local `.zip` only, not a `.zip.age` nor the bucket, in `always:` before *Start the box*, and not when the volume's path was never read, which now comes before *Import the archive*; `examples/box/Makefile`'s `migrate` passes `box_archive_file=$(abspath $(ZIP))` and refuses a `ZIP` with a space |

## Dependencies

None.

## Risks / Trade-offs

- [A much older or newer Hermes wrote the zip] → `hermes import` and the boot migration carry the config; the docs say
  to `hermes update` the old install first; the acceptance's line G4 runs it.
- [The old gateway keeps polling the same bot] → the docs say to stop it before `make migrate`.
- [The old `.env` held a value sops lacks] → the docs say to move every value into sops first; `apply` refuses a
  missing secret the manifest names.

## Verdict

Build the fetch, the restore and the target, then the docs; no hand step. One `box-backup` delta, and one more way
in, through the same restore.

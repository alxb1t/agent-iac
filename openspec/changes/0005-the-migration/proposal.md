---
version: v0.5
---

# 0005-the-migration — a hand-installed Hermes moves into a box

`restore` imports a local archive as well as one from the bucket, so a hand-installed Hermes's `hermes backup` zip
becomes a box's state. Proven by the fetch and play tests; the acceptance by hand runs it on a real Pi.

Read [design](design.md) for the decisions (`D1`–`D6`); the `box-backup` delta under `specs/`; [tasks](tasks.md) for
the phases.

## Why

The first client box replaces a Hermes installed by hand, and its state lives in a `hermes backup` zip on that
machine. `restore` reads only from the bucket, so there is no way in for it. A local archive through the same restore
path is the smallest way in.

## What Changes

- **`restore` takes `-e box_archive_file=<absolute path>`**: a `.zip.age` is decrypted with the same identity, a
  `.zip` copied as is, both into the private temp folder; the user's file is never moved or deleted, per
  [D1](design.md#d1).
- **A local import drops `.env`** from the volume after the import, so the old install's secrets neither shadow the
  sops ones nor stay on the box, per [D2](design.md#d2).
- **The example gains `make migrate ZIP=<path>`**, per [D3](design.md#d3).
- **`docs/host.md` gains *Migrating a hand-installed Hermes***; `RESTORE.md`, `README.md` and `docs/architecture.md`
  name the local archive, per [D4](design.md#d4).
- **The collection is `0.5.0`**, per [D5](design.md#d5).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `box-backup`: `restore` also imports a local archive, and drops its `.env`.

Each requirement the delta touches:

- `box-backup` · *Restore is one step* → modified: a local archive by `box_archive_file`, never moved or deleted;
  `.env` removed after a local import.

## Impact

- Edited: `roles/box/tasks/fetch.yml`, `playbooks/restore.yml`, `examples/box/Makefile`,
  `examples/box/RESTORE.md`, `examples/box/requirements.yml`, `galaxy.yml`, `docs/host.md`, `docs/architecture.md`,
  `README.md`, `tests/test_plays.py`.
- Dependencies: none.

## Not in this change

Each item names the trigger that brings it in, never a date.

- **A plain zip in the bucket** — never: the bucket holds encrypted archives only.
- **Keeping the old install's `.env`** — never: the secrets come from sops.
- **Migrating the old install's KB** — never: the box clones its KB repo.
- **The acceptance by hand** — the next version, run on this one.

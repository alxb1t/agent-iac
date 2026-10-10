# 0004-the-handover — tasks

The phases: the contracts, the backup, restore and the drill, the bootstrap, the example and the docs. Each ends on a
green gate.

## Progress

- [x] 1 — The contracts
- [x] 2 — The backup
- [x] 3 — Restore, the drill and status
- [x] 4 — The bootstrap
- [x] 5 — The example and the docs

## 1 — The contracts

- [x] 1.1 Edit `plugins/module_utils/box_schema.py` per [D1](design.md#d1)–[D3](design.md#d3): `backup` and `restore`
      in `MANIFEST_KEYS`, the R2 pattern in place of `RESTIC_URL`, the R2 names in `HOST_SECRETS`, `read_recipients`.
      Verify: `grep -c 'RESTIC' plugins/module_utils/box_schema.py` prints `0` and `grep -c 'def read_recipients' plugins/module_utils/box_schema.py` prints `1`.
- [x] 1.2 In `plugins/action/box_load.py`, read `.sops.yaml` beside `box.yaml` through `read_recipients` and pass `box_recipients`, per [D3](design.md#d3).
      Verify: `grep -c 'box_recipients' plugins/action/box_load.py` prints `1`.
- [x] 1.3 Add the `backup` and `restore` lines of [D1](design.md#d1) to `runtimes/hermes.yaml`.
      Verify: `grep -c '{archive}' runtimes/hermes.yaml` prints `2`.
- [x] 1.4 Edit `tests/test_box_schema.py` per [D15](design.md#d15); in `tests/conftest.py` set `VALID_BOX`'s `backup` to an R2 URL and add the R2 secrets and `box_recipients`.
      Verify: `uv run pytest -q tests/test_box_schema.py` prints `passed` and no `failed`, and
      `grep -c 'read_recipients' tests/test_box_schema.py` prints a number above `0`.

## 2 — The backup

- [x] 2.1 Apply [D4](design.md#d4) to `roles/box/defaults/main.yml` and `roles/box/tasks/backup.yml`: write `roles/box/templates/rclone.env.j2`,
      delete `roles/box/templates/restic.env.j2`, write the recipients file, remove `<name>.restic.env`.
      Verify: `git grep -c restic -- roles/box ':!roles/box/tasks/backup.yml' | wc -l` prints `0`, `grep -c restic roles/box/tasks/backup.yml` prints `2`
      (the removal's name and path), and `test -f roles/box/templates/rclone.env.j2; echo $?` prints `0`.
- [x] 2.2 Rewrite `roles/box/templates/box-backup.sh.j2` per [D5](design.md#d5).
      Verify: `grep -c 'rclone rcat' roles/box/templates/box-backup.sh.j2` prints `1` and `grep -c 'systemctl' roles/box/templates/box-backup.sh.j2` prints `0`.
- [x] 2.3 Edit `tests/test_templates.py` and `tests/conftest.py` per [D15](design.md#d15): the restic needles and
      tests go, the rclone and keep-five tests come, `RESTIC_PASSWORD` and `box_restic_env` leave the sample vars.
      Verify: `uv run pytest -q tests/test_templates.py` prints `passed` and no `failed`, and `grep -c 'restic' tests/test_templates.py tests/conftest.py | grep -c ':0$'` prints `2`.

## 3 — Restore, the drill and status

- [x] 3.1 Move the *Clone the KB once* block from `roles/box/tasks/box.yml` to `roles/box/tasks/kb.yml`, imported after the flush, per [D9](design.md#d9).
      Verify: `grep -c 'git clone' roles/box/tasks/kb.yml` prints `1` and `grep -c 'git clone' roles/box/tasks/box.yml` prints `0`.
- [x] 3.2 Rewrite `playbooks/restore.yml` per [D7](design.md#d7) and [D8](design.md#d8).
      Verify: `grep -c 'restic' playbooks/restore.yml` prints `0` and `grep -c -- '--entrypoint' playbooks/restore.yml` prints a number above `0`.
- [x] 3.3 Rewrite `playbooks/restore_drill.yml` per [D10](design.md#d10) and `playbooks/status.yml` per [D11](design.md#d11).
      Verify: `grep -c 'restic' playbooks/restore_drill.yml playbooks/status.yml | grep -c ':0$'` prints `2` and `grep -c 'integrity_check' playbooks/restore_drill.yml` prints `1`.
- [x] 3.4 Edit `tests/test_plays.py` per [D15](design.md#d15), replacing `test_restore_deletes_only_inside_the_volume`
      and pointing the KB tests at `roles/box/tasks/kb.yml`.
      Verify: `uv run pytest -q tests/test_plays.py` prints `passed` and no `failed`, and `grep -c 'kb.yml' tests/test_plays.py` prints a number above `0`.

## 4 — The bootstrap

- [x] 4.1 Edit `contrib/bootstrap-pi.sh` per [D12](design.md#d12).
      Verify: `grep -c 'key=\$1' contrib/bootstrap-pi.sh` prints `0`, `grep -c '/dev/tty' contrib/bootstrap-pi.sh` prints a number above `0`,
      and `sh contrib/bootstrap-pi.sh; echo $?` prints usage then `1`.
- [x] 4.2 Write `tests/test_bootstrap.py` per [D15](design.md#d15).
      Verify: `uv run pytest -q tests/test_bootstrap.py` prints `passed` and no `failed`.

## 5 — The example and the docs

- [x] 5.1 Apply [D14](design.md#d14): `galaxy.yml`, `examples/box/requirements.yml`, `examples/box/Makefile`, `examples/box/box.yaml`,
      `tests/keys/example-client.age`, `examples/box/.sops.yaml`, then re-encrypt `examples/box/secrets.sops.yaml` to both keys.
      Verify: `grep -c '^version: 0.4.0' galaxy.yml` prints `1` and `grep -c '^[A-Z0-9_]*: ENC\[' examples/box/secrets.sops.yaml` prints `10`.
- [x] 5.2 Write `examples/box/RESTORE.md` and the `docs/host.md` onboarding per [D13](design.md#d13), and the `docs/kb.md` ruleset line.
      Verify: `grep -c 'tag:box' docs/host.md` prints a number above `0`, `grep -c 'age -d' examples/box/RESTORE.md` prints a number above `0`,
      and `grep -c 'Active' docs/kb.md` prints a number above `0`.
- [x] 5.3 Edit `README.md`, `docs/architecture.md` and `CLAUDE.md` per [D13](design.md#d13).
      Verify: `git grep -c -i 'restic\|sftp' -- README.md docs/architecture.md | wc -l` prints `0` and `grep -c 'eight-field manifest' CLAUDE.md` prints `1`.
- [x] 5.4 **HALT CHECK** No name, client, vault or machine path anywhere new. `P` = `roles playbooks plugins runtimes blueprints examples contrib docs README.md`.
      Verify: `git grep --untracked -l '/Users/' -- $P | wc -l` prints `0`, and `test -s .minions/refused-names && { git grep --untracked -li -f .minions/refused-names -- $P; echo "exit=$?"; }`
      prints only `exit=1`; a missing or empty `.minions/refused-names` prints nothing and fails.

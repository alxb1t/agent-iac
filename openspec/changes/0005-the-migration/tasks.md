# 0005-the-migration — tasks

The phases: the fetch, the restore and the target, the docs. Each ends on a green gate.

## Progress

- [ ] 1 — The fetch
- [ ] 2 — The restore and the target
- [ ] 3 — The docs

## 1 — The fetch

- [ ] 1.1 Add the local-archive branch of [D1](design.md#d1) to `roles/box/tasks/fetch.yml`.
      Verify: `grep -c 'box_archive_file' roles/box/tasks/fetch.yml` prints a number above `2`.
- [ ] 1.2 Extend `tests/test_plays.py` per [D6](design.md#d6): `run_fetch` takes extra vars, and the local-archive
      fetch cases. Verify: `uv run pytest -q tests/test_plays.py` prints `passed` and no `failed`, and
      `grep -c 'box_archive_file' tests/test_plays.py` prints a number above `0`.

## 2 — The restore and the target

- [ ] 2.1 Add *Remove the old install's env* to `playbooks/restore.yml` per [D2](design.md#d2).
      Verify: `grep -c "Remove the old install's env" playbooks/restore.yml` prints `1`.
- [ ] 2.2 Add the `migrate` line of [D3](design.md#d3) to `examples/box/Makefile`.
      Verify: `grep -c 'box_archive_file=$(abspath $(ZIP))' examples/box/Makefile` prints `1`.
- [ ] 2.3 Extend `tests/test_plays.py` per [D6](design.md#d6): the `.env` removal and the `migrate` target.
      Verify: `uv run pytest -q tests/test_plays.py` prints `passed` and no `failed`, and `grep -c 'migrate' tests/test_plays.py` prints a number above `0`.

## 3 — The docs

- [ ] 3.1 Write *7 — Migrating a hand-installed Hermes* in `docs/host.md` and the `examples/box/RESTORE.md` line per [D4](design.md#d4).
      Verify: `grep -c 'make migrate ZIP=' docs/host.md` prints a number above `0` and `grep -c 'make migrate' examples/box/RESTORE.md` prints a number above `0`.
- [ ] 3.2 Edit `README.md` and `docs/architecture.md` per [D4](design.md#d4), and apply [D5](design.md#d5) to `galaxy.yml` and `examples/box/requirements.yml`.
      Verify: `grep -c 'make migrate' README.md` prints a number above `0` and `grep -c '^version: 0.5.0' galaxy.yml` prints `1`.
- [ ] 3.3 **HALT CHECK** No name, client, vault or machine path anywhere new. `P` = `roles playbooks plugins runtimes blueprints examples contrib docs README.md`.
      Verify: `git grep --untracked -l '/Users/' -- $P | wc -l` prints `0`, and `test -s .minions/refused-names && { git grep --untracked -li -f .minions/refused-names -- $P; echo "exit=$?"; }`
      prints only `exit=1`; a missing or empty `.minions/refused-names` prints nothing and fails.

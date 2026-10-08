# 0002-the-box — tasks

Five phases: the skeleton and gate, the host tasks, the box tasks, backup and restore, the example and docs. Each
ends on a green gate.

## Progress

- [x] 1 — Skeleton and gate
- [x] 2 — The host tasks
- [x] 3 — The box tasks
- [x] 4 — Backup, restore, drill, status
- [x] 5 — Example, contrib and docs

## 1 — Skeleton and gate

- [x] 1.1 Write `galaxy.yml` (namespace `alxb1t`, name `agent_iac`, version `0.2.0`, license `Apache-2.0`),
      `pyproject.toml` with the dev group of [Dependencies](design.md#dependencies), `requirements.yml`, the empty role
      files of [D1](design.md#d1), and each playbook as a no-op play (`hosts: localhost`, `gather_facts: false`, `tasks: []`).
      Verify: `uv sync && uv run ansible-lint --version` prints a version.
- [x] 1.2 Append `.venv/`, `.ansible/`, `__pycache__/`, `.pytest_cache/` to `.gitignore`.
      Verify: `mkdir -p .ansible && git check-ignore .venv .ansible | wc -l` prints `2`.
- [x] 1.3 Replace the `gate` recipe in `Makefile` with the five commands of [D13](design.md#d13), in that order.
      Verify: `make -n gate | grep -c 'openspec validate\|yamllint\|ansible-lint\|syntax-check\|pytest'` prints `5`.
- [x] 1.4 Write `plugins/module_utils/box_schema.py` per [D3](design.md#d3) and `tests/test_box_schema.py` per
      [D14](design.md#d14). Verify: `uv run pytest -q tests/test_box_schema.py` prints `passed` and no `failed`.
- [x] 1.5 Write `plugins/action/box_load.py` per [D2](design.md#d2) and `runtimes/hermes.yaml` per [D3](design.md#d3).
      Verify: `grep -c '^blueprint_mount: /opt/data' runtimes/hermes.yaml` prints `1` and `grep -c 'pre_backup' runtimes/hermes.yaml` prints `0`.
- [x] 1.6 Write `.yamllint`, `.ansible-lint` and `meta/runtime.yml` per [D1](design.md#d1), and track the `uv.lock`
      that `uv sync` writes. Verify: `uv run ansible-lint` prints `Passed` and `test -f uv.lock && ! git check-ignore -q uv.lock; echo $?` prints `0`.

## 2 — The host tasks

- [x] 2.1 Write `roles/box/tasks/host.yml` per [D4](design.md#d4) with the guards of [D10](design.md#d10), and
      `roles/box/defaults/main.yml` with the package list and the subuid range.
      Verify: `grep -c 'tailscale up' roles/box/tasks/host.yml` prints `1` and `grep -c 'enable-linger' roles/box/tasks/host.yml` prints `1`.
- [x] 2.2 Write `roles/box/templates/nftables.conf.j2` per [D6](design.md#d6), `auto-upgrades.j2` per [D4](design.md#d4)
      and `cron.j2` per [D11](design.md#d11). Verify: `grep -c 'iifname "tailscale0" accept' roles/box/templates/nftables.conf.j2` prints `1`.
- [x] 2.3 Write `tests/conftest.py` with the sample vars and `tests/test_templates.py` asserting the needles of
      [D14](design.md#d14) for the three templates above. Verify: `uv run pytest -q tests/test_templates.py` prints `passed` and no `failed`.

## 3 — The box tasks

- [x] 3.1 Write `roles/box/templates/env.j2`, `restic.env.j2` per [D7](design.md#d7), `box-blueprint-sync.sh.j2` per
      [D8](design.md#d8), `box.container.j2` per [D5](design.md#d5). Verify: `grep -c '^Exec=gateway run' roles/box/templates/box.container.j2` prints `1`.
- [x] 3.2 Write `roles/box/tasks/box.yml` per [D5](design.md#d5), [D7](design.md#d7)–[D9](design.md#d9) with the guards
      of [D10](design.md#d10), `roles/box/handlers/main.yml` with the restart handler, and `roles/box/tasks/main.yml`
      including `host.yml` then `box.yml`. Verify: `grep -c 'no_log: true' roles/box/tasks/box.yml` prints `1` and `grep -c 'daemon-reload' roles/box/tasks/box.yml` prints `1`.
- [x] 3.3 Write `blueprints/base/config.yaml` and `blueprints/base/SOUL.md` as the minimal Hermes files, with no
      secret and no name. Verify: `grep -ci 'token\|api_key\|sk-' blueprints/base/config.yaml` prints `0`.
- [x] 3.4 Extend `tests/test_templates.py` with the needles for the four templates of 3.1, and write
      `tests/test_sops.py` with `tests/keys/example.age` per [D14](design.md#d14).
      Verify: `uv run pytest -q` prints `passed` and no `failed`.
- [x] 3.5 Write `playbooks/apply.yml`: `box_load`, then the role on the added host.
      Verify: `make gate` output contains `syntax-check` and no `ERROR`.

## 4 — Backup, restore, drill, status

- [x] 4.1 Write `roles/box/templates/box-backup.sh.j2` and `roles/box/tasks/backup.yml` per [D11](design.md#d11) and
      [D12](design.md#d12): the restic env file, the SFTP key, `restic init` guarded, the script installed.
      Verify: `grep -c 'trap' roles/box/templates/box-backup.sh.j2` prints `1` and `grep -c 'no_log: true' roles/box/tasks/backup.yml` prints `1`.
- [x] 4.2 Write `playbooks/backup.yml`, `playbooks/restore.yml`, `playbooks/restore_drill.yml`, `playbooks/status.yml`
      per [D11](design.md#d11). Verify: `ls playbooks | grep -c 'yml$'` prints `5`.
- [x] 4.3 Extend `tests/test_templates.py` with the needles for `box-backup.sh.j2`.
      Verify: `uv run pytest -q` prints `passed` and no `failed`.

## 5 — Example, contrib and docs

- [x] 5.1 Write `examples/box/` per [D1](design.md#d1) and [D2](design.md#d2): the four-target `Makefile` word for
      word, `box.yaml` with `name: example`, `blueprint/SOUL.md`, `.sops.yaml` with the example age public key,
      `secrets.sops.yaml` encrypted to it, `requirements.yml` pinning `alxb1t.agent_iac` at `v0.2.0`.
      Verify: `grep -c '^sops:' examples/box/secrets.sops.yaml` prints `1` and `grep -c '^[A-Z_]*: ENC\[' examples/box/secrets.sops.yaml` prints `5`.
- [x] 5.2 Write `contrib/bootstrap-pi.sh` per the `pi-bootstrap` delta: usage on missing arguments, a root check,
      `apt-get install -y python3`, Tailscale's apt repository behind its pinned signing key, `tailscale up --auth-key=file:`, the key into
      root's `authorized_keys`, idempotent. Verify: `sh -n contrib/bootstrap-pi.sh; echo $?` prints `0` and `sh contrib/bootstrap-pi.sh; echo $?` prints usage then `1`.
- [x] 5.3 Write `docs/host.md` per [D16](design.md#d16). Verify: `grep -c 'bootstrap-pi.sh' docs/host.md` prints `1`.
- [x] 5.4 Edit `docs/architecture.md` and `CLAUDE.md` per [D15](design.md#d15).
      Verify: `grep -c 'pre_backup\|Alpine\|OpenRC' docs/architecture.md` prints `0`, `grep -c 'No systemd on the host' CLAUDE.md` prints `0` and `grep -c 'four-field manifest' CLAUDE.md` prints `1`.
- [x] 5.5 Write `README.md` per [D15](design.md#d15). Verify: `grep -c 'docs/host.md' README.md` prints `1` and `grep -c 'make apply' README.md` prints `1`.
- [x] 5.6 **HALT CHECK** No name, client, vault or machine path anywhere new.
      Verify: `grep -rl '/Users/' roles playbooks plugins runtimes blueprints examples contrib docs README.md | wc -l` prints `0`, and
      `test -s "$NAMES" && { grep -rli -f "$NAMES" <those paths>; echo "exit=$?"; }` prints only `exit=1`, `$NAMES` being
      the gitignored `.minions/refused-names`, one name to refuse per line; a missing or empty file prints nothing and fails.

# 0003-the-knowledge-base — tasks

The phases: the contracts, the quadlet and the tailnet address, the deploy key and the clone, the plugin and the
base blueprint, the example and the docs. Each ends on a green gate.

## Progress

- [x] 1 — The contracts
- [ ] 2 — The quadlet and the tailnet address
- [ ] 3 — The deploy key and the clone
- [ ] 4 — The plugin and the base blueprint
- [ ] 5 — The example and the docs

## 1 — The contracts

- [x] 1.1 Edit `plugins/module_utils/box_schema.py` per [D1](design.md#d1) and [D3](design.md#d3):
      `MANIFEST_KEYS` with `environment` and `ports`, `BOX_OPTIONAL_KEYS`, the `kb` pattern, `missing_secrets(secrets, manifest, box)`.
      Verify: `grep -c 'BOX_OPTIONAL_KEYS' plugins/module_utils/box_schema.py` prints a number above `1`.
- [x] 1.2 Pass `box` to `missing_secrets` in `plugins/action/box_load.py`.
      Verify: `grep -c 'missing_secrets(secrets, manifest, box)' plugins/action/box_load.py` prints `1`.
- [x] 1.3 Write `runtimes/hermes.yaml` as [D2](design.md#d2) shows.
      Verify: `grep -c '^ports:' runtimes/hermes.yaml` prints `1` and `grep -c 'PASSWORD_HASH' runtimes/hermes.yaml` prints `1`.
- [x] 1.4 Edit `tests/test_box_schema.py` per [D10](design.md#d10), and add the dashboard names to `tests/conftest.py`'s sample secrets.
      Verify: `uv run pytest -q tests/test_box_schema.py` prints `passed` and no `failed`, and
      `grep -c 'KB_DEPLOY_KEY' tests/test_box_schema.py` prints a number above `0`.

## 2 — The quadlet and the tailnet address

- [ ] 2.1 Add the tailnet-address read of [D6](design.md#d6) to `roles/box/tasks/host.yml`, after the wait for the
      tailnet. Verify: `grep -c 'tailscale ip -4' roles/box/tasks/host.yml` prints `1`.
- [ ] 2.2 Add the lines of [D5](design.md#d5) to `roles/box/templates/box.container.j2`, after `EnvironmentFile=`.
      Verify: `grep -c 'StrictHostKeyChecking=yes' roles/box/templates/box.container.j2` prints `1`.
- [ ] 2.3 Write `blueprints/base/.ssh/kb_known_hosts`: GitHub's Ed25519, ECDSA and RSA host keys, one `github.com` line each.
      Verify: `ssh-keygen -lf blueprints/base/.ssh/kb_known_hosts | awk '{print $2}' | sort` prints the three
      fingerprints of [D5](design.md#d5), sorted.
- [ ] 2.4 Edit `tests/conftest.py` and `tests/test_templates.py` per [D10](design.md#d10), replacing `test_quadlet_publishes_no_port`.
      Verify: `uv run pytest -q tests/test_templates.py` prints `passed` and no `failed`, and
      `grep -c 'def test_quadlet_publishes_no_port' tests/test_templates.py` prints `0`.

## 3 — The deploy key and the clone

- [ ] 3.1 Add the Podman secret tasks of [D4](design.md#d4) to `roles/box/tasks/box.yml`, before `Write the quadlet`,
      only when `box.kb is defined`. Verify: `grep -c 'podman secret create --replace' roles/box/tasks/box.yml` prints `1`.
- [ ] 3.2 Add the guarded clone of [D7](design.md#d7) to `roles/box/tasks/box.yml`, after `Start the service`.
      Verify: `grep -c 'git clone' roles/box/tasks/box.yml` prints `1`.
- [ ] 3.3 Extend `tests/test_plays.py` per [D10](design.md#d10): the secret task's `no_log` and `stdin`, the clone's guard and user.
      Verify: `uv run pytest -q tests/test_plays.py` prints `passed` and no `failed`, and
      `grep -c 'git clone' tests/test_plays.py` prints a number above `0`.

## 4 — The plugin and the base blueprint

- [ ] 4.1 Copy the files of [D8](design.md#d8) from `https://github.com/aean0x/hermes-git-hook` at `a7303c8` into
      `blueprints/base/plugins/git-hook/`, byte for byte, and add the directory to `.ansible-lint`'s `exclude_paths`.
      Verify: `shasum -a 256 blueprints/base/plugins/git-hook/sync.py` prints
      `591f6a7343d70a63e5c0ef79e58f4ff0bae9bb5799ccbfd7143f637d850554e5` and
      `grep -c 'blueprints/base/plugins/git-hook/' .ansible-lint` prints `1`.
- [ ] 4.2 Write `tests/test_vendored.py` per [D8](design.md#d8) and [D10](design.md#d10).
      Verify: `uv run pytest -q tests/test_vendored.py` prints `passed` and no `failed`.
- [ ] 4.3 Enable the plugin in `blueprints/base/config.yaml` per [D8](design.md#d8), and add the paragraph of
      [D9](design.md#d9) to `blueprints/base/SOUL.md`.
      Verify: `grep -c 'git-hook' blueprints/base/config.yaml` prints `1` and `grep -c '/opt/data/kb' blueprints/base/SOUL.md` prints `1`.

## 5 — The example and the docs

- [ ] 5.1 Apply [D12](design.md#d12) to `galaxy.yml`, `examples/box/requirements.yml`, `examples/box/box.yaml`, and
      re-encrypt `examples/box/secrets.sops.yaml` with `SOPS_AGE_KEY_FILE=tests/keys/example.age`.
      Verify: `grep -c '^version: 0.3.0' galaxy.yml` prints `1` and `grep -c '^[A-Z_]*: ENC\[' examples/box/secrets.sops.yaml` prints `9`.
- [ ] 5.2 Write `docs/kb.md` per [D11](design.md#d11).
      Verify: `grep -c 'kb_deploy.pub' docs/kb.md` prints a number above `0` and `grep -c ':9119' docs/kb.md` prints a number above `0`.
- [ ] 5.3 Edit `README.md`, `docs/architecture.md` and `CLAUDE.md` per [D11](design.md#d11).
      Verify: `grep -c 'four-field' CLAUDE.md docs/architecture.md | grep -c ':0$'` prints `2`,
      `grep -c 'six-field manifest' CLAUDE.md` prints `1` and `grep -c 'docs/kb.md' README.md` prints `1`.
- [ ] 5.4 **HALT CHECK** No name, client, vault or machine path anywhere new. `P` = `roles playbooks plugins runtimes blueprints examples contrib docs README.md`.
      Verify: `grep -rl '/Users/' $P | wc -l` prints `0`, and `test -s .minions/refused-names && { grep -rli -f .minions/refused-names $P; echo "exit=$?"; }`
      prints only `exit=1`; a missing or empty `.minions/refused-names` prints nothing and fails.

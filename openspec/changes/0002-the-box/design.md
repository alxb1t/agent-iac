# 0002-the-box — design

How one role, five playbooks and a script make a Raspberry Pi OS host a box, and how the gate proves what it can
without a host. Verdict: build it in five phases; nothing by hand.

## Context

The repo holds the mf-* bootstrap, `docs/architecture.md` (the contracts, including `pre_backup`, and Alpine as
the host), and `CLAUDE.md` with the invariants, one of them *No systemd on the host*. `openspec/specs/` is empty.
The gate is `openspec validate` alone. The host is now Raspberry Pi OS Lite 64-bit (Debian 13): a client flashes
it headless with Raspberry Pi Imager, which sets hostname, user, SSH key and Wi-Fi; it ships `podman` 5.4 with
quadlet, logind, cgroup v2 delegation, `cron`, `nftables`, `restic`, `unattended-upgrades` and `python3`.

## Goals / Non-Goals

**Goals:**
- `make apply` in an example box repo converges a bootstrapped Pi into a running, backed-up Hermes box.
- Every template, the contract validator and the secrets path are tested on the operator's machine.
- The docs state the host and the contract as built.

**Non-Goals:**
- Running Ansible against a host in the gate. That is the acceptance version's job.
- Any egress control, any published port, any client-facing step.

## Decisions

### D1 — The layout

| id | decision | because | rejected |
|---|---|---|---|
| D1 | the repo root is the collection `alxb1t.agent_iac`; a `uv` project beside it holds the gate's Python tools | one tag pins code and tooling together; `ansible-galaxy collection install git+…,vX.Y.Z` reads a root `galaxy.yml` | a `collection/` subdirectory; a separate tooling repo |

```
galaxy.yml  pyproject.toml  uv.lock  requirements.yml  Makefile  .gitignore  README.md  CLAUDE.md  CHANGELOG.md
.yamllint  .ansible-lint  meta/runtime.yml
roles/box/
  defaults/main.yml      tasks/main.yml  tasks/host.yml  tasks/box.yml  tasks/backup.yml
  templates/             box.container.j2  nftables.conf.j2  env.j2  restic.env.j2  cron.j2
                         auto-upgrades.j2  box-backup.sh.j2  box-blueprint-sync.sh.j2
  handlers/main.yml
playbooks/               apply.yml  status.yml  backup.yml  restore.yml  restore_drill.yml
plugins/module_utils/    box_schema.py        plugins/action/  box_load.py
runtimes/hermes.yaml     blueprints/base/     config.yaml  SOUL.md
examples/box/            Makefile  box.yaml  blueprint/SOUL.md  secrets.sops.yaml  .sops.yaml  requirements.yml
contrib/bootstrap-pi.sh  docs/host.md  docs/architecture.md
tests/                   conftest.py  test_box_schema.py  test_templates.py  test_sops.py  keys/example.age
```

`uv.lock` pins the gate's tools. `.yamllint` reads `.gitignore`, so `.venv/` is not linted, and holds the rules
ansible-lint needs. `.ansible-lint` excludes `openspec/`, the OpenSpec CLI's files. ansible-lint's `galaxy` rule
requires `meta/runtime.yml`.

### D2 — The playbooks take a file, not an inventory

| id | decision | because | rejected |
|---|---|---|---|
| D2 | every playbook takes `-e box_file=<path>`; the `box_load` action reads `box.yaml`, validates it per [D3](#d3), loads the runtime manifest, decrypts `secrets.sops.yaml` beside it, and `add_host`s `target` as root with `ansible_python_interpreter=/usr/bin/python3`; the deployment repo's `Makefile` is four targets, each one `ansible-playbook` line | a deployment is one file; no inventory to drift | a static inventory; `host_vars` |

The example `Makefile`, word for word:

```makefile
COLL = ansible-galaxy collection install -r requirements.yml
apply:          ; $(COLL) && ansible-playbook alxb1t.agent_iac.apply -e box_file=$(CURDIR)/box.yaml
status:         ; ansible-playbook alxb1t.agent_iac.status -e box_file=$(CURDIR)/box.yaml
backup:         ; ansible-playbook alxb1t.agent_iac.backup -e box_file=$(CURDIR)/box.yaml
restore-drill:  ; ansible-playbook alxb1t.agent_iac.restore_drill -e box_file=$(CURDIR)/box.yaml
```

### D3 — The contracts, validated before any connection

| id | decision | because | rejected |
|---|---|---|---|
| D3 | `plugins/module_utils/box_schema.py` holds pure functions `validate_box(dict) -> list[str]` and `validate_manifest(dict) -> list[str]` returning every error at once; `box_load` fails with their output; the manifest has **four fields** `image · state · env · blueprint_mount` | pure functions are unit-tested without Ansible; one message names every fault | a JSON Schema dependency; pydantic |

The Hermes manifest, as shipped:

```yaml
# runtimes/hermes.yaml — env names re-checked against the pinned image's docs at every version bump
image: docker.io/nousresearch/hermes-agent
state:
  - /opt/data
env:
  - TELEGRAM_BOT_TOKEN
  - TELEGRAM_ALLOWED_USERS
  - OPENROUTER_API_KEY
blueprint_mount: /opt/data
```

### D4 — The host tasks

| id | decision | because | rejected |
|---|---|---|---|
| D4 | `tasks/host.yml`, in order: `apt` packages `podman crun rsync restic nftables unattended-upgrades tailscale`; `/etc/apt/apt.conf.d/20auto-upgrades` from `auto-upgrades.j2`; the user `box` with `/home/box`, shell `/bin/sh`, no password, in no group but its own; `/etc/subuid` and `/etc/subgid` lines `box:100000:65536`; `loginctl enable-linger box`; `tailscaled` enabled; `tailscale up --authkey <key>` only when `tailscale status --json` reports `.BackendState != "Running"`; the nftables ruleset of [D6](#d6) written and the `nftables` service enabled only after `.BackendState == "Running"`; `/etc/cron.d/box-<name>` from `cron.j2` | Debian's rootless Podman as tasks; the ordering keeps the LAN path open until the tailnet works | `pam_rundir`; a second user for Ansible; `sudo` for the box user |

Every task names its idempotence: package, user and `lineinfile` tasks are idempotent natively; `enable-linger`
is guarded by `ls /var/lib/systemd/linger/box`; `tailscale up` has `when:` on the status read and
`changed_when: true` only when it ran; every file is `template`d, so a byte-identical file is unchanged.

### D5 — The quadlet

```ini
# box.container.j2 → /home/box/.config/containers/systemd/{{ box.name }}.container
[Unit]
Description=agent-iac box {{ box.name }}
After=network-online.target

[Container]
ContainerName={{ box.name }}
Image={{ manifest.image }}:{{ box.version }}
Volume={{ box.name }}-data:{{ manifest.blueprint_mount }}
EnvironmentFile=%h/.config/agent-iac/{{ box.name }}.env
Exec=gateway run
AutoUpdate=none

[Service]
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
```

| id | decision | because | rejected |
|---|---|---|---|
| D5 | the quadlet above as the box user's systemd user unit; `systemctl --user daemon-reload` and `enable --now` run with `become_user: box` and the user bus in the task's `environment:` — `XDG_RUNTIME_DIR=/run/user/<uid>`, `DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/<uid>/bus` — the uid read from `getent passwd box` | quadlet is Podman's own systemd integration; lingering gives the user bus at boot without a login | an OpenRC-style script; a rootful system unit with `User=`; `podman generate systemd` |

### D6 — The ruleset

```
# nftables.conf.j2 → /etc/nftables.conf — inbound closed to the tailnet; outbound open
#!/usr/sbin/nft -f
flush ruleset
table inet filter {
  chain input {
    type filter hook input priority 0; policy drop;
    iif lo accept
    iifname "tailscale0" accept
    ct state established,related accept
    udp dport 41641 accept
    icmp type echo-request accept
    icmpv6 type { echo-request, nd-neighbor-solicit, nd-neighbor-advert, nd-router-advert } accept
  }
  chain forward { type filter hook forward priority 0; policy drop; }
  chain output  { type filter hook output  priority 0; policy accept; }
}
```

| id | decision | because | rejected |
|---|---|---|---|
| D6 | the ruleset above, loaded by Debian's `nftables.service`; written only after Tailscale is up ([D4](#d4)) | a reader can hold it in their head; Tailscale's UDP port stays open so the node keeps direct paths; IPv6 neighbour discovery stays alive | an allowlist of LAN addresses; `ufw`; `iptables` |

### D7 — The env file

| id | decision | because | rejected |
|---|---|---|---|
| D7 | `env.j2` renders `NAME=value` lines for every name in the manifest's `env`, to `/home/box/.config/agent-iac/<name>.env`, mode `0600`, owner `box`; the task has `no_log: true`; `restic.env.j2` renders `RESTIC_REPOSITORY` and `RESTIC_PASSWORD` to `<name>.restic.env` the same way | the container reads them through `EnvironmentFile`; nothing secret enters the volume | writing `.env` into `/opt/data`; `podman secret` |

### D8 — The volume and the blueprint copy

| id | decision | because | rejected |
|---|---|---|---|
| D8 | the volume `<name>-data` is created with `podman volume create` guarded by `podman volume inspect`, as `box`; the blueprint is staged by `copy` to `/home/box/.config/agent-iac/<name>/blueprint/` — the collection's `blueprints/base/` first, the deployment's `blueprint/` over it — then `box-blueprint-sync.sh` runs `podman unshare rsync -a --checksum --itemize-changes <staging>/ <volume>/_data/` and `podman unshare chown -R 10000:10000` on the copied files; the task is `changed_when` the rsync output is non-empty, and notifies the restart handler | rootless volumes are owned by mapped ids only `podman unshare` can write; rsync's itemize output is the change signal | `podman cp`; a bind mount; copying on every apply unconditionally |

### D9 — The service lifecycle

| id | decision | because | rejected |
|---|---|---|---|
| D9 | `podman pull <image>:<version>` as `box`, guarded by `podman image exists`; the quadlet file `template`d; `daemon-reload` only when the file changed; `enable --now <name>` guarded by `is-active`; a handler `restart <name>` notified by the blueprint sync, the env file and the quadlet file | the pull is separate so a missing image fails loudly, not in the restart loop | `AutoUpdate=registry` (the tag is pinned on purpose) |

### D10 — Idempotence guards, named

| task | guard | changed when |
|---|---|---|
| create the volume | `podman volume inspect <name>-data` rc | the inspect failed and create ran |
| pull the image | `podman image exists <image>:<version>` rc | the pull ran |
| copy the blueprint | rsync itemize output | the output is non-empty |
| join the tailnet | `tailscale status --json` `.BackendState` | `tailscale up` ran |
| enable linger | `/var/lib/systemd/linger/box` exists | the file was created |
| enable the service | `systemctl --user is-active <name>` | `enable --now` ran |
| write any file | `template`/`copy` checksum | the checksum differed |

### D11 — Backup, restore, drill, status

| id | decision | because | rejected |
|---|---|---|---|
| D11 | `/usr/local/bin/box-backup <name>`, run by root from `/etc/cron.d/box-<name>`: `systemctl --user -M box@ stop <name>`, then `su - box -c 'podman unshare restic backup <volume>/_data --tag <name>'` with the restic env file, then `systemctl --user -M box@ start <name>` in a `trap` so the start runs on failure too, errors to `logger`; the cron line `0 4 * * * root /usr/local/bin/box-backup <name>`; `restore.yml`: stop, `podman unshare restic restore <snapshot> --target / --delete` as `box`, start; `restore_drill.yml`: `restic restore latest --target /tmp/drill-<name>` then `diff -rq` against `<volume>/_data` excluding `logs/` and `sessions/`, non-zero on a difference; `status.yml`: `podman ps --filter name=<name> --format '{{.State}} {{.Image}}'` and `restic snapshots --latest 1 --json` | one minute of downtime buys a one-step restore; the trap keeps the agent up on a failed backup; the drill never touches the service | a `pre_backup` hook; a restore that needs `hermes import`; a systemd timer (one more unit for one line) |

### D12 — The restic repository in this version

| id | decision | because | rejected |
|---|---|---|---|
| D12 | `backup` is any restic URL; the example uses `sftp:`; `apply` generates an ed25519 key for `box` if absent and `status` prints its public half for the operator to authorise on the SFTP host; `restic init` runs guarded by `restic snapshots` succeeding | the client's bucket and the no-delete key come with a later version; SFTP needs no account | a `local:` path on the Pi; a bucket now |

### D13 — The gate

| id | decision | because | rejected |
|---|---|---|---|
| D13 | `make gate` runs, in order: `openspec validate --all --strict --no-interactive`, `uv run yamllint .`, `uv run ansible-lint`, one `uv run ansible-playbook --syntax-check` line over `playbooks/*.yml` with the collection installed into `.ansible/` (gitignored), `uv run pytest -q`; `make gate` is the recipe, prose names it | everything a change can break without a host | molecule; a container-based integration test |

### D14 — The tests

| id | decision | because | rejected |
|---|---|---|---|
| D14 | `tests/test_box_schema.py`: the valid example, each missing key, an extra key, an unknown runtime, a tagged image; `tests/test_templates.py`: renders every file in `roles/box/templates/` with Jinja2 from `tests/conftest.py`'s sample vars and asserts the needles below; `tests/test_sops.py`: encrypts a dict with the committed throwaway key `tests/keys/example.age`, decrypts it through `sops`, asserts equality — fails loudly when `sops` or `age` is absent | render tests catch a broken variable before a host does | skipping when binaries are missing |

| template | needle |
|---|---|
| `box.container.j2` | `ContainerName=example` · `Image=docker.io/nousresearch/hermes-agent:v2026.9.24` · `Exec=gateway run` · `AutoUpdate=none` · `Restart=always` |
| `nftables.conf.j2` | `policy drop` · `iifname "tailscale0" accept` · `udp dport 41641 accept` |
| `env.j2` | one `NAME=value` line per manifest env name, nothing else |
| `restic.env.j2` | `RESTIC_REPOSITORY=` · `RESTIC_PASSWORD=` |
| `cron.j2` | `0 4 * * * root /usr/local/bin/box-backup example` |
| `auto-upgrades.j2` | `APT::Periodic::Unattended-Upgrade "1";` |
| `box-backup.sh.j2` | `trap` · `podman unshare restic backup` · `systemctl --user -M box@ start example` |
| `box-blueprint-sync.sh.j2` | `rsync -a --checksum --itemize-changes` · `chown -R 10000:10000` |

### D15 — The docs that change

| id | decision | because | rejected |
|---|---|---|---|
| D15 | `docs/architecture.md`: `## The host` says Raspberry Pi OS Lite and a systemd user service through quadlet, and names no other OS; the box diagram's `ALPINE … OpenRC` line becomes `PI OS … quadlet`; the manifest paragraph and block lose `pre_backup`; the backup bullets say stop–snapshot–start; `## The box` gains the Imager and bootstrap step and "`target` is always a tailnet name". `CLAUDE.md`: the invariant *No systemd on the host* is replaced by *One host OS.* Raspberry Pi OS (Debian) today; another host OS lands as a decision, not a branch in a role; the vocabulary line says "a four-field manifest". `README.md`: the one-paragraph pitch, the five steps (flash with Imager and bootstrap · copy the example · secrets · `box.yaml` and blueprint · `make apply`), links to `docs/architecture.md` and `docs/host.md` | a decision in force is edited where it lives | leaving the page stale until the next version |

### D16 — The host checklist

| id | decision | because | rejected |
|---|---|---|---|
| D16 | `docs/host.md`: the Imager settings (Raspberry Pi OS Lite 64-bit; hostname; the holder's user; the operator's SSH public key; Wi-Fi; SSH on), first boot, then `curl -fsSL <raw url of contrib/bootstrap-pi.sh> \| sudo sh -s -- <tailscale auth key> "<operator ssh public key>"`, and how the operator confirms the node on the tailnet | the one page a client follows; no agent-iac on their machine | a wizard; a second script |

## Dependencies

Python, in `pyproject.toml` under `[dependency-groups] dev`, resolved by `uv`:
- `ansible-core>=2.19,<3`
- `ansible-lint>=25.0`
- `yamllint>=1.35`
- `pytest>=8.0`
- `jinja2>=3.1` (also a dependency of ansible-core; named because the tests import it)
- `pyyaml>=6.0`

Ansible collections, in `requirements.yml`:
- `community.sops>=2.0.0,<3.0.0`
- `community.general>=10.0.0`

Binaries on the operator's machine, documented in `README.md`, not installed by the change: `sops`, `age`,
`restic`, `openspec`, `uv`.

## Risks / Trade-offs

- [The image's first-boot chown behaves differently under rootless] → the stage2 hook degrades gracefully on
  chown failure; the acceptance version runs it on the real volume; a failure there is a task change, not a plan change.
- [The migration rewrites `config.yaml` on every boot, so rsync sees a change every apply] → the sync compares the
  staged blueprint against the volume with `--checksum`; if the acceptance shows a spurious change, `config.yaml`
  is excluded from the change signal after the first copy, recorded in `docs/host.md`.
- [`unattended-upgrades` upgrades Podman under a running container] → accepted; the service restarts on the next
  boot; pinning the Podman package is the fix when it bites.
- [The SFTP key must be authorised by hand on the operator's machine] → `status` prints it; the acceptance version
  does it once.
- [A backup at 04:00 interrupts a conversation] → accepted for a personal agent; a later version may pick the hour.

## Verdict

Five phases, no hand step. Four spec deltas, the host and the contract edited in the docs, and a gate that now
has five commands.

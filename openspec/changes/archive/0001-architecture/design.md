# 0001-architecture — design

How the settled architecture lands in the repo: the decisions, and the exact text the build places. Verdict:
write three files, change no behaviour.

## Context

The repo holds the mf-* bootstrap (`Makefile`, `CLAUDE.md`, `CHANGELOG.md`, `openspec/`, `.gitignore`) and a
one-line `README.md`. `openspec/specs/` is empty. The gate is `openspec validate --all --strict`. `.minions/` is
gitignored. See [proposal](proposal.md) for why.

The decisions below were settled in a grilling outside the repo. They are recorded here so the repo stands alone:
nothing in it points back.

## Goals / Non-Goals

**Goals:**
- A reader of `docs/architecture.md` knows what agent-iac is, what a box is, and what an agent and a deployment
  declare.
- A builder of the next change finds the `box.yaml` and runtime-manifest contracts fixed, with Hermes written out.
- `CLAUDE.md` states the invariants a change may not break, and the five words.

**Non-Goals:**
- Any code, role, playbook or Make target.
- A spec delta: no behaviour exists yet. Specs arrive with the first role.
- A `README.md` pitch.

## Decisions

### D1 — The essence

| id | decision | because | rejected |
|---|---|---|---|
| D1 | agent-iac is a tool on the operator's machine that turns a machine they already have into a **box** for one agent, and keeps it so by re-applying one file. Five sentences define it: a declared machine becomes the box; the agent runs rootless from a pinned official image with its state on a volume; secrets are encrypted in the repo; backups leave the box and provably restore; nothing listens publicly | each sentence is a mechanism a later change builds; nothing else is the product | a sandbox service, a scheduler, a fleet dashboard, a per-agent config language |

### D2 — The box

| id | decision | because | rejected |
|---|---|---|---|
| D2 | one box = one **target** + one **runtime** + one deployment repo; one agent per box; the target is a plain host the operator already owns — a Raspberry Pi first, a VPS or a Proxmox guest later; agent-iac creates no machines | one agent = one tenant holds for every runtime; targets are mixed and client-owned | Railway (a container is not a host: no fence, no host hardening, the backup key inside the agent's container); several agents in one box |

```
 operator's Mac                       the box: a Pi today; a VPS or a Proxmox guest later
 ┌──────────────────────────┐  ssh   ┌───────────────────────────────────────┐
 │ deployment repo (private)│───────▶│ ALPINE   rootless podman · tailscale   │
 │  box.yaml · blueprint/   │        │          nftables · restic · OpenRC    │
 │  secrets.sops.yaml       │        │  ┌─────────────────────────────────┐  │
 │  requirements.yml ──┐    │        │  │ the agent's official image      │  │
 └─────────────────────┼────┘        │  │ state volume · blueprint copied │  │
                       ▼             │  └─────────────────────────────────┘  │
 agent-iac (public collection)       └───────────────────────────────────────┘
 client phone ─Telegram─▶ Telegram ◀─poll─ the box · client Mac ─tailnet─▶ gateway port
```

### D3 — The host

| id | decision | because | rejected |
|---|---|---|---|
| D3 | **Alpine** is the one host OS; **OpenRC** supervises one service per box; **rootless Podman**, one unprivileged user per box; the agent's official image runs **unmodified**; the host is reachable **only over Tailscale**, nftables drops everything else inbound | the host must be systemd-free; Alpine has a cloud image and official Pi images, a supervising init, and a tiny footprint; the container's libc is not a boundary, the host is | Debian or Devuan (Devuan: no cloud image, no supervision); NixOS (systemd); FreeBSD (Linux containers experimental); rebuilding the image on Alpine; a second host OS (a roles-branch cost in every role) |

### D4 — The runtime manifest

| id | decision | because | rejected |
|---|---|---|---|
| D4 | the agent-agnostic seam is a **five-field manifest** per runtime: `image · state · env · pre_backup · blueprint_mount`; the image tag comes from `box.yaml`'s `version`; agent-iac never parses the agent's own config | an agent declares what the box must know and nothing more; the agent never knows agent-iac exists | a per-agent config language; `ports`, `healthcheck`, `human_once`, `run` (each returns with the change that needs it) |

The Hermes manifest, as the doc states it:

```yaml
# runtimes/hermes.yaml
image: docker.io/nousresearch/hermes-agent     # the official image, unmodified; the tag is box.yaml's version
state:
  - /opt/data                                  # everything Hermes keeps; backed up as a whole
env:                                           # the secret names the runtime reads
  - TELEGRAM_BOT_TOKEN
  - OPENROUTER_API_KEY
pre_backup: hermes backup --quick              # exec'd in the container before restic, so SQLite is not torn
blueprint_mount: /opt/data                     # where the blueprint's files are copied before start
```

### D5 — `box.yaml`

| id | decision | because | rejected |
|---|---|---|---|
| D5 | a deployment is one `box.yaml` of **five fields**: `name · target · runtime · version · backup`; nothing runtime-specific inside; `tier` and `egress` arrive with the fence | a model choice, an allowlist of users, a cron line are the agent's settings and live in the blueprint | `allowed_users`, `cron`, `access`, fixed-path fields (`blueprint`, `secrets`) |

```yaml
# box.yaml
name: example
target: example.tailnet.example       # the host, as SSH reaches it
runtime: hermes                       # names runtimes/hermes.yaml
version: v2026.10.1                   # the pinned image tag
backup: sftp:user@mac:/backups/example   # a restic repository URL; a bucket later
```

### D6 — Secrets

| id | decision | because | rejected |
|---|---|---|---|
| D6 | **sops + age**: `secrets.sops.yaml` in the deployment repo, keys readable, values encrypted to the operator's age public key; at apply, Ansible decrypts on the operator's machine and writes a `0600` env file for the box user; the age private key never leaves the operator's machine | nothing to unseal; diffs show which key changed; the agent reads only its own env | Ansible Vault (ties secrets to Ansible); `podman secret` (plaintext on disk); a secrets server |

### D7 — Backups

| id | decision | because | rejected |
|---|---|---|---|
| D7 | **restic** from the host on cron over the manifest's `state` paths, after `pre_backup`; the restic repository is a URL in `box.yaml`; a **restore drill** from the operator's machine is a release gate of every change that touches backup; prune runs from the operator's machine, never on the box; a bucket credential, when a bucket is used, cannot delete | the box must not hold the key that destroys its own backups; "backed up" is proven by a restore, not a log line | backup from inside the agent's container; snapshots as the only backup; prune on the box |

### D8 — The tiers

| id | decision | because | rejected |
|---|---|---|---|
| D8 | two tiers keyed to the box, not to the agent's settings: **open** — the box as D3–D7 describe it; **fenced** — plus a proxy container on an internal Podman network with a CONNECT allowlist by domain, nftables outbound, every deny logged; a third tier, *sealed*, is a backlog line. The page states them as a table whose rows begin `| open |` and `| fenced |` | a tier is what the agent cannot undo; an agent's approval mode is a convenience, not a control | tiers keyed to Hermes knobs; a budgeted LLM key inside the fenced tier (it belongs with the gateway) |

### D9 — The repos and the knowledge base

| id | decision | because | rejected |
|---|---|---|---|
| D9 | **library, not template**: a deployment repo holds data only — `box.yaml`, `blueprint/`, `secrets.sops.yaml`, a four-line `Makefile`, `requirements.yml` pinning the collection to a git tag; one private repo per client; the collection ships `blueprints/base/`, and the role copies the base first, then the deployment's `blueprint/` over it, **whole file, no merge**; the knowledge base reaches the client's devices through **git**: the agent commits and pushes every write, Obsidian's Git plugin pulls on the client's Mac | a fix is a one-line bump in each repo; the client can leave on a public tag; a blueprint overlay holds only what differs; git conflicts are visible, sync conflicts are not | a full copy per client; a fleet index before the fourth box; Syncthing or Obsidian Sync as the first sync |

### D10 — Invariants and vocabulary

| id | decision | because | rejected |
|---|---|---|---|
| D10 | `CLAUDE.md` carries the invariants and the five words, as the two sections below | the build reads `CLAUDE.md`; a rule that lives only in a doc is not enforced | a separate `docs/invariants.md` |

The `## Invariants` section, word for word:

```markdown
## Invariants (hold for every change)

- **Generic.** The repo names no person, company or client. Examples use `example`.
- **No plain secret.** A secret is encrypted with sops + age or absent. No token, key or password in clear.
- **Pinned.** Every image, collection and plugin is pinned to a tag or a commit. Nothing follows `latest`.
- **Creates no machines.** agent-iac starts from "a host exists". Flashing a Pi or creating a VPS is outside it.
- **Extends, never wraps.** The agent runs its official image unmodified and never knows agent-iac exists.
- **The box never reaches back.** Nothing on a box names the operator's machine, the vault or this repo's path.
- **No systemd on the host.** The host is Alpine with OpenRC. A mechanism that needs systemd is not used.
```

The `## Vocabulary` section, word for word:

```markdown
## Vocabulary — five words, one meaning each

**box** · one machine made into a home for one agent — **target** · the machine before it is a box, as SSH
reaches it — **runtime** · one kind of agent, declared by a five-field manifest — **tier** · what the box
enforces around the agent: `open` or `fenced` — **blueprint** · the agent's own config files, copied in at start.
```

### D11 — The backlog

| id | decision | because | rejected |
|---|---|---|---|
| D11 | the deferred items are cards in `.minions/backlog.md`, untracked by the line's convention, one card per item: `- **0001·Bn — title**`, then `- **What:**`, `- **Trigger:**`, `- **Status:** open`; the same items are listed with their triggers under *Not in this change* in the proposal, which is tracked | the mf-* paydown flow reads `.minions/backlog.md`; the tracked proposal keeps the public record | tracking `.minions/backlog.md`; a `docs/backlog.md` outside the paydown flow |

### D12 — No spec delta

| id | decision | because | rejected |
|---|---|---|---|
| D12 | `skip_specs: true` with `specs/.gitkeep`; the contracts in D4 and D5 live in `docs/architecture.md`; the first role's change writes the first spec | a spec describes behaviour, and none exists | inventing requirements for an empty repo |

## The architecture page

`docs/architecture.md` has these sections, in this order, each opening with one line that says what it decides:

```
# agent-iac — architecture
## The essence            D1: the five sentences
## The box                D2: the diagram
## The host               D3
## The runtime manifest   D4: the five fields; the Hermes manifest block
## box.yaml               D5: the five fields; the example block
## Secrets and backups    D6, D7
## The tiers              D8: a two-row table — tier · what the box enforces
## The repos and the knowledge base   D9
```

It names no vault, no brief, no path outside the repo, and no person.


## The cards

The backlog's cards, in this order, ids `0001·B1` to `0001·B18`. Each is `title — trigger`; the card's **What**
line is the title expanded to one sentence.

1. The Claude Code manifest on paper — a second runtime is wanted.
2. `run` in the manifest (`service | job`) — the first runtime that exits.
3. `healthcheck` in the manifest — a box must be watched.
4. The `/login` plugin, `make login`, the client re-login page — the first runtime or client needing a paste-back.
5. `fleet-index` and `apply-all` — the fourth box.
6. The base blueprint as its own repo and Hermes distribution — someone wants it without agent-iac.
7. The sealed tier: logs off-box, read-only root, approval outside the model — the first high-risk client.
8. Tailscale ACL tags — the first shared node or second operator.
9. A WireGuard overlay instead of Tailscale — a box that must not depend on Tailscale.
10. LUKS on a Pi's data partition — a Pi holding a client's data.
11. Another systemd-free host OS — a target that cannot run Alpine.
12. `contrib/hetzner-alpine.sh`, Alpine written over a stock image through rescue mode — the first VPS box.
13. Per-container CPU and memory limits — a team on one box.
14. A quarantined reader skill: a tool-less model extracts from fetched pages — the first web-reading client.
15. Syncthing as the knowledge-base sync — a minute of git latency feels broken.
16. `memory-diff`: a nightly diff of the knowledge base and memory files to the operator — the first live box with a knowledge base.
17. `operator-root`: hardware-keyed age and Tailscale identities, bucket keys in a password manager, a lost-machine drill — the first client box.
18. `image-provenance`: a signed-release check for the pinned digest, a canary upgrade — the first upgrade that breaks a box.

## Dependencies

None.

## Risks / Trade-offs

- [The contracts drift once a role exists] → the first role's change writes the spec from this page and edits
  the page in the same change.
- [`.minions/backlog.md` is lost with the operator's machine] → the proposal's *Not in this change* keeps the
  same items, tracked.
- [The Hermes manifest's env names are read from the image's docs today and may move] → the first role's change
  re-checks them against the pinned image; the page says so in the manifest block's comment.

## Verdict

Three phases, three files, no code, no spec. The gate stays as it is.

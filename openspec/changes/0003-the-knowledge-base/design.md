# 0003-the-knowledge-base — design

How a box clones a KB, hands the agent its deploy key, ships the sync plugin and opens the dashboard on the tailnet,
and how the gate proves it without a host. Verdict: build it phase by phase, as [tasks](tasks.md) orders; nothing by hand.

## Context

v0.2 shipped the role and the base blueprint with its overlay. In `plugins/module_utils/box_schema.py` the manifest
keys (`:15`), the `box.yaml` keys, all required (`:14`), and the required secrets, the manifest's `env` plus
`HOST_SECRETS` (`:16`, `:89`), are fixed. The quadlet sets only `EnvironmentFile=` and publishes no port
(`roles/box/templates/box.container.j2:9`, asserted at `tests/test_templates.py:65`); the blueprint sync chowns to
`10000:10000`, the image's `hermes` user (`roles/box/templates/box-blueprint-sync.sh.j2:23`).

Facts from the pinned image and the plugin, read at the cut:
- **Bundled skills** `llm-wiki` and `obsidian` ship in the image and are copied into `/opt/data/skills` at every
  start; they find the KB through `WIKI_PATH` and `OBSIDIAN_VAULT_PATH`.
- **`git-hook`** (MIT, v0.5.1, commit `a7303c8`): pulls `--ff-only` before reads, commits and pushes the files each
  turn changed, only in worktrees under `GIT_HOOK_ROOTS`; it skips a commit when git has no identity. Manual install:
  its directory under `$HERMES_HOME/plugins/git-hook`, and `git-hook` in `plugins.enabled` of `config.yaml`.
- **The image ships `git` and `openssh-client`.** `HERMES_DASHBOARD=1` starts `hermes serve` on 9119 under s6;
  off loopback its login is always on; `HERMES_DASHBOARD_BASIC_AUTH_PASSWORD_HASH` takes a stdlib-scrypt string,
  `scrypt$16384$8$1$<salt_b64>$<dk_b64>`.
- **Hermes rewrites its own `.env`**, so nothing here writes one.

## Goals / Non-Goals

**Goals:**
- `make apply` with `kb:` leaves a box whose agent writes `/opt/data/kb` and whose plugin pushes it.
- Hermes Desktop reaches `<target>:9119` over the tailnet, behind the dashboard login.
- Every new template line, validator rule and vendored byte is tested on the operator's machine.

**Non-Goals:**
- Running Ansible against a host in the gate.
- Anything on the client's devices beyond `docs/kb.md`.

## Decisions

### D1 — The manifest grows to six fields

| id | decision | because | rejected |
|---|---|---|---|
| D1 | `MANIFEST_KEYS` becomes `image · state · env · blueprint_mount · environment · ports`; `validate_manifest` refuses an `environment` that is not a mapping of `ENV_NAME` to strings, and `ports` that is not a list of ints from 1 to 65535 (a `bool` is not an int) | the role stays generic: a runtime declares its fixed variables and ports, the role renders them | variables in the blueprint's `.env` (Hermes rewrites it); variables in `box.yaml` (they belong to the runtime, not the deployment) |

### D2 — The Hermes manifest

```yaml
# runtimes/hermes.yaml — env names re-checked against the pinned image's docs at every version bump
image: docker.io/nousresearch/hermes-agent
state:
  - /opt/data
env:
  - TELEGRAM_BOT_TOKEN
  - TELEGRAM_ALLOWED_USERS
  - OPENROUTER_API_KEY
  - HERMES_DASHBOARD_BASIC_AUTH_USERNAME
  - HERMES_DASHBOARD_BASIC_AUTH_PASSWORD_HASH
  - HERMES_DASHBOARD_BASIC_AUTH_SECRET
blueprint_mount: /opt/data
environment:
  HERMES_DASHBOARD: "1"
  WIKI_PATH: /opt/data/kb
  OBSIDIAN_VAULT_PATH: /opt/data/kb
  GIT_HOOK_ROOTS: /opt/data/kb
ports:
  - 9119
```

| id | decision | because | rejected |
|---|---|---|---|
| D2 | the manifest above; the dashboard login is in `env`, so every Hermes box requires it; a test asserts that every `environment` value naming the KB equals `<blueprint_mount>/kb`, the path [D7](#d7) clones to | Desktop works on every box; one KB path, checked | the plain `…_PASSWORD` (the hash keeps the plaintext off the box); a KB path field in the manifest (one more field for one value) |

### D3 — `kb:` in `box.yaml`, and its secret

| id | decision | because | rejected |
|---|---|---|---|
| D3 | `BOX_OPTIONAL_KEYS = ("kb",)`; `validate_box` accepts it and refuses a value not matching `^git@github\.com:[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\.git$`; `missing_secrets(secrets, manifest, box)` adds `KB_DEPLOY_KEY` when `box` has `kb`; `box_load` passes `box` | the pinned host keys are GitHub's ([D5](#d5)); a KB without its key fails before any connection | HTTPS with a token (it expires); any SSH host (unpinned keys) |

### D4 — The deploy key as a Podman secret

| id | decision | because | rejected |
|---|---|---|---|
| D4 | when `kb` is set, as the box user: read `podman secret inspect --format '{{ .Spec.Labels.sha256 }}' <name>-kb-deploy-key`; when it differs from the key's SHA-256, run `podman secret create --replace --label sha256=<hash> <name>-kb-deploy-key -` with the key on `stdin`, `no_log: true`, notifying the restart handler; the key is written with one trailing newline | the key never lands on the volume or in the env file; the label is the idempotence guard without reading the secret back | a file in the box user's home bind-mounted in; the key in the env file (ssh reads a file) |

### D5 — The quadlet

```ini
# box.container.j2 — the lines this change adds, after EnvironmentFile=
{% for k, v in manifest.environment.items() %}
Environment="{{ k }}={{ v }}"
{% endfor %}
{% if box.kb is defined %}
Secret={{ box.name }}-kb-deploy-key,type=mount,target=/run/secrets/kb_deploy_key,uid=10000,gid=10000,mode=0400
Environment="GIT_SSH_COMMAND=ssh -i /run/secrets/kb_deploy_key -o IdentitiesOnly=yes -o StrictHostKeyChecking=yes -o UserKnownHostsFile={{ manifest.blueprint_mount }}/.ssh/kb_known_hosts"
Environment="GIT_AUTHOR_NAME={{ box.name }}"
Environment="GIT_AUTHOR_EMAIL={{ box.name }}@box.invalid"
Environment="GIT_COMMITTER_NAME={{ box.name }}"
Environment="GIT_COMMITTER_EMAIL={{ box.name }}@box.invalid"
{% endif %}
{% for p in manifest.ports %}
PublishPort={{ box_tailnet_ip }}:{{ p }}:{{ p }}
{% endfor %}
```

| id | decision | because | rejected |
|---|---|---|---|
| D5 | the lines above; `blueprints/base/.ssh/kb_known_hosts` holds GitHub's published Ed25519, ECDSA and RSA host keys, whose fingerprints are `SHA256:+DiY3wvvV6TuJJhbpZisF/zLDA0zPMSvHdkr4UvCOqU` (Ed25519), `SHA256:p2QAMXNIC1TJYWeIOttrVc98/R1BUFWu3/LiyKgUfQM` (ECDSA) and `SHA256:uNiVztksCsDhcc0u9e8BujQXVUpKZIDTMczCvj3tD2s` (RSA); the uid `10000` is the image's `hermes` user, as the sync already assumes (backlog 0002·R10) | git's own variables need no config file; `StrictHostKeyChecking=yes` with a pinned file refuses an unknown host; `.invalid` is a reserved domain no mail reaches | `accept-new` (trust on first use); a `.gitconfig` in the blueprint (Hermes's home is its volume, and the identity is per box) |

### D6 — The tailnet address

| id | decision | because | rejected |
|---|---|---|---|
| D6 | `host.yml` reads `tailscale ip -4` after Tailscale is up, every apply, `changed_when: false`, into `box_tailnet_ip`; an empty answer fails apply | a port bound to the tailnet address is unreachable from the LAN even without the ruleset | `0.0.0.0` behind nftables alone (one layer); a `box.yaml` field (it can drift from the node) |

### D7 — The one-time clone

| id | decision | because | rejected |
|---|---|---|---|
| D7 | after `Start the service`, when `kb` is set, as the box user: `podman exec <name> test -d <blueprint_mount>/kb/.git`, retried until its rc is `0` or `1` (the container may still be starting); on `1`, `podman exec --user 10000 <name> git clone <kb> <blueprint_mount>/kb`, `changed_when: true`, its failure naming the repository and git's stderr | the container already holds the key, the host keys and the identity; the agent's user owns the clone; an existing clone is never touched | cloning on the host through `podman unshare` (the key would sit on the host's command path); `git pull` on apply (`git-hook` owns sync) |

### D8 — `git-hook`, vendored

| id | decision | because | rejected |
|---|---|---|---|
| D8 | copy `LICENSE`, `README.md`, `__init__.py`, `plugin.yaml` and `sync.py` from `https://github.com/aean0x/hermes-git-hook` at `a7303c8` into `blueprints/base/plugins/git-hook/`, byte for byte; `blueprints/base/config.yaml` gains `plugins: {enabled: [git-hook]}`; `tests/test_vendored.py` holds the SHA-256 of each file below and fails on any difference or extra file; `.ansible-lint`'s `exclude_paths` gains `blueprints/base/plugins/git-hook/` | pinned and readable; the hashes make the pin a check; a vendored file is not ours to lint | `hermes plugins install` at run time (unpinned, networked); a git submodule (the blueprint sync copies files, not repos) |

| file | SHA-256 at `a7303c8` |
|---|---|
| `LICENSE` | `465dbda8220e2c8252b6b5fdfe323cb17bcfa30f42f65299c35d2dcff2f7a65b` |
| `README.md` | `1bf76997338d2997f32a32c0be94ecaa4699e8058a6185a4e11542662d6ce263` |
| `__init__.py` | `e1b5a9caadb79156f6870ea1e25b19757148c44789659ffcfc66af0068df1b3b` |
| `plugin.yaml` | `b7f59782888b9cbbf049a0313639adbbe3897752caf17943ec252110c67728e5` |
| `sync.py` | `591f6a7343d70a63e5c0ef79e58f4ff0bae9bb5799ccbfd7143f637d850554e5` |

Command: `git show a7303c8:<file> | shasum -a 256` in a clone of the plugin's repository.

### D9 — The base `SOUL.md`

| id | decision | because | rejected |
|---|---|---|---|
| D9 | `blueprints/base/SOUL.md` gains one paragraph: when `/opt/data/kb` exists it is the knowledge base, kept with the `llm-wiki` skill, and every change there is committed and pushed for the agent | the agent learns where its KB is; `llm-wiki` writes its own schema on first use | a KB seed (a trade's schema belongs to its client's blueprint) |

### D10 — The tests

| file | what it asserts |
|---|---|
| `tests/test_box_schema.py` | `kb` accepted when valid, refused as HTTPS; `missing_secrets` names `KB_DEPLOY_KEY` only when `kb` is set; `environment` and `ports` refused when malformed; the Hermes manifest's six names and env list; every KB path in `environment` equals `<blueprint_mount>/kb` |
| `tests/test_templates.py` | `box.container.j2` renders `Environment="HERMES_DASHBOARD=1"` and `PublishPort=100.64.0.1:9119:9119`; with `kb` it renders the `Secret=` line, `GIT_SSH_COMMAND` with `StrictHostKeyChecking=yes`, and `example@box.invalid`; without `kb` none of them. `test_quadlet_publishes_no_port` is replaced by `test_quadlet_publishes_only_on_the_tailnet_address`: every `PublishPort=` line starts with `box_tailnet_ip` |
| `tests/test_plays.py` | the secret task has `no_log: true` and passes the key on `stdin`; the clone task is guarded by the `.git` test and runs as `--user 10000` |
| `tests/test_vendored.py` | the hashes of [D8](#d8), and no other file in the directory |
| `tests/conftest.py` | `box_tailnet_ip: 100.64.0.1` and the dashboard names in the sample secrets |

### D11 — The docs that change

| id | decision | because | rejected |
|---|---|---|---|
| D11 | `docs/kb.md`: the operator makes the private KB repo and `ssh-keygen -t ed25519 -f kb_deploy`, adds `kb_deploy.pub` as a deploy key with write access, puts the private half in sops as `KB_DEPLOY_KEY` and the URL in `kb:`; the client installs Obsidian and its Git plugin, clones the repo, pulls every minute; Hermes Desktop adds a *Remote gateway* at `http://<target>:9119`. `README.md`: step 3 lists the dashboard login and `KB_DEPLOY_KEY`, with the hash line `python3 -c "import base64,getpass,hashlib,os; s=os.urandom(16); d=hashlib.scrypt(getpass.getpass().encode(),salt=s,n=16384,r=8,p=1,dklen=32); print('scrypt\$16384\$8\$1\$'+base64.b64encode(s).decode()+'\$'+base64.b64encode(d).decode())"`; step 4 names `kb`; a link to `docs/kb.md`. `docs/architecture.md`: the manifest block and paragraph say six fields, `box.yaml` names the optional `kb`, *The repos and the knowledge base* names the deploy key, `git-hook` and the dashboard on the tailnet address. `CLAUDE.md`: "four-field manifest" → "six-field manifest" | a decision in force is edited where it lives | leaving the architecture page at four fields |

### D12 — The version

| id | decision | because | rejected |
|---|---|---|---|
| D12 | `galaxy.yml` `version: 0.3.0`; `examples/box/requirements.yml` pins `v0.3.0`; `examples/box/box.yaml` gains `kb: git@github.com:example/example-kb.git`; `examples/box/secrets.sops.yaml` is re-encrypted with `tests/keys/example.age` holding every name [D2](#d2) and [D3](#d3) require, each a placeholder | the example applies as written; `docs/host.md` keeps `v0.2.0`, since `bootstrap-pi.sh` does not change | bumping `docs/host.md` (the script is the same) |

## Dependencies

- `hermes-git-hook` — `https://github.com/aean0x/hermes-git-hook` at commit `a7303c89b429704a31e2df4212ec4f08ee76692a`
  (v0.5.1, MIT), vendored per [D8](#d8). Not installed: copied into the repo.

No new Python package, collection or binary.

## Risks / Trade-offs

- [Hermes's boot migration rewrites `config.yaml` and drops `plugins.enabled`] → the acceptance shows it; the fix is
  a task change, recorded in `docs/kb.md`.
- [The skills sync at each start overwrites a bundled skill the agent edited] → accepted: bundled skills are the
  image's; a client's own skill lives in its blueprint.
- [`tailscale0` is not up when the container starts at boot, so the bind to the tailnet address fails] →
  `Restart=always` retries every five seconds until it is.
- [The dashboard hash holds `$`] → `podman`'s env file and the quadlet take values literally; a template test
  renders one.
- [A KB push conflict with an Obsidian edit] → `git-hook` pulls `--ff-only` and reports a refused push; the conflict
  stays visible in git, as the architecture decided.
- [The uid `10000` in the `Secret=` line and the clone] → the image's `hermes` user, as v0.2 already assumes;
  backlog 0002·R10 moves it into the manifest with a second runtime.

## Verdict

Build the contracts, the quadlet, the key and the clone, the plugin, then the docs; no hand step. The
`box-contracts`, `box-apply` and `box-knowledge-base` deltas, one vendored plugin pinned by hash, and the dashboard on
the tailnet address only.

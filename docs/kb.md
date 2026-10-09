# agent-iac — the knowledge base

How a box keeps a knowledge base (**KB**) the client reads in Obsidian, and how Hermes Desktop reaches the box. The
operator does section 1 once per box; the client does sections 2 and 3 on their own devices.

```
 agent ──writes──▶ /opt/data/kb ──git-hook push──▶ private KB repo ──pull every minute──▶ Obsidian
 Hermes Desktop ──tailnet──▶ <target>:9119 (dashboard login)
```

The box clones the KB once, at the first `make apply` with `kb:` set; it never pulls or resets it after. The
`git-hook` plugin pulls before the agent reads and pushes the files each turn changed, under the box's name: for the
box `example`, `example <example@box.invalid>`. Where the KB sits among the repos: [architecture](architecture.md).

A deployment's own `blueprint/config.yaml` or `SOUL.md` replaces the base file whole: keep `git-hook` in
`plugins.enabled`, or the KB is never pushed, and keep the base `SOUL.md`'s paragraph naming `/opt/data/kb`.

## 1 — The operator: the KB repo and its deploy key

1. Make a **private** GitHub repo for the client's KB, e.g. `example/example-kb`. GitHub is the only host the box
   trusts: its host keys are pinned in `blueprints/base/.ssh/kb_known_hosts`, and `blueprints/base/.ssh/config`
   makes every ssh of the agent to GitHub, the plugin's pushes included, use them and the deploy key.
2. Make a key pair for the box alone: `ssh-keygen -t ed25519 -N '' -C example-kb -f kb_deploy`.
3. In the repo's **Settings → Deploy keys**, add `kb_deploy.pub` and tick **Allow write access**. Then, in
   **Settings → Rules → Rulesets**, add a branch ruleset on the default branch with **Restrict deletions** and
   **Block force pushes**: the deploy key cannot bypass it, so an agent steered by a prompt injection cannot erase
   the KB's history, and the plugin's ordinary pushes still pass. A private repo's rulesets need a paid GitHub plan.
4. Run `sops secrets.sops.yaml` and add the private half as a block: a line `KB_DEPLOY_KEY: |`, then every line
   of `kb_deploy`, indented two spaces. Then delete `kb_deploy` and `kb_deploy.pub`.
5. Add the repo's SSH URL to `box.yaml`: `kb: git@github.com:example/example-kb.git`. On a box that ran without
   `kb:`, the agent may already have written `/opt/data/kb`; git clones only into an empty folder, so move it aside
   first: `podman exec example mv /opt/data/kb /opt/data/kb.old`, as the box user.
6. Run `make apply`. It stores the key as a Podman secret of the box user, restarts a running box so the key is
   mounted, and clones the KB into `/opt/data/kb`.

A clone GitHub refuses fails `apply` with the repository and git's message; check the deploy key in step 3.

## 2 — The client: Obsidian

1. Install [Obsidian](https://obsidian.md) and, in its community plugins, **Git**.
2. Clone the KB repo with the client's own GitHub access, and open the clone as a vault.
3. In the Git plugin's settings, set **Auto pull interval** to `1` minute.

The agent pushes; the client mostly reads. An edit in Obsidian is pushed by the Git plugin, and the agent's next
pull takes it. When both edit one file at once, git refuses the second push and the conflict stays visible in git.

## 3 — The client: Hermes Desktop

The dashboard listens on port `9119` of the box's tailnet address only, so the device running Hermes Desktop is on
the tailnet.

1. In Hermes Desktop, add a **Remote gateway** at `http://<target>:9119`, e.g. `http://example-pi.tailnet.example:9119`.
2. Log in with `HERMES_DASHBOARD_BASIC_AUTH_USERNAME` and the password whose hash is
   `HERMES_DASHBOARD_BASIC_AUTH_PASSWORD_HASH`; the [README](../README.md) shows how to make the hash.

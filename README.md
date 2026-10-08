# agent-iac

agent-iac makes a Raspberry Pi you already have into a **box**: a home for one AI agent. The agent runs its official
image rootless, the Pi is reachable only over your tailnet, secrets stay encrypted in git, and a nightly backup
restores in one step. It is an Ansible collection, `alxb1t.agent_iac`; a deployment is a small private repo that
pins it. How it is built: [architecture](docs/architecture.md).

```
 Pi ──Imager + bootstrap──▶ host on the tailnet ──apply──▶ box running the agent
```

## Set up a box

1. **Flash and bootstrap the Pi.** Raspberry Pi Imager, then one command on the Pi: the
   [host checklist](docs/host.md).
2. **Copy the example.** Copy `examples/box/` out of this repo and make it a private git repo.
3. **Secrets.** Put your age public key in `.sops.yaml`, delete the example `secrets.sops.yaml`, and run
   `sops secrets.sops.yaml` to write the bot token, the allowed users, the OpenRouter key, the Tailscale auth key
   and the restic password.
4. **`box.yaml` and the blueprint.** Set `name`, `target` (the Pi's tailnet name), `version` (the image tag) and
   `backup` (a restic repository URL). Put the agent's own files in `blueprint/`; they replace the base ones.
5. **Apply.** Run `make apply`. The first run prints the box's SFTP key if the backup host refuses it: authorise
   it there, then apply again.

After that: `make status`, `make backup`, `make restore-drill`.

## What you need

- On the operator's machine: `ansible-core`, `sops`, `age`, `restic`.
- To work on this repo: `uv` and `openspec`. `make gate` checks a change.

# agent-iac

agent-iac makes a Raspberry Pi you already have into a **box**: a home for one AI agent. The agent runs its official
image rootless, the Pi is reachable only over your tailnet, secrets stay encrypted in git, and a nightly encrypted
archive in the client's own bucket restores in one step. It is an Ansible collection, `alxb1t.agent_iac`; a
deployment is a small private repo that pins it. How it is built: [architecture](docs/architecture.md).

```
 Pi ──Imager + bootstrap──▶ host on the tailnet ──apply──▶ box running the agent
```

## Set up a box

1. **Onboard, flash and bootstrap.** The client's R2 bucket and age key, the tailnet's policy and auth key, then
   Raspberry Pi Imager and one command on the Pi: the [host checklist](docs/host.md).
2. **Copy the example.** Copy `examples/box/` out of this repo and make it a private git repo.
3. **Secrets.** Put your age public key and the client's in `.sops.yaml`, delete the example `secrets.sops.yaml`,
   and run `sops secrets.sops.yaml` to write the bot token, the allowed users, the OpenRouter key, the dashboard
   login (`HERMES_DASHBOARD_BASIC_AUTH_USERNAME`, `…_PASSWORD_HASH` and `…_SECRET`, a long random string), the
   Tailscale auth key, the R2 key pair (`R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`) and, with a knowledge base,
   `KB_DEPLOY_KEY`. This line prints the password's hash:

   ```sh
   python3 -c "import base64,getpass,hashlib,os; s=os.urandom(16); d=hashlib.scrypt(getpass.getpass().encode(),salt=s,n=16384,r=8,p=1,dklen=32); print('scrypt\$16384\$8\$1\$'+base64.b64encode(s).decode()+'\$'+base64.b64encode(d).decode())"
   ```
4. **`box.yaml` and the blueprint.** Set `name`, `target` (the Pi's tailnet name), `version` (the image tag),
   `backup` (the R2 bucket, `r2:<account id>/<bucket>`) and, optionally, `kb` (the knowledge base's GitHub SSH URL).
   Put the agent's own files in `blueprint/`; they replace the base ones. The knowledge base and Hermes Desktop:
   [knowledge base](docs/kb.md).
5. **Apply.** Run `make apply`.

After that: `make status`, `make backup`, `make restore-drill`, and `make restore` to bring the box back: the
example's [RESTORE.md](examples/box/RESTORE.md).

## What you need

- On the operator's machine: `ansible-core`, `sops`, `age`, `rclone`.
- To work on this repo: `uv` and `openspec`. `make gate` checks a change.

# agent-iac — the host checklist

What happens, once, before `make apply`: the operator and the client set up the bucket, the keys and the tailnet,
then whoever holds the Pi flashes it, boots it and runs one command. No agent-iac on the holder's machine. Then the
operator takes over with `make apply`, per the [architecture](architecture.md).

```
 onboarding ──▶ Imager ──▶ first boot ──▶ bootstrap ──▶ on the tailnet ──▶ hand-over ──▶ make apply
 (operator +     (holder)   (holder)       (holder,      (operator checks)  (operator)
  client)                                   on LAN)
```

## 1 — Onboarding: the bucket, the keys, the tailnet

The client owns the bucket and holds a key to every archive; the operator holds the other. Each can restore alone.

**The bucket**, in the client's own Cloudflare account:

1. In R2, create a bucket, e.g. `example-backups`.
2. In the bucket's settings, add one **bucket lock rule**: no prefix, **4 days**. The box cannot delete or overwrite
   an archive younger than that, so the newest four nights survive a compromised box. A longer lock would refuse
   every delete the box makes to keep its newest five. A compromised box can still upload an archive of its own:
   after one, rotate the token, then restore an archive from before it by name, `-e box_archive=<name>`.
3. Create an R2 API token with **Object Read & Write**, scoped to that bucket alone. It cannot edit the bucket's
   settings, so the box cannot lift the lock. It is a key pair: an access key id and a secret.
4. In the deployment repo, set `box.yaml`'s `backup` to `r2:<account id>/<bucket>`, e.g.
   `r2:0123456789abcdef0123456789abcdef/example-backups`; the account id is on the R2 overview page. Run
   `sops secrets.sops.yaml` and add the pair as `R2_ACCESS_KEY_ID` and `R2_SECRET_ACCESS_KEY`.

**The client's key:**

1. The client runs `age-keygen -o client.age`. It prints the public key, `age1…`.
2. The operator adds that public key beside their own in the deployment repo's `.sops.yaml`, comma-separated:
   `age: <operator's key>,<client's key>`. Then `sops updatekeys secrets.sops.yaml` re-encrypts the secrets to both.
   Every archive goes to the same keys.
3. The client keeps `client.age` in their password manager and deletes the file. With it, the client can restore
   without the operator: [the example's RESTORE.md](../examples/box/RESTORE.md).

**The tailnet**, in the operator's Tailscale admin console:

1. In **Access controls**, set the policy to:

   ```json
   {"tagOwners": {"tag:box": ["autogroup:admin"]}, "acls": [{"action": "accept", "src": ["autogroup:member"], "dst": ["*:*"]}, {"action": "accept", "src": ["autogroup:shared"], "dst": ["tag:box:22,9119"]}]}
   ```

   A `tag:box` node is no member, so it reaches nothing on the tailnet; the operator's own devices are members and
   reach it. The client, once the node is shared with them, is in `autogroup:shared`, not a member, and reaches the
   box's dashboard and SSH only. The policy replaces the tailnet's default, which lets every node reach every other.
2. In **Settings → Keys**, generate an auth key: tagged `tag:box`, single use, pre-approved.

**The knowledge base**, with `kb:` only: section 1 of [knowledge base](kb.md).

## 2 — Flash with Raspberry Pi Imager

In Raspberry Pi Imager, choose the device, then **Raspberry Pi OS Lite (64-bit)**, then the SD card. In the OS
customisation settings:

| setting | value |
|---|---|
| hostname | the box's name, e.g. `example-pi` |
| username and password | the holder's own user |
| Wi-Fi | the network the Pi lives on; skip it for Ethernet |
| locale | the holder's time zone; the backup runs at 04:00 in it |
| SSH | on, **public-key authentication only**, with the operator's SSH public key |

Write the card.

## 3 — First boot

Put the card in the Pi and power it. The first boot resizes the card and joins the network; give it a few minutes.
From a machine on the same network, `ssh <user>@<hostname>.local` reaches it.

## 4 — Run the bootstrap

The operator sends the holder the auth key of section 1 and their SSH public key. In an SSH session on the Pi, run:

```sh
curl -fsSL https://raw.githubusercontent.com/alxb1t/agent-iac/v0.4.0/contrib/bootstrap-pi.sh | sudo sh -s -- "<operator ssh public key>"
```

It asks for the auth key and does not echo it, so the key is on no command line and in no shell history. It installs
`python3`, and Tailscale from Tailscale's apt repository behind its pinned signing key, joins the tailnet with the
key, and puts the operator's key in root's `authorized_keys`. Running it again changes nothing.

## 5 — The operator confirms the node

On the operator's machine:

- `tailscale status` lists the Pi by its hostname.
- `ssh root@<hostname>` logs in over the tailnet.

That tailnet name is the `target` in `box.yaml`. The host exists; the holder is done.

## 6 — The hand-over

1. In the Tailscale admin console, open the node's menu, choose **Share**, and share it with the client's email.
   The client's devices then reach the dashboard on `<target>:9119`: section 3 of [knowledge base](kb.md).
2. For the client to run `make restore` without the operator, add the client's SSH public key to root's keys:
   `ssh root@<target> 'cat >> /root/.ssh/authorized_keys' < client.pub`. A Pi re-flashed later takes the client's
   key in place of the operator's in the bootstrap of section 4.
3. Run `make apply`.
4. A model provider that logs in at a terminal, not by an API key in the secrets, logs in on the box as the box
   user:

   ```sh
   ssh root@<target>
   su - box
   export XDG_RUNTIME_DIR=/run/user/$(id -u)
   podman exec -it <name> hermes auth add <provider>
   ```

## 7 — Migrating a hand-installed Hermes

When the box replaces a Hermes installed by hand, its state moves in after section 6, through `restore`. Provider
logins come with it; the old `.env` does not.

1. Move every value of the old install's `.env` into `secrets.sops.yaml`: `sops secrets.sops.yaml`. The box removes
   the imported `.env`, so a value left out is lost.
2. On the old machine, `hermes update` an install much older than the box's `version`.
3. On the old machine, `hermes backup -o migrate.zip`. Then stop the old install's gateway: a bot token is polled by
   one gateway at a time.
4. Copy `migrate.zip` to the operator's machine, e.g. `scp <old machine>:migrate.zip .`.
5. In the deployment repo, run `make migrate ZIP=migrate.zip`. It copies the zip to the box, imports it, removes its
   `.env` and starts the agent. The zip itself stays where it was.
6. Delete `migrate.zip` on both machines: it holds the old install's secrets in clear.

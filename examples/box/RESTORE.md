# Restore this box

How the client, or the operator, brings the box back from its bucket with their own age key, with or without the
operator. Every night the box uploads an encrypted archive, `<name>-<UTC timestamp>.zip.age`, and keeps the newest
five.

```
 R2 bucket ──rclone──▶ your machine ──age -d, your key──▶ backup.zip ──▶ hermes import
```

## With this repo: `make restore`

On a machine that reaches the box as root over SSH, with `ansible-core`, `sops`, `age` and `rclone` installed. The
operator's machine does; the client's does once the operator has added the client's SSH public key at the hand-over,
or once the client has bootstrapped a re-flashed Pi with their own key.

1. Point `SOPS_AGE_KEY_FILE` at your age key file, e.g. `export SOPS_AGE_KEY_FILE=$HOME/client.age`, or put the key
   where sops looks by default. The same key decrypts `secrets.sops.yaml`.
2. Run `make restore`. It downloads the newest archive, decrypts it on your machine, stops the agent, imports the
   archive, starts the agent again and, with `kb:`, clones the knowledge base afresh. The decrypted copy is removed
   from your machine and from the box.

`make status` names the newest archive. To restore an older one, name it:

```sh
ansible-playbook alxb1t.agent_iac.restore -e box_file=$PWD/box.yaml -e box_archive=example-20261001T040000Z.zip.age
```

`make restore` names the archive it picked before it downloads it, and stops on a newest archive dated in the
future: no nightly run wrote it, so the box that uploaded it was compromised. Rotate the R2 token, then name an
archive from before the compromise, as above.

An archive already on your machine, `.zip` or `.zip.age`, restores with `make migrate ZIP=<path>`, a path with no
space in it. A `.zip.age`, e.g. one downloaded from the bucket, keeps its `.env`. A `.zip` is a hand-installed Hermes's
`hermes backup` zip, per section 7 of the [host checklist](../../docs/host.md): its `.env` is removed, so the secrets
come from sops.

## By hand: the dashboard, `age` and `hermes`

Without this repo or the box, on any machine with `age` and Hermes installed:

1. In the Cloudflare dashboard, open the R2 bucket and download the archive, e.g. `example-20261001T040000Z.zip.age`.
2. Decrypt it with your key:

   ```sh
   age -d -i <key> -o backup.zip example-20261001T040000Z.zip.age
   ```

3. Import it into Hermes: `hermes import backup.zip`. Then delete `backup.zip`: it is your agent's state in clear.

# Restore this box

How the client, or the operator, brings the box back from its bucket with their own age key, with or without the
operator. Every night the box uploads an encrypted archive, `<name>-<UTC timestamp>.zip.age`, and keeps the newest
five.

```
 R2 bucket ──rclone──▶ your machine ──age -d, your key──▶ backup.zip ──▶ hermes import
```

## With this repo: `make restore`

On a machine that reaches the box as root over SSH, with `ansible-core`, `sops`, `age` and `rclone` installed:

1. Point `SOPS_AGE_KEY_FILE` at your age key file, e.g. `export SOPS_AGE_KEY_FILE=$HOME/client.age`, or put the key
   where sops looks by default. The same key decrypts `secrets.sops.yaml`.
2. Run `make restore`. It downloads the newest archive, decrypts it on your machine, stops the agent, imports the
   archive, starts the agent again and, with `kb:`, clones the knowledge base afresh. The decrypted copy is removed
   from your machine and from the box.

`make status` names the newest archive. To restore an older one, name it:

```sh
ansible-playbook alxb1t.agent_iac.restore -e box_file=$PWD/box.yaml -e box_archive=example-20261001T040000Z.zip.age
```

## By hand: the dashboard, `age` and `hermes`

Without this repo or the box, on any machine with `age` and Hermes installed:

1. In the Cloudflare dashboard, open the R2 bucket and download the archive, e.g. `example-20261001T040000Z.zip.age`.
2. Decrypt it with your key:

   ```sh
   age -d -i <key> -o backup.zip example-20261001T040000Z.zip.age
   ```

3. Import it into Hermes: `hermes import backup.zip`. Then delete `backup.zip`: it is your agent's state in clear.

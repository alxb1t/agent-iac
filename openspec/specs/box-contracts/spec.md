# box-contracts Specification

## Purpose

The two files a box is declared by — `box.yaml` for a deployment and a runtime manifest for an agent — and the
refusal of a file that does not fit.

## Requirements

### Requirement: Secrets are read only from the encrypted file
`apply` SHALL read secrets only from `secrets.sops.yaml` in the deployment repo, decrypted on the operator's machine.
Every name the manifest's `env` lists SHALL be present in the decrypted file, plus `TAILSCALE_AUTH_KEY`,
`R2_ACCESS_KEY_ID` and `R2_SECRET_ACCESS_KEY`, plus `KB_DEPLOY_KEY` when `box.yaml` sets `kb`.

#### Scenario: A missing secret stops apply
- **WHEN** the decrypted file lacks a name the manifest's `env` lists
- **THEN** `apply` stops before touching the host, naming the missing name and never printing a value

#### Scenario: A kb without its deploy key stops apply
- **WHEN** `box.yaml` sets `kb` and the decrypted file lacks `KB_DEPLOY_KEY`
- **THEN** `apply` stops before touching the host, naming `KB_DEPLOY_KEY`

#### Scenario: No secret is written to the volume
- **WHEN** `apply` has completed
- **THEN** no file under the agent's state volume contains a value from `secrets.sops.yaml`

### Requirement: box.yaml holds five fields and an optional kb
A `box.yaml` SHALL contain the keys `name`, `target`, `runtime`, `version` and `backup`, each a non-empty string,
and MAY contain `kb`. No other key SHALL be accepted. `name` SHALL match `^[a-z][a-z0-9-]{1,31}$`. `runtime` SHALL
name a manifest shipped by the collection. `backup` SHALL be an R2 bucket of the form `r2:<account-id>/<bucket>`,
the account id 32 lowercase hex digits. `kb`, when present, SHALL be a GitHub SSH URL of the form
`git@github.com:<owner>/<repo>.git`.

#### Scenario: A valid box.yaml is accepted
- **WHEN** `apply` reads a `box.yaml` with the five keys and valid values, with or without `kb`
- **THEN** it proceeds, and the values are available to every task

#### Scenario: A missing or extra key is refused
- **WHEN** `apply` reads a `box.yaml` lacking `backup`, or carrying an extra key such as `allowed_users`
- **THEN** it stops before touching the host, naming every offending key in one message

#### Scenario: An unknown runtime is refused
- **WHEN** `runtime` names a manifest the collection does not ship
- **THEN** `apply` stops before touching the host, naming the runtime and the manifests it knows

#### Scenario: A kb that is not a GitHub SSH URL is refused
- **WHEN** `kb` is `https://github.com/example/example-kb.git`
- **THEN** `apply` stops before touching the host, naming `kb`

#### Scenario: A restic URL is refused
- **WHEN** `backup` is `sftp:backup@example-nas:/srv/restic/example`
- **THEN** `apply` stops before touching the host, naming `backup`

### Requirement: A runtime manifest holds eight fields
A runtime manifest SHALL contain exactly `image`, `state`, `env`, `blueprint_mount`, `environment`, `ports`,
`backup` and `restore`. `image` SHALL be an image reference without a tag; the tag SHALL come from `box.yaml`'s
`version`. `state` SHALL be a non-empty list of absolute container paths. `env` SHALL be a list of environment
variable names. `blueprint_mount` SHALL be an absolute container path. `environment` SHALL map environment variable
names to string values that are not secret. `ports` SHALL be a list of TCP port numbers from 1 to 65535. `backup`
and `restore` SHALL each be a non-empty list of strings, a command line run in the runtime's image, holding the
placeholder `{archive}` exactly once.

#### Scenario: The Hermes manifest resolves
- **WHEN** `box.yaml` says `runtime: hermes` and `version: v2026.9.24`
- **THEN** the image to run is `docker.io/nousresearch/hermes-agent:v2026.9.24`, the state path is `/opt/data`, the
  ports are `9119`, the backup command is `hermes backup -o {archive}` and the restore command is
  `hermes import --force {archive}`

#### Scenario: A manifest with a tagged image is refused
- **WHEN** a manifest's `image` carries a tag or digest
- **THEN** validation fails, naming the field

#### Scenario: A manifest with a bad port is refused
- **WHEN** a manifest's `ports` holds `0` or `"9119"`
- **THEN** validation fails, naming `ports`

#### Scenario: A backup command without its archive is refused
- **WHEN** a manifest's `backup` is `[hermes, backup]`
- **THEN** validation fails, naming `backup`

### Requirement: The backup recipients are the secrets' recipients
`apply` SHALL read the age recipients from the first creation rule of `.sops.yaml` beside `box.yaml`, and SHALL
encrypt every archive to each of them. There SHALL be at least one, each an age public key; a client's box carries
the client's and the operator's. A box not named `example` SHALL NOT name a throwaway key of `tests/keys/`.

#### Scenario: Two recipients
- **WHEN** `.sops.yaml` lists the operator's and the client's age public keys
- **THEN** every archive of the box decrypts with either private key alone

#### Scenario: A copied throwaway key stops apply
- **WHEN** a box not named `example` lists in `.sops.yaml` a public key of `tests/keys/`
- **THEN** `apply` stops before touching the host, naming the key and `.sops.yaml`

#### Scenario: No recipient stops apply
- **WHEN** `.sops.yaml` has no `age` recipient
- **THEN** `apply` stops before touching the host, naming `.sops.yaml`

# box-contracts Specification

## Purpose

The two files a box is declared by — `box.yaml` for a deployment and a runtime manifest for an agent — and the
refusal of a file that does not fit.

## Requirements

### Requirement: box.yaml holds five fields
A `box.yaml` SHALL contain exactly the keys `name`, `target`, `runtime`, `version` and `backup`, each a non-empty
string. `name` SHALL match `^[a-z][a-z0-9-]{1,31}$`. `runtime` SHALL name a manifest shipped by the collection.
`backup` SHALL be a restic repository URL.

#### Scenario: A valid box.yaml is accepted
- **WHEN** `apply` reads a `box.yaml` with the five keys and valid values
- **THEN** it proceeds, and the values are available to every task

#### Scenario: A missing or extra key is refused
- **WHEN** `apply` reads a `box.yaml` lacking `backup`, or carrying an extra key such as `allowed_users`
- **THEN** it stops before touching the host, naming every offending key in one message

#### Scenario: An unknown runtime is refused
- **WHEN** `runtime` names a manifest the collection does not ship
- **THEN** `apply` stops before touching the host, naming the runtime and the manifests it knows

### Requirement: A runtime manifest holds four fields
A runtime manifest SHALL contain exactly `image`, `state`, `env` and `blueprint_mount`. `image` SHALL be an image
reference without a tag; the tag SHALL come from `box.yaml`'s `version`. `state` SHALL be a non-empty list of
absolute container paths. `env` SHALL be a list of environment variable names. `blueprint_mount` SHALL be an
absolute container path.

#### Scenario: The Hermes manifest resolves
- **WHEN** `box.yaml` says `runtime: hermes` and `version: v2026.9.24`
- **THEN** the image to run is `docker.io/nousresearch/hermes-agent:v2026.9.24`, the state path is `/opt/data`, and
  the env names are `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ALLOWED_USERS` and `OPENROUTER_API_KEY`

#### Scenario: A manifest with a tagged image is refused
- **WHEN** a manifest's `image` carries a tag or digest
- **THEN** validation fails, naming the field

### Requirement: Secrets are read only from the encrypted file
`apply` SHALL read secrets only from `secrets.sops.yaml` in the deployment repo, decrypted on the operator's machine.
Every name the manifest's `env` lists SHALL be present in the decrypted file, plus `TAILSCALE_AUTH_KEY` and
`RESTIC_PASSWORD`.

#### Scenario: A missing secret stops apply
- **WHEN** the decrypted file lacks a name the manifest's `env` lists
- **THEN** `apply` stops before touching the host, naming the missing name and never printing a value

#### Scenario: No secret is written to the volume
- **WHEN** `apply` has completed
- **THEN** no file under the agent's state volume contains a value from `secrets.sops.yaml`

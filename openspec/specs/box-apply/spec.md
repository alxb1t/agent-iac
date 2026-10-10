# box-apply Specification

## Purpose

What one `apply` guarantees: a Raspberry Pi OS host on the tailnet becomes, and stays, a box running one agent
rootless as a systemd user service, reachable only over the tailnet, and a second apply changes nothing.

## Requirements

### Requirement: Apply converges the host
`apply` SHALL connect to `target` as root over SSH and leave the host with: `podman`, `crun`, `rsync`, `age`,
`rclone`, `nftables`, `unattended-upgrades` and `tailscale` installed; unattended upgrades enabled; the box user with
subuid and subgid ranges and lingering enabled; Tailscale enabled and up; the backup on cron. No restic environment
file SHALL remain in the box user's configuration, nor the SFTP key, its public half, the ssh `config` or the
`known_hosts` that v0.3's backup wrote in the box user's `~/.ssh`.

#### Scenario: A fresh host after bootstrap
- **WHEN** `apply` runs against a host that `bootstrap-pi.sh` left on the tailnet
- **THEN** every item above holds, and `apply` reports each as changed once

#### Scenario: A second apply is a no-op
- **WHEN** `apply` runs again with the same `box.yaml`, blueprint and secrets
- **THEN** it reports zero changed tasks

#### Scenario: A v0.3 box loses its restic password
- **WHEN** `apply` runs on a box that holds `<name>.restic.env` and v0.3's SFTP key
- **THEN** the file and the key are gone afterwards

### Requirement: Inbound traffic reaches the host only over the tailnet
After `apply`, the host SHALL accept inbound connections only on the loopback interface and the Tailscale
interface, plus Tailscale's own UDP port; every other inbound connection SHALL be dropped. Outbound traffic SHALL
be unrestricted.

#### Scenario: SSH from the LAN is dropped
- **WHEN** a connection to port 22 arrives on the LAN interface
- **THEN** it is dropped, while the same connection over the tailnet succeeds

#### Scenario: The ruleset is written only after Tailscale is up
- **WHEN** Tailscale fails to come up during `apply`
- **THEN** the ruleset is not written and `apply` fails, leaving the LAN path open

### Requirement: The agent runs rootless as a systemd user service
`apply` SHALL leave one quadlet per box in the box user's systemd configuration, enabled at boot through lingering,
that runs the pinned image as the box user with the state on a named volume, the blueprint copied into the state
before the first start, the secrets passed as environment variables from a file readable only by the box user, and
every variable of the manifest's `environment` set. The service SHALL restart the container when it exits and start
it at boot. Each port in the manifest's `ports` SHALL be published on the host's tailnet IPv4 address only; no other
port SHALL be published.

#### Scenario: The service starts the gateway
- **WHEN** the service starts
- **THEN** a container named after the box runs `gateway run` from `docker.io/nousresearch/hermes-agent:<version>`,
  owned by the box user, with `/opt/data` on the volume

#### Scenario: A crash restarts the container
- **WHEN** the container's main process exits
- **THEN** systemd starts it again within seconds

#### Scenario: The blueprint lands before first start
- **WHEN** the volume is empty at `apply`
- **THEN** `config.yaml` and `SOUL.md` from the base blueprint, overlaid by the deployment's `blueprint/`, exist in
  the state before the gateway's first start

#### Scenario: A changed blueprint is copied and the service restarted
- **WHEN** a file in the deployment's `blueprint/` differs from the copy in the state
- **THEN** `apply` copies it over and restarts the service, and reports the task as changed

#### Scenario: The manifest's environment reaches the agent
- **WHEN** the service starts a box whose runtime is `hermes`
- **THEN** the container's environment holds `HERMES_DASHBOARD=1` and `WIKI_PATH=/opt/data/kb`

#### Scenario: The dashboard port listens on the tailnet address only
- **WHEN** the service runs on a host whose tailnet IPv4 address is `100.64.0.1`
- **THEN** port 9119 is published on `100.64.0.1` and on no other host address

### Requirement: The agent holds no host privilege
The box user SHALL have no password, no `sudo` rule and no membership in `sudo`. The container SHALL run in the box
user's user namespace, so that root inside the container maps to the box user on the host.

#### Scenario: Root in the container is unprivileged on the host
- **WHEN** a process inside the container runs as root
- **THEN** on the host it runs as the box user's mapped subuid and cannot read `/etc/shadow`

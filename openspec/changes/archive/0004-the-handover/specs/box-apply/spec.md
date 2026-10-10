## MODIFIED Requirements

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

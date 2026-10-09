## MODIFIED Requirements

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

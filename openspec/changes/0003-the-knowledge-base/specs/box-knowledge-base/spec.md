## Purpose

The knowledge base a box keeps: a private git repo the deployment names, cloned once into the agent's state, written
by the agent and pushed every turn under the box's name, with a deploy key that never touches the volume.

## ADDED Requirements

### Requirement: The knowledge base is cloned once
When `box.yaml` sets `kb`, `apply` SHALL clone that repository into `kb` under the runtime's `blueprint_mount`, as
the agent's user inside the container, if no git repository is there yet. `apply` SHALL NOT clone, pull or reset an
existing one. When `kb` is not set, `apply` SHALL clone nothing.

#### Scenario: A fresh box clones its KB
- **WHEN** `apply` runs with `kb` set and `/opt/data/kb` holds no git repository
- **THEN** `/opt/data/kb` holds a clone of the repository, owned by the agent's user, and the task reports changed

#### Scenario: A second apply leaves the KB alone
- **WHEN** `apply` runs again on a box whose `/opt/data/kb` holds a clone with unpushed commits
- **THEN** the clone and its commits are unchanged, and the task reports nothing changed

#### Scenario: A refused clone stops apply
- **WHEN** GitHub refuses the deploy key
- **THEN** `apply` fails, naming the repository and git's message

### Requirement: The deploy key reaches the agent only as a mounted file
When `box.yaml` sets `kb`, `apply` SHALL store `KB_DEPLOY_KEY` as a Podman secret of the box user and mount it into
the container as a file readable only by the agent's user. Git in the container SHALL use that key, and SHALL trust
only the GitHub host keys the base blueprint pins. The key SHALL NOT be written to the env file or the state volume.

#### Scenario: The key is a file, not a variable
- **WHEN** the service runs a box with `kb` set
- **THEN** `/run/secrets/kb_deploy_key` exists in the container with mode `0400`, and no environment variable of the
  container holds the key

#### Scenario: A changed key replaces the secret
- **WHEN** `KB_DEPLOY_KEY` changes in `secrets.sops.yaml` and `apply` runs
- **THEN** the Podman secret holds the new key and the service is restarted

#### Scenario: An unknown host key is refused
- **WHEN** the host answering for `github.com` presents a key the base blueprint does not pin
- **THEN** git refuses the connection

### Requirement: The agent commits under the box's name
When `box.yaml` sets `kb`, the container's environment SHALL set git's author and committer to the box's name, with
the email `<name>@box.invalid`.

#### Scenario: A commit names the box
- **WHEN** the agent commits in the KB of the box `example`
- **THEN** the commit's author and committer are `example <example@box.invalid>`

### Requirement: The sync plugin ships with the base blueprint
The base blueprint SHALL carry the `git-hook` Hermes plugin, copied unmodified from one pinned commit of its
repository, and SHALL enable it in `config.yaml`. The runtime manifest's `environment` SHALL limit the plugin to the
KB path.

#### Scenario: The vendored files match the pinned commit
- **WHEN** the gate runs
- **THEN** every file under `blueprints/base/plugins/git-hook/` hashes to the value recorded for commit `a7303c8`

#### Scenario: The plugin touches only the KB
- **WHEN** the service starts a box whose runtime is `hermes`
- **THEN** the container's environment holds `GIT_HOOK_ROOTS=/opt/data/kb`

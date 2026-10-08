# box-backup Specification

## Purpose

The nightly snapshot of the agent's state, the one-step restore that brings a box back, the drill that proves it,
and the status line.

## Requirements

### Requirement: Nightly backup by stop, snapshot, start
At 04:00 host time the box SHALL stop the agent's service, back up the state volume to the restic repository named
in `box.yaml`, and start the service again, in that order. The backup SHALL run as the box user. A failed backup
SHALL still restart the service and SHALL leave an error in the system log.

#### Scenario: The nightly snapshot lands
- **WHEN** the cron line fires
- **THEN** `restic snapshots` on the repository shows a new snapshot of the state, and the service is running again

#### Scenario: A backup failure does not keep the agent down
- **WHEN** the repository is unreachable at 04:00
- **THEN** the service is started again and the failure is logged

### Requirement: Restore is one step
`restore` SHALL stop the service, replace the contents of the state volume with the latest snapshot (or a named
one), and start the service. No other step SHALL be needed for the agent to resume with its previous state.

#### Scenario: A fresh box resumes after restore
- **WHEN** `apply` has run on a fresh host and `restore` is run against the same repository
- **THEN** the agent starts with the sessions and memories of the snapshot

### Requirement: The restore drill proves a snapshot
`restore-drill` SHALL restore the latest snapshot into a scratch directory on the box and compare it with the live
state, file by file, without touching the service. It SHALL exit non-zero on any difference outside the paths the
agent writes continuously.

#### Scenario: A clean drill
- **WHEN** `restore-drill` runs after a backup with no writes in between
- **THEN** it reports no differences and exits zero

### Requirement: Status is three lines
`status` SHALL print whether the box's container is running, the image it runs, and the time of the latest snapshot.

#### Scenario: A healthy box
- **WHEN** `status` runs against a running box with one snapshot
- **THEN** it prints the container state, the image reference and the snapshot time, and nothing else

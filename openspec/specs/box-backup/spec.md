# box-backup Specification

## Purpose

The nightly encrypted archive of the agent's state, the one-step restore that brings a box back, the drill that proves it,
and the status line.

## Requirements

### Requirement: Restore is one step
`restore` SHALL fetch the newest archive (or a named one), decrypt it on the machine running it, stop the service,
import it into the state volume with the manifest's `restore` command, and start the service. When `box.yaml` sets
`kb`, it SHALL then replace `kb` under the blueprint mount with a fresh clone. No other step SHALL be needed for the
agent to resume with its previous state. The decrypted archive SHALL be removed from both machines at the end. It
SHALL print the archive's name before the download, and SHALL stop when the newest archive is dated after the time
of the machine running it, unless the archive is named.

#### Scenario: A fresh box resumes after restore
- **WHEN** `apply` has run on a fresh host and `restore` is run against the same bucket
- **THEN** the agent starts with the sessions and memories of the archive

#### Scenario: The KB comes back from its remote
- **WHEN** `restore` runs on a box with `kb` set
- **THEN** `/opt/data/kb` is a clone of the KB repo with its history, not the archive's copy

#### Scenario: An unreachable box leaves no decrypted copy
- **WHEN** `restore` runs while the box is off the network, or the box drops during the copy of the zip
- **THEN** it fails before decrypting, or removes the decrypted archive from the machine running it

#### Scenario: A planted archive is refused
- **WHEN** a compromised box has uploaded `<name>-99991231T000000Z.zip.age` and `restore` runs without naming one
- **THEN** it stops before the download, naming that archive, and the box is not touched

#### Scenario: The client restores alone
- **WHEN** the client runs `make restore` from their deployment repo with their own age key
- **THEN** the restore completes without the operator's key

### Requirement: Status is three lines
`status` SHALL print whether the box's container is running, the image it runs, and the name of the newest archive
in the bucket.

#### Scenario: A healthy box
- **WHEN** `status` runs against a running box with one archive
- **THEN** it prints the container state, the image reference and the archive's name, and nothing else

### Requirement: Nightly backup by archive, encrypt, upload
At 04:00 host time the box SHALL run the manifest's `backup` command in the running container, encrypt the archive
to the recipients of `.sops.yaml` with `age`, and upload it to the bucket named in `box.yaml` as
`<name>-<UTC timestamp>.zip.age`. The agent SHALL keep running. No unencrypted copy of the archive SHALL be written
outside the state volume, and the copy inside it SHALL be removed after the upload. A failed backup SHALL leave an
error in the system log and exit non-zero.

#### Scenario: The nightly archive lands
- **WHEN** the cron line fires
- **THEN** the bucket holds a new `<name>-<timestamp>.zip.age`, and the service was never stopped

#### Scenario: An unreachable bucket fails loudly
- **WHEN** the bucket is unreachable at 04:00
- **THEN** the script exits non-zero, the failure is logged, and the agent keeps running

#### Scenario: The box cannot read its own archive
- **WHEN** someone holding the box's files tries to decrypt an archive
- **THEN** they cannot: the box holds only the recipients' public keys

### Requirement: The box keeps the newest five archives
After an upload the box SHALL delete every archive of its own name in the bucket except the newest five. A delete
the bucket refuses SHALL be logged as a warning and SHALL NOT fail the backup.

#### Scenario: The sixth archive goes
- **WHEN** an upload leaves six archives of the box in the bucket
- **THEN** the oldest is deleted and five remain

#### Scenario: Another box's archives stay
- **WHEN** the bucket also holds the archives of a box whose name starts with this one's, `example-two` beside `example`
- **THEN** `example`'s backup deletes none of them, and its restore, drill and status never pick one

#### Scenario: A locked archive stays
- **WHEN** the oldest archive past the newest five is younger than the bucket's lock
- **THEN** the delete is refused, a warning is logged, and the backup exits zero

### Requirement: The restore drill proves an archive
`restore-drill` SHALL fetch the newest archive, decrypt it on the machine running it, import it with the manifest's
`restore` command into a scratch volume on the box, and check that `state.db` passes `PRAGMA integrity_check`, has a
`sessions` table, and that `config.yaml` exists. It SHALL print the session count, SHALL NOT touch the service or the
live volume, and SHALL remove the scratch volume and every decrypted copy at the end.

#### Scenario: A clean drill
- **WHEN** `restore-drill` runs after a backup
- **THEN** it prints the archive's name and the session count, and exits zero

#### Scenario: An unreachable box leaves no decrypted copy
- **WHEN** `restore-drill` runs while the box is off the network, or the box drops during the copy of the zip
- **THEN** it fails before decrypting, or removes the decrypted archive from the machine running it

#### Scenario: A broken archive fails the drill
- **WHEN** the newest archive's `state.db` fails its integrity check
- **THEN** the drill exits non-zero, naming the check

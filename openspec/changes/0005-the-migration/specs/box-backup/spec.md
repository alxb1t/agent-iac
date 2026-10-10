## MODIFIED Requirements

### Requirement: Restore is one step
`restore` SHALL fetch the newest archive (or a named one), decrypt it on the machine running it, stop the service,
import it into the state volume with the manifest's `restore` command, and start the service. When `box.yaml` sets
`kb`, it SHALL then replace `kb` under the blueprint mount with a fresh clone. No other step SHALL be needed for the
agent to resume with its previous state. The decrypted archive SHALL be removed from both machines at the end. It
SHALL print the archive's name before the download, and SHALL stop when the newest archive is dated after the time
of the machine running it, unless the archive is named. Given `box_archive_file`, an absolute path on the machine
running it, `restore` SHALL take that file instead of the bucket: a `.zip.age` decrypted, a `.zip` copied as is,
anything else refused; the file itself SHALL NOT be moved or deleted; and after the import it SHALL remove `.env`
from the blueprint mount.

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

#### Scenario: A hand-installed Hermes migrates
- **WHEN** `restore` runs with `box_archive_file` naming a `hermes backup` zip from a hand-installed Hermes
- **THEN** the agent starts with that Hermes's sessions and memories, `/opt/data/.env` holds none of its values, and
  the zip is still where it was

#### Scenario: A local archive needs no bucket
- **WHEN** `restore` runs with `box_archive_file` naming a `.zip`
- **THEN** nothing is listed or downloaded from the bucket, and no age identity is needed

#### Scenario: An unknown file is refused
- **WHEN** `box_archive_file` names `migrate.tar`, or `box_archive` is given too
- **THEN** `restore` stops before touching the box, naming the problem

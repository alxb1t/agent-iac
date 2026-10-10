## MODIFIED Requirements

### Requirement: The bootstrap script joins the tailnet and admits the operator
`bootstrap-pi.sh` SHALL take the operator's SSH public key as its one argument, read the Tailscale auth key from the
terminal without echoing it, run as root, and leave the Pi with `python3` and `tailscale` installed, the
`tailscaled` service enabled and up, the node joined with the given key, and the operator's key in root's
`authorized_keys`. The auth key SHALL NOT appear on any command line. The Tailscale signing key SHALL be checked
against its pinned hash before apt can trust it. It SHALL be safe to run twice.

#### Scenario: A fresh Pi
- **WHEN** the script runs on a Pi freshly flashed with Raspberry Pi OS Lite, with network
- **THEN** the Pi appears on the tailnet and the operator can `ssh root@<tailnet name>`

#### Scenario: A second run
- **WHEN** the script runs again on the same Pi
- **THEN** it changes nothing and exits zero

#### Scenario: Missing arguments
- **WHEN** the script is run without the SSH public key
- **THEN** it prints usage and exits non-zero before changing anything

#### Scenario: Not root
- **WHEN** the script is run by a user other than root
- **THEN** it says to run it with `sudo` and exits non-zero before changing anything

#### Scenario: A bad keyring download
- **WHEN** the download of Tailscale's signing key is cut short or does not match the pinned hash
- **THEN** nothing is written where apt reads keyrings, and the script exits non-zero

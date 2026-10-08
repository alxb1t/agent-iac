## Purpose

The one hand-run step between "a Pi was flashed with Imager" and "a host exists on the tailnet": a script whoever
holds the Pi runs once from their own machine on the Pi's LAN.

## ADDED Requirements

### Requirement: The bootstrap script joins the tailnet and admits the operator
`bootstrap-pi.sh` SHALL take a Tailscale auth key and the operator's SSH public key as arguments, run as root, and
leave the Pi with `python3` and `tailscale` installed, the `tailscaled` service enabled and up, the node joined with
the given key, and the operator's key in root's `authorized_keys`. It SHALL be safe to run twice.

#### Scenario: A fresh Pi
- **WHEN** the script runs on a Pi freshly flashed with Raspberry Pi OS Lite, with network
- **THEN** the Pi appears on the tailnet and the operator can `ssh root@<tailnet name>`

#### Scenario: A second run
- **WHEN** the script runs again on the same Pi
- **THEN** it changes nothing and exits zero

#### Scenario: Missing arguments
- **WHEN** the script is run without both arguments
- **THEN** it prints usage and exits non-zero before changing anything

#### Scenario: Not root
- **WHEN** the script is run by a user other than root
- **THEN** it says to run it with `sudo` and exits non-zero before changing anything

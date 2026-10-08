#!/bin/sh
# Join a freshly flashed Raspberry Pi OS host to the tailnet and admit the operator's key as root.
# Run once on the Pi; a second run changes nothing. The checklist around it: docs/host.md.
set -eu

usage='usage: sudo sh bootstrap-pi.sh <tailscale auth key> "<operator ssh public key>"'
if [ $# -ne 2 ] || [ -z "$1" ] || [ -z "$2" ]; then
  echo "$usage" >&2
  exit 1
fi
if [ "$(id -u)" -ne 0 ]; then
  echo "run it as root, with sudo: $usage" >&2
  exit 1
fi
key=$1
pubkey=$2

# Ansible needs python3 on the host.
if ! command -v python3 >/dev/null 2>&1; then
  apt-get update
  apt-get install -y python3
fi

# Tailscale from its apt repository, behind its signing key pinned by hash
# (fingerprint 2596 A99E AAB3 3821 893C  0A79 458C A832 957F 5868); apt checks every package against it.
if ! command -v tailscale >/dev/null 2>&1; then
  codename=$(. /etc/os-release && echo "$VERSION_CODENAME")
  keyring=/usr/share/keyrings/tailscale-archive-keyring.gpg
  curl -fsSL -o "$keyring" "https://pkgs.tailscale.com/stable/debian/$codename.noarmor.gpg"
  if ! echo "3e03dacf222698c60b8e2f990b809ca1b3e104de127767864284e6c228f1fb39  $keyring" | sha256sum -c - >/dev/null; then
    rm -f "$keyring"
    echo "Tailscale's signing key is not the pinned one; stopping" >&2
    exit 1
  fi
  echo "deb [signed-by=$keyring] https://pkgs.tailscale.com/stable/debian $codename main" >/etc/apt/sources.list.d/tailscale.list
  apt-get update
  apt-get install -y tailscale
fi
systemctl enable --now tailscaled

if ! tailscale status --json 2>/dev/null | grep -q '"BackendState": *"Running"'; then
  # The key reaches tailscale in a root-only file, not on its command line.
  keyfile=$(mktemp)
  trap 'rm -f "$keyfile"' EXIT
  printf '%s' "$key" >"$keyfile"
  tailscale up --auth-key="file:$keyfile"
fi

mkdir -p /root/.ssh
chmod 700 /root/.ssh
touch /root/.ssh/authorized_keys
chmod 600 /root/.ssh/authorized_keys
grep -qxF "$pubkey" /root/.ssh/authorized_keys || printf '%s\n' "$pubkey" >> /root/.ssh/authorized_keys

echo "joined the tailnet as $(hostname); the operator can now ssh root@$(hostname)"

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
authkey=$1
pubkey=$2

# Ansible needs python3 on the host.
if ! command -v python3 >/dev/null 2>&1; then
  apt-get update
  apt-get install -y python3
fi

if ! command -v tailscale >/dev/null 2>&1; then
  curl -fsSL https://tailscale.com/install.sh | sh
fi
systemctl enable --now tailscaled

if ! tailscale status --json 2>/dev/null | grep -q '"BackendState": *"Running"'; then
  tailscale up --authkey "$authkey"
fi

mkdir -p /root/.ssh
chmod 700 /root/.ssh
touch /root/.ssh/authorized_keys
chmod 600 /root/.ssh/authorized_keys
grep -qxF "$pubkey" /root/.ssh/authorized_keys || printf '%s\n' "$pubkey" >> /root/.ssh/authorized_keys

echo "joined the tailnet as $(hostname); the operator can now ssh root@$(hostname)"

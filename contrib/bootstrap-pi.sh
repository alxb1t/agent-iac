#!/bin/sh
# Join a freshly flashed Raspberry Pi OS host to the tailnet and admit the operator's key as root.
# Run once on the Pi; a second run changes nothing. The checklist around it: docs/host.md.
set -eu

usage='usage: sudo sh bootstrap-pi.sh "<operator ssh public key>"; it asks for the Tailscale auth key'
if [ $# -ne 1 ] || [ -z "$1" ]; then
  echo "$usage" >&2
  exit 1
fi
if [ "$(id -u)" -ne 0 ]; then
  echo "run it as root, with sudo: $usage" >&2
  exit 1
fi
pubkey="$1"

joined() {
  command -v tailscale >/dev/null 2>&1 && tailscale status --json 2>/dev/null | grep -q '"BackendState": *"Running"'
}

# The auth key comes from the terminal, so it is on no command line. /dev/tty, not stdin:
# `curl … | sudo sh -s -- "<key>"` feeds the script itself on stdin. Why: 0004-the-handover design D12.
if ! joined; then
  if ! (: </dev/tty) 2>/dev/null; then
    echo "no terminal to read the Tailscale auth key from; run it in an SSH session" >&2
    exit 1
  fi
  printf 'Tailscale auth key: ' >/dev/tty
  trap 'stty echo </dev/tty; exit 1' INT TERM
  stty -echo </dev/tty
  IFS= read -r authkey </dev/tty || authkey=
  stty echo </dev/tty
  trap - INT TERM
  printf '\n' >/dev/tty
  if [ -z "$authkey" ]; then
    echo "no Tailscale auth key given" >&2
    exit 1
  fi
fi

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
  # A download cut short or tampered with never reaches the path apt trusts.
  download=$(mktemp)
  trap 'rm -f "$download"' EXIT
  curl -fsSL -o "$download" "https://pkgs.tailscale.com/stable/debian/$codename.noarmor.gpg"
  if ! echo "3e03dacf222698c60b8e2f990b809ca1b3e104de127767864284e6c228f1fb39  $download" | sha256sum -c - >/dev/null; then
    echo "Tailscale's signing key is not the pinned one; stopping" >&2
    exit 1
  fi
  install -m 0644 "$download" "$keyring"
  rm -f "$download"
  echo "deb [signed-by=$keyring] https://pkgs.tailscale.com/stable/debian $codename main" >/etc/apt/sources.list.d/tailscale.list
  apt-get update
  apt-get install -y tailscale
fi
systemctl enable --now tailscaled

if ! joined; then
  # The key reaches tailscale in a root-only file, not on its command line.
  keyfile=$(mktemp)
  trap 'rm -f "$keyfile"' EXIT
  printf '%s' "$authkey" >"$keyfile"
  tailscale up --auth-key="file:$keyfile"
fi

mkdir -p /root/.ssh
chmod 700 /root/.ssh
touch /root/.ssh/authorized_keys
chmod 600 /root/.ssh/authorized_keys
grep -qxF "$pubkey" /root/.ssh/authorized_keys || printf '%s\n' "$pubkey" >> /root/.ssh/authorized_keys

echo "joined the tailnet as $(hostname); the operator can now ssh root@$(hostname)"

# agent-iac — the host checklist

What whoever holds the Pi does, once, so that "a host exists": flash it, boot it, run one command. No agent-iac on
their machine. Then the operator takes over with `make apply`, per the [architecture](architecture.md).

```
 Imager ──▶ first boot ──▶ bootstrap script ──▶ on the tailnet ──▶ operator: make apply
 (holder)    (holder)        (holder, on LAN)    (operator checks)
```

## 1 — Flash with Raspberry Pi Imager

In Raspberry Pi Imager, choose the device, then **Raspberry Pi OS Lite (64-bit)**, then the SD card. In the OS
customisation settings:

| setting | value |
|---|---|
| hostname | the box's name, e.g. `example-pi` |
| username and password | the holder's own user |
| Wi-Fi | the network the Pi lives on; skip it for Ethernet |
| locale | the holder's time zone; the backup runs at 04:00 in it |
| SSH | on, **public-key authentication only**, with the operator's SSH public key |

Write the card.

## 2 — First boot

Put the card in the Pi and power it. The first boot resizes the card and joins the network; give it a few minutes.
From a machine on the same network, `ssh <user>@<hostname>.local` reaches it.

## 3 — Run the bootstrap

The operator sends the holder a Tailscale auth key (single use, pre-approved) and their SSH public key. On the Pi,
paste the auth key at the prompt of the first line, so it stays out of the shell's history:

```sh
read -rs -p 'Tailscale auth key: ' key; echo
curl -fsSL https://raw.githubusercontent.com/alxb1t/agent-iac/v0.2.0/contrib/bootstrap-pi.sh | sudo sh -s -- "$key" "<operator ssh public key>"
```

It installs `python3`, and Tailscale from Tailscale's apt repository behind its pinned signing key, joins the
tailnet with the key, and puts the operator's key in root's `authorized_keys`. Running it again changes nothing.

## 4 — The operator confirms the node

On the operator's machine:

- `tailscale status` lists the Pi by its hostname.
- `ssh root@<hostname>` logs in over the tailnet.

That tailnet name is the `target` in `box.yaml`. The host exists; the holder is done.

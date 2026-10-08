"""Every template renders with the sample vars, and each carries the lines its file must hold."""

import pytest

from conftest import TEMPLATES

# The lines each rendered file must hold: 0002-the-box design D14.
NEEDLES = {
    "nftables.conf.j2": ["policy drop", 'iifname "tailscale0" accept', "udp dport 41641 accept"],
    "cron.j2": ["0 4 * * * root /usr/local/bin/box-backup example"],
    "auto-upgrades.j2": ['APT::Periodic::Unattended-Upgrade "1";'],
    "box.container.j2": [
        "ContainerName=example",
        "Image=docker.io/nousresearch/hermes-agent:v2026.9.24",
        "Exec=gateway run",
        "AutoUpdate=none",
        "Restart=always",
    ],
    "restic.env.j2": ["RESTIC_REPOSITORY=", "RESTIC_PASSWORD="],
    "box-blueprint-sync.sh.j2": ["rsync -a --checksum --itemize-changes", "chown -R 10000:10000"],
    "box-backup.sh.j2": ["trap", "podman unshare restic backup", "systemctl --user -M box@ start example"],
}


def missing(text, needles):
    """Return the needles absent from text, e.g. ("a b", ["a", "c"]) → ["c"]."""
    return [n for n in needles if n not in text]


@pytest.mark.parametrize("name", sorted(p.name for p in TEMPLATES.iterdir()))
def test_every_template_renders(render, name):
    render(name)


@pytest.mark.parametrize("name", sorted(NEEDLES))
def test_needles(render, name):
    assert missing(render(name), NEEDLES[name]) == []


def test_needle_check_catches_a_dropped_line(render):
    text = render("nftables.conf.j2").replace('iifname "tailscale0" accept', "")
    assert missing(text, NEEDLES["nftables.conf.j2"]) == ['iifname "tailscale0" accept']


# cron ignores a last line with no newline.
def test_cron_line_ends_with_a_newline(render):
    assert render("cron.j2").endswith("\n")


def test_env_file_holds_the_manifest_env_and_nothing_else(render, sample_vars):
    secrets = sample_vars["box_secrets"]
    expected = [f"{n}={secrets[n]}" for n in sample_vars["manifest"]["env"]]
    assert render("env.j2").splitlines() == expected


def test_env_file_check_catches_a_host_secret(render, sample_vars):
    manifest = {**sample_vars["manifest"], "env": sample_vars["manifest"]["env"] + ["TAILSCALE_AUTH_KEY"]}
    expected = [f"{n}={sample_vars['box_secrets'][n]}" for n in sample_vars["manifest"]["env"]]
    assert render("env.j2", manifest=manifest).splitlines() != expected


def test_restic_env_quotes_a_password_for_the_shell(render, sample_vars):
    secrets = {**sample_vars["box_secrets"], "RESTIC_PASSWORD": "a b'c"}
    assert "RESTIC_PASSWORD='a b'\"'\"'c'" in render("restic.env.j2", box_secrets=secrets)


def test_quadlet_publishes_no_port(render):
    assert "PublishPort" not in render("box.container.j2")


def test_quadlet_check_catches_a_published_port(render):
    text = render("box.container.j2").replace("[Service]", "PublishPort=8080:8080\n[Service]")
    assert "PublishPort" in text


def test_backup_starts_the_box_on_every_exit(render):
    text = render("box-backup.sh.j2")
    trap = next(line for line in text.splitlines() if line.startswith("trap "))
    assert "start example" in trap and trap.endswith(" EXIT")
    assert text.index("trap ") < text.index("stop example")

"""Every template renders with the sample vars, and each carries the lines its file must hold."""

import pytest

from conftest import TEMPLATES

# The lines each rendered file must hold: 0002-the-box design D14.
NEEDLES = {
    "nftables.conf.j2": ["policy drop", 'iifname "tailscale0" accept', "udp dport 41641 accept"],
    "cron.j2": ["0 4 * * * root /usr/local/bin/box-backup example"],
    "auto-upgrades.j2": ['APT::Periodic::Unattended-Upgrade "1";'],
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

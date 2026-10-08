"""Every template renders with the sample vars, and each carries the lines its file must hold."""

import shlex
import subprocess

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
        "EnvironmentFile=/home/box/.config/agent-iac/example.env",
        "Exec=gateway run",
        "AutoUpdate=none",
        "Restart=always",
    ],
    "restic.env.j2": ["RESTIC_REPOSITORY=", "RESTIC_PASSWORD="],
    "box-blueprint-sync.sh.j2": ["rsync -a --omit-dir-times --checksum --itemize-changes", "chown -R 10000:10000"],
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


def test_restic_env_quotes_a_password_for_the_shell(render, sample_vars):
    secrets = {**sample_vars["box_secrets"], "RESTIC_PASSWORD": "a b'c"}
    assert "RESTIC_PASSWORD='a b'\"'\"'c'" in render("restic.env.j2", box_secrets=secrets)


def test_quadlet_publishes_no_port(render):
    assert "PublishPort" not in render("box.container.j2")


# A source ending in "/" carries its own mode and time onto the volume root, which the agent writes into.
def test_blueprint_sync_names_the_entries_not_the_staging_root(render):
    line = next(line for line in render("box-blueprint-sync.sh.j2").splitlines() if "rsync " in line)
    words = shlex.split(line[line.index("rsync ") : line.rindex(")")])
    sources = [w for w in words[1:] if not w.startswith("-")][:-1]
    assert sources and not [s for s in sources if s.endswith("/")]


def test_backup_starts_the_box_on_every_exit(render):
    text = render("box-backup.sh.j2")
    trap = next(line for line in text.splitlines() if line.startswith("trap "))
    assert "start example" in trap and trap.endswith(" EXIT")
    assert text.index("trap ") < text.index("stop example")


def stub(bin_dir, name, body=""):
    """Write an executable shell stub, e.g. stub(d, "su") → a `su` that does nothing and exits 0."""
    path = bin_dir / name
    path.write_text(f"#!/bin/sh\n{body}\nexit 0\n")
    path.chmod(0o755)


def run_backup(render, tmp_path, systemctl):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    stub(bin_dir, "systemctl", systemctl)
    stub(bin_dir, "su")
    stub(bin_dir, "logger")
    script = tmp_path / "box-backup"
    script.write_text(render("box-backup.sh.j2"))
    env = {"PATH": f"{bin_dir}:/usr/bin:/bin"}
    return subprocess.run(["sh", str(script), "example"], env=env, capture_output=True, check=False)


def test_backup_exits_zero_when_every_step_succeeds(render, tmp_path):
    assert run_backup(render, tmp_path, "").returncode == 0


# A backup that leaves the agent stopped must not read as a success to the playbook or cron.
def test_backup_fails_when_the_start_fails(render, tmp_path):
    assert run_backup(render, tmp_path, 'case "$*" in *" start "*) exit 1;; esac').returncode != 0


# Tailscale keeps its own chains in other tables; the ruleset replaces only the table it owns.
def test_ruleset_replaces_only_its_own_table(render):
    lines = [line.strip() for line in render("nftables.conf.j2").splitlines()]
    assert "flush ruleset" not in lines
    assert lines.index("table inet filter") < lines.index("delete table inet filter") < lines.index("table inet filter {")


# rsync reads a bare name with a colon in it as host:path; a name starting with "./" is always local.
def test_blueprint_sync_hands_rsync_local_names(render, tmp_path):
    bin_dir, data = tmp_path / "bin", tmp_path / "data"
    staging = tmp_path / "config" / "example" / "blueprint"
    for d in (bin_dir, data, staging):
        d.mkdir(parents=True)
    (staging / "notes:2026.md").write_text("x")
    stub(bin_dir, "podman", 'case "$1" in volume) echo "$DATA";; unshare) shift; exec "$@";; esac')
    stub(bin_dir, "rsync", 'printf "%s\\n" "$@" > "$ARGS"; echo ">f+++++++++ notes:2026.md"')
    stub(bin_dir, "chown")
    script = tmp_path / "box-blueprint-sync"
    script.write_text(render("box-blueprint-sync.sh.j2", box_config=str(tmp_path / "config")))
    args = tmp_path / "args"
    env = {"PATH": f"{bin_dir}:/usr/bin:/bin", "DATA": str(data), "ARGS": str(args)}
    subprocess.run(["sh", str(script)], env=env, check=True)
    assert "./notes:2026.md" in args.read_text().splitlines()

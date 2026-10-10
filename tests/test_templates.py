"""Every template renders with the sample vars, and each carries the lines its file must hold."""

import re
import shlex
import subprocess

import pytest

from conftest import ARCHIVES, OTHER_BOX_ARCHIVES, ROOT, TEMPLATES

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
        'Environment="HERMES_DASHBOARD=1"',
        'Environment="GIT_HOOK_ROOTS=/opt/data/kb"',
        "PublishPort=100.64.0.1:9119:9119",
    ],
    "rclone.env.j2": [
        "RCLONE_CONFIG_R2_TYPE=s3",
        "RCLONE_CONFIG_R2_PROVIDER=Cloudflare",
        "RCLONE_CONFIG_R2_ACCESS_KEY_ID=example-r2-access-key-id",
        "RCLONE_CONFIG_R2_SECRET_ACCESS_KEY=example-r2-secret-access-key",
        "RCLONE_CONFIG_R2_ENDPOINT=https://0123456789abcdef0123456789abcdef.r2.cloudflarestorage.com",
        "RCLONE_CONFIG_R2_NO_CHECK_BUCKET=true",
    ],
    "box-blueprint-sync.sh.j2": ["rsync -a --omit-dir-times --checksum --itemize-changes", "chown -R 10000:10000"],
    "box-backup.sh.j2": [
        "set -euo pipefail",
        "podman exec --user 10000 example hermes backup -o /opt/data/backups/agent-iac.zip",
        "age -R /home/box/.config/agent-iac/example.recipients",
        "rclone rcat",
    ],
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


def test_rclone_env_quotes_a_secret_for_the_shell(render, sample_vars):
    secrets = {**sample_vars["box_secrets"], "R2_SECRET_ACCESS_KEY": "a b'c"}
    assert "R2_SECRET_ACCESS_KEY='a b'\"'\"'c'" in render("rclone.env.j2", box_secrets=secrets)


def off_tailnet_ports(text, ip):
    """Return the PublishPort= lines not bound to ip, e.g. "PublishPort=9119:9119" → that line."""
    lines = [line for line in text.splitlines() if line.startswith("PublishPort=")]
    return [line for line in lines if not line.startswith(f"PublishPort={ip}:")]


def test_quadlet_publishes_only_on_the_tailnet_address(render, sample_vars):
    text = render("box.container.j2")
    assert "PublishPort=" in text
    assert off_tailnet_ports(text, sample_vars["box_tailnet_ip"]) == []


def test_tailnet_check_catches_a_port_on_every_address(render, sample_vars):
    text = render("box.container.j2") + "PublishPort=9119:9119\n"
    assert off_tailnet_ports(text, sample_vars["box_tailnet_ip"]) == ["PublishPort=9119:9119"]


KB = "git@github.com:example/example-kb.git"
KB_LINES = [
    "Secret=example-kb-deploy-key,type=mount,target=/run/secrets/kb_deploy_key,uid=10000,gid=10000,mode=0400",
    "StrictHostKeyChecking=yes",
    "UserKnownHostsFile=/opt/data/.ssh/kb_known_hosts",
    'Environment="GIT_AUTHOR_EMAIL=example@box.invalid"',
    'Environment="GIT_COMMITTER_EMAIL=example@box.invalid"',
]


def test_quadlet_with_kb_mounts_the_key_and_names_the_box(render, sample_vars):
    text = render("box.container.j2", box={**sample_vars["box"], "kb": KB})
    assert missing(text, KB_LINES) == []
    assert "KB_DEPLOY_KEY" not in text


def test_quadlet_without_kb_has_no_kb_line(render):
    text = render("box.container.j2")
    assert missing(text, KB_LINES) == KB_LINES
    assert "GIT_SSH_COMMAND" not in text


def github_ssh_options(text):
    """Return the options under `Host github.com`, names lowercased, e.g. "IdentitiesOnly yes" → {"identitiesonly": "yes"}."""
    options, host = {}, None
    for line in text.splitlines():
        words = line.split("#", 1)[0].replace("=", " ").split()
        if len(words) == 2 and words[0].lower() == "host":
            host = words[1]
        elif len(words) == 2 and host == "github.com":
            options[words[0].lower()] = words[1]
    return options


# git-hook runs ssh with its own GIT_SSH_COMMAND, so the key and the pin sit where every ssh of the agent's user
# reads them: the agent's ~/.ssh/config, its home being the blueprint mount. Why: 0003-the-knowledge-base design D5.
def test_the_agents_ssh_config_pins_github_to_the_quadlets_key(render, sample_vars):
    mount = sample_vars["manifest"]["blueprint_mount"]
    quadlet = render("box.container.j2", box={**sample_vars["box"], "kb": KB})
    key = re.search(r"^Secret=[^,]+,type=mount,target=([^,]+),", quadlet, re.M)[1]
    known_hosts = re.search(r"UserKnownHostsFile=(\S+)\"$", quadlet, re.M)[1]
    ssh = ROOT / "blueprints" / "base" / ".ssh"
    assert github_ssh_options((ssh / "config").read_text()) == {
        "identityfile": key,
        "identitiesonly": "yes",
        "stricthostkeychecking": "yes",
        "userknownhostsfile": known_hosts,
        "globalknownhostsfile": "/dev/null",
    }
    assert known_hosts == f"{mount}/.ssh/kb_known_hosts" and (ssh / "kb_known_hosts").is_file()


def test_ssh_options_read_only_the_github_host():
    text = "Host example\n  IdentityFile /a\nHost github.com\n  # a note\n  StrictHostKeyChecking=yes\n"
    assert github_ssh_options(text) == {"stricthostkeychecking": "yes"}


# A source ending in "/" carries its own mode and time onto the volume root, which the agent writes into.
def test_blueprint_sync_names_the_entries_not_the_staging_root(render):
    line = next(line for line in render("box-blueprint-sync.sh.j2").splitlines() if "rsync " in line)
    words = shlex.split(line[line.index("rsync ") : line.rindex(")")])
    sources = [w for w in words[1:] if not w.startswith("-")][:-1]
    assert sources and not [s for s in sources if s.endswith("/")]


def stub(bin_dir, name, body=""):
    """Write an executable shell stub, e.g. stub(d, "su") → a `su` that does nothing and exits 0."""
    path = bin_dir / name
    path.write_text(f"#!/bin/sh\n{body}\nexit 0\n")
    path.chmod(0o755)


# The stubs log each call to $LOG; the container's /opt/data is $DATA.
BACKUP_STUBS = {
    "su": 'while [ "$1" != -c ]; do shift; done; exec /bin/bash -c "$2"',
    "podman": """echo "podman $*" >> "$LOG"
case "$1" in
  volume) echo "$DATA";;
  unshare) shift; exec "$@";;
  exec) case "$*" in
    *" rm -f "*) rm -f "$DATA/backups/agent-iac.zip";;
    *) mkdir -p "$DATA/backups"; echo zip > "$DATA/backups/agent-iac.zip";;
  esac;;
esac""",
    "age": "exec cat",
    "rclone": """echo "rclone $*" >> "$LOG"
case "$1" in
  rcat) cat > "$UPLOAD"; exit "$RCAT_RC";;
  lsf) while [ "$1" != --include ]; do shift; done
    for f in $LISTING; do case $f in $2) echo "$f";; esac; done;;
  deletefile) exit "$DELETE_RC";;
esac""",
    "logger": 'echo "logger $*" >> "$LOG"',
}


def run_backup(render, tmp_path, rcat_rc=0, delete_rc=0, edit=lambda text: text, listing=ARCHIVES, rclone_env=True):
    """Run box-backup against the stubs; return its exit code, the calls logged and the volume's zip path."""
    bin_dir, data = tmp_path / "bin", tmp_path / "data"
    bin_dir.mkdir()
    data.mkdir()
    for name, body in BACKUP_STUBS.items():
        stub(bin_dir, name, body)
    env_file, log, upload = tmp_path / "example.rclone.env", tmp_path / "log", tmp_path / "upload"
    if rclone_env:
        env_file.write_text("")
    log.write_text("")
    script = tmp_path / "box-backup"
    script.write_text(edit(render("box-backup.sh.j2", box_rclone_env=str(env_file))))
    env = {
        "PATH": f"{bin_dir}:/usr/bin:/bin",
        "LOG": str(log),
        "DATA": str(data),
        "UPLOAD": str(upload),
        "LISTING": " ".join(listing),
        "RCAT_RC": str(rcat_rc),
        "DELETE_RC": str(delete_rc),
    }
    code = subprocess.run(["bash", str(script), "example"], env=env, capture_output=True, check=False).returncode
    return code, log.read_text().splitlines(), data / "backups" / "agent-iac.zip"


def calls(log, prefix):
    """Return the logged calls starting with prefix, e.g. "rclone deletefile" → each delete's line."""
    return [line for line in log if line.startswith(prefix)]


def test_backup_uploads_the_encrypted_archive_and_keeps_five(render, tmp_path):
    code, log, zip_path = run_backup(render, tmp_path)
    assert code == 0
    assert (tmp_path / "upload").read_text() == "zip\n"
    [rcat] = calls(log, "rclone rcat ")
    assert re.fullmatch(r"rclone rcat r2:example-backups/example-\d{8}T\d{6}Z\.zip\.age", rcat)
    glob = "example-" + "[0-9]" * 8 + "T" + "[0-9]" * 6 + "Z.zip.age"
    assert calls(log, "rclone lsf ") == [f"rclone lsf --files-only --include {glob} r2:example-backups"]
    assert sorted(calls(log, "rclone deletefile ")) == [
        "rclone deletefile r2:example-backups/example-20261001T040000Z.zip.age",
        "rclone deletefile r2:example-backups/example-20261002T040000Z.zip.age",
    ]
    assert calls(log, "logger ") == []
    assert not zip_path.exists()


# The bucket may hold the archives of a box whose name starts with this one's: 0004-the-handover review R1.
def test_keep_five_leaves_another_boxs_archives(render, tmp_path):
    code, log, _ = run_backup(render, tmp_path, listing=OTHER_BOX_ARCHIVES + ARCHIVES)
    assert code == 0
    assert sorted(calls(log, "rclone deletefile ")) == [
        "rclone deletefile r2:example-backups/example-20261001T040000Z.zip.age",
        "rclone deletefile r2:example-backups/example-20261002T040000Z.zip.age",
    ]


# A locked archive is the lock working, not a failed backup.
def test_a_refused_delete_warns_and_exits_zero(render, tmp_path):
    code, log, _ = run_backup(render, tmp_path, delete_rc=1)
    assert code == 0
    assert len(calls(log, "logger -p user.warning ")) == 2
    assert calls(log, "logger -p user.err ") == []


def test_a_failed_upload_fails_logs_and_removes_the_zip(render, tmp_path):
    code, log, zip_path = run_backup(render, tmp_path, rcat_rc=1)
    assert code != 0
    assert len(calls(log, "logger -p user.err ")) == 1
    assert calls(log, "rclone deletefile ") == []
    assert not zip_path.exists()


# An env file removed or no longer readable by hand still leaves its line in the log: 0004-the-handover review R9.
def test_a_missing_rclone_env_fails_and_logs(render, tmp_path):
    code, log, _ = run_backup(render, tmp_path, rclone_env=False)
    assert code != 0
    [err] = calls(log, "logger -p user.err ")
    assert "no rclone env" in err
    assert calls(log, "podman ") == [] and calls(log, "rclone ") == []


def test_zip_check_catches_a_dropped_trap(render, tmp_path):
    def drop_trap(text):
        return "\n".join(line for line in text.splitlines() if not line.startswith("trap "))

    _, _, zip_path = run_backup(render, tmp_path, rcat_rc=1, edit=drop_trap)
    assert zip_path.exists()


# hermes backup copies the database safely while the gateway runs: 0004-the-handover design D5.
def test_backup_never_stops_the_service(render):
    assert "systemctl" not in render("box-backup.sh.j2")


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

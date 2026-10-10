"""The playbooks and the role's tasks, read as YAML: the commands that can lose state or wedge an apply."""

import fnmatch
import json
import os
import shlex
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest
import yaml

from conftest import ARCHIVES, OTHER_BOX_ARCHIVES, ROOT, jinja_env


def plays(path):
    return yaml.safe_load((ROOT / path).read_text())


def walk(items):
    """Yield every item and the tasks under it, blocks flattened, e.g. a block's `always` tasks too."""
    for item in items or []:
        yield item
        for key in ("tasks", "block", "rescue", "always"):
            yield from walk(item.get(key))


def tasks(path):
    """Yield every task in a playbook or a task file."""
    yield from walk(plays(path))


def task(path, name):
    return next(t for t in tasks(path) if t.get("name") == name)


def argv(t):
    return t["ansible.builtin.command"]["argv"]


def names(items):
    return [t.get("name") for t in items]


RESTORE_BLOCK = "Restore with the service stopped"


# A stopped service holds no database, and a failed import still leaves the agent up: 0004-the-handover design D8.
def test_restore_stops_before_the_import_and_starts_in_always():
    block = task("playbooks/restore.yml", RESTORE_BLOCK)
    steps = names(block["block"])
    assert steps.index("Hand the zip to the box") < steps.index("Stop the box") < steps.index("Import the archive")
    assert {"Start the box", "Remove the zip from the box"} <= set(names(block["always"]))


def import_words(path, sample_vars):
    """Return the import command of a playbook, rendered with the sample vars and split as `command` splits it."""
    env = jinja_env()
    play_vars = plays(path)[-1]["vars"]
    values = {**sample_vars, "box_zip": "/z/restore.zip", "box_in_container": play_vars["box_in_container"]}
    return shlex.split(env.from_string(task(path, "Import the archive")["ansible.builtin.command"]["cmd"]).render(values))


def expected_import(volume):
    return [
        *("podman", "run", "--rm", "--user", "10000", "--entrypoint", "hermes"),
        *("-v", f"{volume}:/opt/data", "-v", "/z/restore.zip:/tmp/agent-iac-restore.zip:ro"),
        *("docker.io/nousresearch/hermes-agent:v2026.9.24", "import", "--force", "/tmp/agent-iac-restore.zip"),
    ]


def test_restore_imports_in_a_one_off_container_as_the_agent(sample_vars):
    assert import_words("playbooks/restore.yml", sample_vars) == expected_import("example-data")


def test_the_drill_imports_into_its_scratch_volume_only(sample_vars):
    assert import_words("playbooks/restore_drill.yml", sample_vars) == expected_import("example-drill")


# The archive's kb/ has no .git; the clone after it brings the KB back with its history.
def test_restore_replaces_the_kb_only_with_kb():
    rm = task("playbooks/restore.yml", "Remove the archive's KB")
    assert rm["when"] == "box.kb is defined"
    assert argv(rm)[:4] == ["podman", "unshare", "rm", "-rf"] and argv(rm)[4].endswith("/kb")
    steps = plays("playbooks/restore.yml")[-1]["tasks"]
    clone = next(t for t in steps if t.get("ansible.builtin.include_role", {}).get("tasks_from") == "kb.yml")
    assert names(steps).index(RESTORE_BLOCK) < steps.index(clone)


# An imported .env would shadow the sops secrets; a box's own .env holds keys `hermes auth add` wrote.
# Why: 0005-the-migration design D2.
def test_restore_drops_the_env_of_a_local_import_only():
    steps = names(task("playbooks/restore.yml", RESTORE_BLOCK)["block"])
    rm = task("playbooks/restore.yml", "Remove the old install's env")
    read = task("playbooks/restore.yml", "Read the volume's path")
    assert rm["when"] == "box_archive_file is defined"
    assert argv(rm) == ["podman", "unshare", "rm", "-f", "{{ box_volume.stdout }}/.env"]
    assert steps.index("Import the archive") < steps.index("Read the volume's path") < steps.index(rm["name"])
    assert read["when"] == "box.kb is defined or box_archive_file is defined"


EXAMPLE = ROOT / "examples" / "box"


# `make restore -e …` hands -e to make, not Ansible; abspath makes a relative ZIP safe: 0005-the-migration design D3.
def test_make_migrate_restores_the_zip_by_its_absolute_path():
    done = subprocess.run(["make", "-n", "-C", EXAMPLE, "migrate", "ZIP=migrate.zip"], capture_output=True, text=True)
    assert done.returncode == 0, done.stderr
    assert f"-e box_archive_file={EXAMPLE / 'migrate.zip'}" in done.stdout
    assert "alxb1t.agent_iac.restore" in done.stdout


def test_make_migrate_without_a_zip_says_how():
    done = subprocess.run(["make", "-n", "-C", EXAMPLE, "migrate"], capture_output=True, text=True)
    assert done.returncode != 0
    assert "usage: make migrate ZIP=<path to the zip>" in done.stderr


FETCH = "roles/box/tasks/fetch.yml"


def runs_age_decrypt(t):
    return "'age', '-d'" in str(t.get("ansible.builtin.command", ""))


def decrypting_hosts(play_list):
    """Return the hosts of the plays that run `age -d` or include fetch.yml, e.g. a box play decrypting → {"box"}."""
    def decrypts(t):
        return runs_age_decrypt(t) or t.get("ansible.builtin.include_role", {}).get("tasks_from") == "fetch.yml"

    return {p["hosts"] for p in play_list if any(decrypts(t) for t in walk(p.get("tasks")))}


# The box holds public keys only, so the private key never leaves the machine running make: design D7.
def test_archives_are_decrypted_only_on_the_operators_machine():
    assert any(runs_age_decrypt(t) for t in tasks(FETCH))
    for path in ("playbooks/restore.yml", "playbooks/restore_drill.yml"):
        assert decrypting_hosts(plays(path)) == {"localhost"}


def test_decrypt_check_catches_a_decrypt_on_the_box():
    play = {"hosts": "box", "tasks": [{"ansible.builtin.command": {"argv": ["age", "-d", "x"]}}]}
    assert decrypting_hosts([play]) == {"box"}
    play = {"hosts": "box", "tasks": [{"ansible.builtin.include_role": {"tasks_from": "fetch.yml"}}]}
    assert decrypting_hosts([play]) == {"box"}


# Restore, the drill and status take the newest name rclone lists: never another box's: 0004-the-handover review R1.
def test_restore_drill_and_status_list_only_this_boxs_archives(sample_vars):
    listing = OTHER_BOX_ARCHIVES + ARCHIVES
    listed = [name for name in listing if fnmatch.fnmatchcase(name, sample_vars["box_archives_glob"])]
    assert sorted(listed) == sorted(ARCHIVES)
    assert sorted(listed)[-1] == "example-20261007T040000Z.zip.age"
    assert "{{ box_archives_glob }}" in argv(task(FETCH, "List the archives"))
    assert "--include '{{ box_archives_glob }}'" in argv(task("playbooks/status.yml", "List the archives"))[-1]


# rclone lists $LISTING and downloads a stand-in; age, like age, needs its identity file. Each logs to $LOG.
FETCH_STUBS = {
    "rclone": """echo "rclone $*" >> "$LOG"
case "$1" in
  lsf) for f in $LISTING; do echo "$f"; done;;
  copyto) echo archive > "$3";;
esac""",
    # age -d -i <identity> -o <out> <in>
    "age": """echo "age $*" >> "$LOG"
[ -f "$3" ] || { echo "age: no identity file $3" >&2; exit 1; }
cp "$6" "$5"
""",
}


@pytest.fixture
def short_tmp():
    """A temp folder with a short path: ansible-playbook's RPC socket lives in TMPDIR, and a socket path is short."""
    path = Path(tempfile.mkdtemp(prefix="aiac-", dir="/tmp"))
    yield path
    shutil.rmtree(path)


def run_fetch(sample_vars, tmp_path, short_tmp, listing=ARCHIVES, identity=True, extra_vars=None):
    """Run fetch.yml on this machine against the stubs; return ansible-playbook's exit code, its output, the calls."""
    bin_dir, home, log = tmp_path / "bin", tmp_path / "home", tmp_path / "log"
    for d in (bin_dir, home):
        d.mkdir()
    for name, body in FETCH_STUBS.items():
        (bin_dir / name).write_text(f"#!/bin/sh\n{body}\n")
        (bin_dir / name).chmod(0o755)
    log.write_text("")
    (tmp_path / "vars.json").write_text(json.dumps({**sample_vars, **(extra_vars or {})}))
    play = [{"hosts": "localhost", "gather_facts": False, "tasks": [{"ansible.builtin.import_tasks": str(ROOT / FETCH)}]}]
    (tmp_path / "fetch.yml").write_text(yaml.safe_dump(play))
    env = {k: v for k, v in os.environ.items() if k != "SOPS_AGE_KEY_FILE"}
    env.update(PATH=f"{bin_dir}:{env['PATH']}", HOME=str(home), TMPDIR=str(short_tmp), LOG=str(log))
    env.update(LISTING=" ".join(listing), ANSIBLE_NOCOLOR="1", ANSIBLE_NOCOWS="1")
    if identity:
        (tmp_path / "key.txt").write_text("AGE-SECRET-KEY-EXAMPLE\n")
        env["SOPS_AGE_KEY_FILE"] = str(tmp_path / "key.txt")
    playbook = Path(sys.executable).parent / "ansible-playbook"
    argv = [playbook, "-i", "localhost,", "-c", "local", "-e", f"ansible_python_interpreter={sys.executable}"]
    argv += ["-e", f"@{tmp_path / 'vars.json'}", tmp_path / "fetch.yml"]
    done = subprocess.run(argv, env=env, capture_output=True, text=True, check=False)
    return done.returncode, done.stdout + done.stderr, log.read_text().splitlines()


def test_fetch_names_and_decrypts_the_newest_archive(sample_vars, tmp_path, short_tmp):
    code, out, log = run_fetch(sample_vars, tmp_path, short_tmp)
    assert code == 0, out
    assert "archive: example-20261007T040000Z.zip.age" in out
    [age] = [line for line in log if line.startswith("age ")]
    assert age.endswith("/example-20261007T040000Z.zip.age")


# No SOPS_AGE_KEY_FILE and no key where sops looks: the run says so, not "decrypt failed": 0004-the-handover review R3.
def test_fetch_without_an_age_identity_stops_before_the_download(sample_vars, tmp_path, short_tmp):
    code, out, log = run_fetch(sample_vars, tmp_path, short_tmp, identity=False)
    assert code != 0
    assert "Stop without an age identity failed; the box was not touched" in out
    assert log == []


# A compromised box can upload a name that sorts after every nightly one: 0004-the-handover security S3.
def test_fetch_refuses_an_archive_dated_in_the_future(sample_vars, tmp_path, short_tmp):
    code, out, log = run_fetch(sample_vars, tmp_path, short_tmp, listing=[*ARCHIVES, "example-99991231T000000Z.zip.age"])
    assert code != 0
    assert "example-99991231T000000Z.zip.age is dated in the future" in out
    assert [line for line in log if not line.startswith("rclone lsf ")] == []


# A hand-installed Hermes's zip is copied as is: no bucket, no identity, and the file stays where it was.
def test_fetch_copies_a_local_zip_and_leaves_it(sample_vars, tmp_path, short_tmp):
    zip_file = tmp_path / "migrate.zip"
    zip_file.write_bytes(b"example zip")
    extra = {"box_archive_file": str(zip_file)}
    code, out, log = run_fetch(sample_vars, tmp_path, short_tmp, identity=False, extra_vars=extra)
    assert code == 0, out
    assert "archive: migrate.zip" in out
    assert log == []
    assert zip_file.read_bytes() == b"example zip"
    [folder] = short_tmp.glob("agent-iac-restore-*")
    assert (folder / "restore.zip").read_bytes() == b"example zip"


def test_fetch_decrypts_a_local_age_archive_without_the_bucket(sample_vars, tmp_path, short_tmp):
    archive = tmp_path / "migrate.zip.age"
    archive.write_bytes(b"example archive")
    code, out, log = run_fetch(sample_vars, tmp_path, short_tmp, extra_vars={"box_archive_file": str(archive)})
    assert code == 0, out
    [age] = log
    assert age.startswith("age -d ") and age.endswith(f" {archive}")
    assert archive.exists()


# Each refusal names its problem and stops before the private folder is made.
@pytest.mark.parametrize(
    ("extra", "problem"),
    [
        ({"box_archive_file": "{tmp}/migrate.tar"}, "is not a .zip or a .zip.age"),
        ({"box_archive_file": "migrate.zip"}, "is not an absolute path"),
        ({"box_archive_file": "{tmp}/missing.zip"}, "is not a file"),
        ({"box_archive_file": "{tmp}/migrate.zip", "box_archive": ARCHIVES[0]}, "not both"),
    ],
)
def test_fetch_refuses_a_bad_local_archive(sample_vars, tmp_path, short_tmp, extra, problem):
    for name in ("migrate.tar", "migrate.zip"):
        (tmp_path / name).write_bytes(b"example")
    extra = {k: v.format(tmp=tmp_path) for k, v in extra.items()}
    code, out, log = run_fetch(sample_vars, tmp_path, short_tmp, extra_vars=extra)
    assert code != 0
    assert problem in out
    assert "TASK [Make the private folder]" not in out
    assert log == []


# The files the v0.3 backup wrote for its SFTP host: 0002-the-box design D11 and D12; 0004-the-handover review R10.
V03_BACKUP_FILES = {
    "/home/box/.config/agent-iac/example.restic.env",
    "/home/box/.ssh/id_ed25519",
    "/home/box/.ssh/id_ed25519.pub",
    "/home/box/.ssh/config",
    "/home/box/.ssh/known_hosts",
}


def removed_paths(path, sample_vars):
    """Return the paths a task file sets absent, each loop item rendered, e.g. a loop over [a, b] → {.../a, .../b}."""
    env, paths = jinja_env(), set()
    for t in tasks(path):
        f = t.get("ansible.builtin.file", {})
        if f.get("state") == "absent":
            for item in t.get("loop", [None]):
                paths.add(env.from_string(f["path"]).render({**sample_vars, "item": item}))
    return paths


# An upgraded v0.3 box keeps no key its old backup host still accepts.
def test_apply_removes_what_the_v03_backup_left(sample_vars):
    assert removed_paths("roles/box/tasks/backup.yml", sample_vars) >= V03_BACKUP_FILES


SEND = "roles/box/tasks/send.yml"


def includes(t, tasks_from):
    return t.get("ansible.builtin.include_role", {}).get("tasks_from") == tasks_from


# The decrypted zip leaves this machine with its copy to the box, whatever the box does: 0004-the-handover review R2.
def test_the_decrypted_zip_is_removed_here_whatever_the_box_does():
    [hand] = plays(SEND)
    copy, check = hand["block"]
    assert copy["name"] == "Copy the zip to the box" and copy["ignore_unreachable"] is True
    assert check["ansible.builtin.assert"]["that"] == f"{copy['register']} is not unreachable"
    [rm] = hand["always"]
    assert rm["delegate_to"] == "localhost" and rm["become"] is False
    assert rm["ansible.builtin.file"] == {"path": "{{ box_local }}", "state": "absent"}


# An unreachable box stops the run before the decrypt; once decrypted, the zip's hand-over is the box's first task.
@pytest.mark.parametrize("path", ["playbooks/restore.yml", "playbooks/restore_drill.yml"])
def test_the_box_is_reached_before_the_decrypt_and_handed_the_zip_first(path):
    play_list = plays(path)
    fetch = next(i for i, p in enumerate(play_list) if any(includes(t, "fetch.yml") for t in walk(p["tasks"])))
    reach = [p for p in play_list[:fetch] if p["hosts"] == "box"]
    assert reach and any(includes(t, "user_env.yml") for t in walk(reach[0]["tasks"]))
    [box_play] = [p for p in play_list[fetch + 1 :] if p["hosts"] == "box"]
    first = next(t for t in walk(box_play["tasks"]) if "block" not in t)
    assert includes(first, "send.yml")


def test_the_drill_removes_its_scratch_volume_on_every_exit():
    block = task("playbooks/restore_drill.yml", "Drill in a scratch volume")
    rm = task("playbooks/restore_drill.yml", "Remove the scratch volume")
    assert rm in block["always"]
    assert argv(rm) == ["podman", "volume", "rm", "-f", "{{ box.name }}-drill"]
    assert "Remove the zip from the box" in names(block["always"])


# An apply that failed after writing the quadlet leaves it unchanged, so the reload cannot hang on that change.
def test_every_apply_reloads_systemd_before_the_start():
    start = task("roles/box/tasks/box.yml", "Start the service")["ansible.builtin.systemd_service"]
    assert start["daemon_reload"] is True
    assert not [t for t in tasks("roles/box/tasks/box.yml") if t.get("when") == "box_quadlet is changed"]


# /proc shows a command line to every local user, so the auth key reaches tailscale in a root-only file.
def test_the_join_keeps_the_auth_key_off_the_command_line():
    join = task("roles/box/tasks/host.yml", "Join the tailnet")["ansible.builtin.command"]
    assert "TAILSCALE_AUTH_KEY" not in join and "--auth-key=file:" in join


def secret_faults(t):
    """Return how a deploy-key task could leak the key, e.g. a task without no_log → ["no_log"]."""
    cmd = t["ansible.builtin.command"]
    faults = [] if t.get("no_log") is True else ["no_log"]
    return faults + ([] if "stdin" in cmd else ["stdin"])


# The key reaches podman on stdin and never shows in a log, so it stays off /proc and the operator's terminal.
def test_the_deploy_key_stays_off_the_command_line_and_the_log():
    assert secret_faults(task("roles/box/tasks/box.yml", "Store the deploy key")) == []


def test_secret_check_catches_a_logged_key():
    t = task("roles/box/tasks/box.yml", "Store the deploy key")
    cmd = {k: v for k, v in t["ansible.builtin.command"].items() if k != "stdin"}
    assert secret_faults({"ansible.builtin.command": cmd}) == ["no_log", "stdin"]


def clone_faults(look, clone):
    """Return how the KB clone could touch an existing clone or the wrong owner, e.g. no guard → ["guard"]."""
    faults = [] if "test -d {{ manifest.blueprint_mount }}/kb/.git" in look["ansible.builtin.command"] else ["test"]
    faults += [] if clone.get("when") == "box_kb_clone.rc == 1" else ["guard"]
    cmd = clone["ansible.builtin.command"]["cmd"]
    faults += [] if "podman exec --user 10000 " in cmd else ["user"]
    return faults + ([] if "git clone {{ box.kb }} {{ manifest.blueprint_mount }}/kb" in cmd else ["target"])


# An existing clone may hold unpushed commits, so apply clones only where no repository is, as the agent's user.
def test_the_kb_is_cloned_once_as_the_agent():
    look = task("roles/box/tasks/kb.yml", "Look for the KB clone")
    assert clone_faults(look, task("roles/box/tasks/kb.yml", "Clone the KB")) == []


def test_clone_check_catches_an_unguarded_clone():
    look = {"ansible.builtin.command": "podman exec example true"}
    clone = {"ansible.builtin.command": {"cmd": "podman exec example git clone x /tmp"}}
    assert clone_faults(look, clone) == ["test", "guard", "user", "target"]


def flush_before_clone(path):
    """Return whether handlers flush after the start and before kb.yml is imported, e.g. no flush → False."""
    steps = [t.get("ansible.builtin.meta") or t.get("ansible.builtin.import_tasks") or t.get("name") for t in tasks(path)]
    start, clone = steps.index("Start the service"), steps.index("kb.yml")
    return "flush_handlers" in steps[start + 1 : clone]


# A running box restarts only in a handler, so the clone must not run in the container the old quadlet started.
def test_the_kb_is_cloned_in_the_container_the_new_quadlet_starts():
    assert flush_before_clone("roles/box/tasks/box.yml")


def test_flush_check_catches_a_clone_before_the_restart(tmp_path):
    play = [{"name": "Start the service"}, {"ansible.builtin.import_tasks": "kb.yml"}, {"ansible.builtin.meta": "flush_handlers"}]
    (tmp_path / "box.yml").write_text(yaml.safe_dump(play))
    assert not flush_before_clone(tmp_path / "box.yml")


def run_drill_check(home):
    """Run the drill's check on a folder standing in for the imported volume; return the finished process."""
    script = plays("playbooks/restore_drill.yml")[-1]["vars"]["box_drill_check"]
    return subprocess.run([sys.executable, "-c", script, str(home)], capture_output=True, text=True, check=False)


def make_state(home, sessions=True):
    (home / "config.yaml").write_text("model: example\n")
    db = sqlite3.connect(home / "state.db")
    if sessions:
        db.execute("CREATE TABLE sessions (id TEXT)")
        db.execute("INSERT INTO sessions VALUES ('a'), ('b')")
    db.commit()
    db.close()


def test_the_drill_check_passes_a_sound_state_and_counts_its_sessions(tmp_path):
    make_state(tmp_path)
    done = run_drill_check(tmp_path)
    assert (done.returncode, done.stdout) == (0, "sessions: 2\n")


@pytest.mark.parametrize(
    ("damage", "named"),
    [
        (lambda home: (home / "config.yaml").unlink(), "config.yaml exists"),
        (lambda home: (home / "state.db").write_bytes(b"SQLite format 3\0" + b"\xff" * 4096), "PRAGMA integrity_check"),
        (lambda home: sqlite3.connect(home / "state.db").execute("DROP TABLE sessions").connection.commit(), "a sessions table"),
    ],
)
def test_the_drill_check_names_the_failed_check(tmp_path, damage, named):
    make_state(tmp_path)
    damage(tmp_path)
    done = run_drill_check(tmp_path)
    assert done.returncode != 0 and f"drill failed: {named}" in done.stderr

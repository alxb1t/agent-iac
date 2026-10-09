"""The playbooks and the role's tasks, read as YAML: the commands that can lose state or wedge an apply."""

import shlex
import sqlite3
import subprocess
import sys

import pytest
import yaml

from conftest import ROOT, jinja_env


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
    assert steps.index("Stop the box") < steps.index("Import the archive")
    assert {"Start the box", "Remove the zip from the box", "Remove the decrypted archive"} <= set(names(block["always"]))


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


def test_the_drill_removes_its_scratch_volume_on_every_exit():
    block = task("playbooks/restore_drill.yml", "Drill in a scratch volume")
    rm = task("playbooks/restore_drill.yml", "Remove the scratch volume")
    assert rm in block["always"]
    assert argv(rm) == ["podman", "volume", "rm", "-f", "{{ box.name }}-drill"]
    assert "Remove the decrypted archive" in names(block["always"])


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

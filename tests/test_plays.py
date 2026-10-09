"""The playbooks and the role's tasks, read as YAML: the commands that can lose state or wedge an apply."""

import shlex

import yaml

from conftest import ROOT


def tasks(path):
    """Yield every task in a playbook or a task file, blocks flattened, e.g. a block's `always` tasks too."""

    def walk(items):
        for item in items or []:
            yield item
            for key in ("tasks", "block", "rescue", "always"):
                yield from walk(item.get(key))

    yield from walk(yaml.safe_load((ROOT / path).read_text()))


def task(path, name):
    return next(t for t in tasks(path) if t.get("name") == name)


# A restore deletes what the snapshot lacks, so its target is the volume and nothing above it.
def test_restore_deletes_only_inside_the_volume():
    cmd = task("playbooks/restore.yml", "Replace the volume with the snapshot")["ansible.builtin.command"]["argv"][-1]
    restic = shlex.split(cmd[cmd.index("restic restore") :])
    assert "--delete" in restic
    assert restic[restic.index("--target") + 1] == "$data"
    assert restic[2].endswith(":$data")
    play = next(p for p in yaml.safe_load((ROOT / "playbooks/restore.yml").read_text()) if p["hosts"] == "box")
    assert "data=$(podman volume inspect" in play["vars"]["box_as_user"]


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
    faults += [] if "stdin" in cmd else ["stdin"]
    return faults + (["key on the command line"] if "KB_DEPLOY_KEY" in str(cmd.get("cmd", "")) else [])


# The key reaches podman on stdin and never shows in a log, so it stays off /proc and the operator's terminal.
def test_the_deploy_key_stays_off_the_command_line_and_the_log():
    assert secret_faults(task("roles/box/tasks/box.yml", "Store the deploy key")) == []


def test_secret_check_catches_a_logged_key():
    t = task("roles/box/tasks/box.yml", "Store the deploy key")
    cmd = {k: v for k, v in t["ansible.builtin.command"].items() if k != "stdin"}
    assert secret_faults({"ansible.builtin.command": cmd}) == ["no_log", "stdin"]


def clone_faults(path):
    """Return how the KB clone could touch an existing clone or the wrong owner, e.g. no guard → ["guard"]."""
    look = task(path, "Look for the KB clone")
    clone = task(path, "Clone the KB")
    faults = [] if "test -d {{ manifest.blueprint_mount }}/kb/.git" in look["ansible.builtin.command"] else ["test"]
    faults += [] if clone.get("when") == "box_kb_clone.rc == 1" else ["guard"]
    cmd = clone["ansible.builtin.command"]["cmd"]
    faults += [] if "podman exec --user 10000 " in cmd else ["user"]
    return faults + ([] if "git clone {{ box.kb }} {{ manifest.blueprint_mount }}/kb" in cmd else ["target"])


# An existing clone may hold unpushed commits, so apply clones only where no repository is, as the agent's user.
def test_the_kb_is_cloned_once_as_the_agent():
    assert clone_faults("roles/box/tasks/box.yml") == []


def test_clone_check_catches_an_unguarded_clone(tmp_path):
    text = (ROOT / "roles/box/tasks/box.yml").read_text()
    text = text.replace("when: box_kb_clone.rc == 1", "when: box.kb is defined").replace("--user 10000 ", "")
    (tmp_path / "box.yml").write_text(text)
    assert clone_faults(tmp_path / "box.yml") == ["guard", "user"]

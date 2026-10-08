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

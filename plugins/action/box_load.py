"""Read box.yaml, validate it and its runtime, decrypt its secrets, and add its target as a host.

Runs on the operator's machine before any connection. Why a file, not an inventory: 0002-the-box design D2.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import yaml
from ansible.errors import AnsibleActionFail
from ansible.plugins.action import ActionBase

from ansible_collections.alxb1t.agent_iac.plugins.module_utils.box_schema import (
    RUNTIMES_DIR,
    missing_secrets,
    read_recipients,
    validate_box,
    validate_manifest,
)

GROUP = "box"


def _read_yaml(path: Path) -> object:
    try:
        return yaml.safe_load(path.read_text())
    except (OSError, yaml.YAMLError) as e:
        raise AnsibleActionFail(f"cannot read {path}: {e}") from None


def _decrypt(path: Path) -> object:
    try:
        out = subprocess.run(
            ["sops", "--decrypt", "--output-type", "json", str(path)],
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        raise AnsibleActionFail("sops is not installed on this machine") from None
    except subprocess.CalledProcessError as e:
        # sops' stderr names the key it lacks, never a plaintext value.
        raise AnsibleActionFail(f"cannot decrypt {path}: {e.stderr.strip()}") from None
    return json.loads(out.stdout)


class ActionModule(ActionBase):
    _requires_connection = False

    def run(self, tmp=None, task_vars=None):
        result = super().run(tmp, task_vars)
        box_file = self._task.args.get("box_file")
        if not box_file:
            raise AnsibleActionFail("box_load needs box_file, e.g. -e box_file=$(CURDIR)/box.yaml")
        box_path = Path(box_file).expanduser().resolve()

        box = _read_yaml(box_path)
        errors = validate_box(box)
        if errors:
            raise AnsibleActionFail("; ".join(errors))
        manifest = _read_yaml(RUNTIMES_DIR / f"{box['runtime']}.yaml")
        errors = validate_manifest(manifest)
        if errors:
            raise AnsibleActionFail(f"runtimes/{box['runtime']}.yaml: " + "; ".join(errors))
        # The secrets' recipients are the archives' recipients: 0004-the-handover design D3.
        recipients, errors = read_recipients(_read_yaml(box_path.parent / ".sops.yaml"))
        if errors:
            raise AnsibleActionFail("; ".join(errors))
        secrets = _decrypt(box_path.parent / "secrets.sops.yaml")
        errors = missing_secrets(secrets, manifest, box)
        if errors:
            raise AnsibleActionFail("; ".join(errors))

        host_vars = {
            "ansible_user": "root",
            "ansible_python_interpreter": "/usr/bin/python3",
            "box": box,
            "manifest": manifest,
            "box_secrets": secrets,
            "box_recipients": recipients,
            "box_dir": str(box_path.parent),
        }
        # The builtin add_host action does both: the result key for older cores, the call for newer.
        result["add_host"] = {"host_name": box["target"], "groups": [GROUP], "host_vars": host_vars}
        if hasattr(self, "add_host"):
            self.add_host(host_name=box["target"], parent_group_names=[GROUP], host_vars=host_vars)
        result["changed"] = False
        result["msg"] = f"box {box['name']} → {box['target']}"
        # The result carries the decrypted secrets in add_host.
        result["_ansible_no_log"] = True
        return result

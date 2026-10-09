"""Sample vars a template sees on a box named example, and a renderer that refuses an undefined one."""

import shlex
from pathlib import Path

import jinja2
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "roles" / "box" / "templates"
# The public half of tests/keys/example.age.
EXAMPLE_RECIPIENT = "age1nhgskk4d2lsf6sk72wxgez67epsu65guw2c6zjn4pn9x48x3tyasdu8y6q"

VALID_BOX = {
    "name": "example",
    "target": "example-pi",
    "runtime": "hermes",
    "version": "v2026.9.24",
    "backup": "r2:0123456789abcdef0123456789abcdef/example-backups",
}


@pytest.fixture(scope="session")
def hermes():
    return yaml.safe_load((ROOT / "runtimes" / "hermes.yaml").read_text())


@pytest.fixture(scope="session")
def sample_vars(hermes):
    return {
        "box": VALID_BOX,
        "manifest": hermes,
        "box_secrets": {
            "TELEGRAM_BOT_TOKEN": "example-bot-token",
            "TELEGRAM_ALLOWED_USERS": "1",
            "OPENROUTER_API_KEY": "example-openrouter-key",
            "HERMES_DASHBOARD_BASIC_AUTH_USERNAME": "example",
            "HERMES_DASHBOARD_BASIC_AUTH_PASSWORD_HASH": "scrypt$16384$8$1$ZXhhbXBsZQ==$ZXhhbXBsZQ==",
            "HERMES_DASHBOARD_BASIC_AUTH_SECRET": "example-dashboard-secret",
            "TAILSCALE_AUTH_KEY": "example-tailscale-key",
            "R2_ACCESS_KEY_ID": "example-r2-access-key-id",
            "R2_SECRET_ACCESS_KEY": "example-r2-secret-access-key",
            "RESTIC_PASSWORD": "example-restic-password",
        },
        "box_user": "box",
        "box_config": "/home/box/.config/agent-iac",
        "box_restic_env": "/home/box/.config/agent-iac/example.restic.env",
        "box_tailnet_ip": "100.64.0.1",
        "box_recipients": [EXAMPLE_RECIPIENT],
    }


@pytest.fixture(scope="session")
def render(sample_vars):
    # The template module's defaults; `quote` is Ansible's filter of the same name.
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(TEMPLATES),
        undefined=jinja2.StrictUndefined,
        trim_blocks=True,
        keep_trailing_newline=True,
    )
    env.filters["quote"] = shlex.quote

    def _render(name, **overrides):
        return env.get_template(name).render({**sample_vars, **overrides})

    return _render

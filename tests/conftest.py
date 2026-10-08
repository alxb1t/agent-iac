"""Sample vars a template sees on a box named example, and a renderer that refuses an undefined one."""

from pathlib import Path

import jinja2
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "roles" / "box" / "templates"


@pytest.fixture
def sample_vars():
    manifest = yaml.safe_load((ROOT / "runtimes" / "hermes.yaml").read_text())
    return {
        "box": {
            "name": "example",
            "target": "example-pi",
            "runtime": "hermes",
            "version": "v2026.9.24",
            "backup": "sftp:backup@example-nas:/srv/restic/example",
        },
        "manifest": manifest,
        "box_secrets": {
            "TELEGRAM_BOT_TOKEN": "example-bot-token",
            "TELEGRAM_ALLOWED_USERS": "1",
            "OPENROUTER_API_KEY": "example-openrouter-key",
            "TAILSCALE_AUTH_KEY": "example-tailscale-key",
            "RESTIC_PASSWORD": "example-restic-password",
        },
        "box_user": "box",
    }


@pytest.fixture
def render(sample_vars):
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(TEMPLATES),
        undefined=jinja2.StrictUndefined,
        keep_trailing_newline=True,
    )

    def _render(name, **overrides):
        return env.get_template(name).render({**sample_vars, **overrides})

    return _render

"""Sample vars a template sees on a box named example, and a renderer that refuses an undefined one."""

import shlex
from pathlib import Path

import jinja2
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "roles" / "box" / "templates"
DEFAULTS = ROOT / "roles" / "box" / "defaults" / "main.yml"
# The public half of tests/keys/example.age.
EXAMPLE_RECIPIENT = "age1nhgskk4d2lsf6sk72wxgez67epsu65guw2c6zjn4pn9x48x3tyasdu8y6q"

VALID_BOX = {
    "name": "example",
    "target": "example-pi",
    "runtime": "hermes",
    "version": "v2026.9.24",
    "backup": "r2:0123456789abcdef0123456789abcdef/example-backups",
}
# A week of the example box's nightly archives, unsorted, and those of a box whose name starts with its own.
ARCHIVES = [f"example-202610{d:02d}T040000Z.zip.age" for d in (3, 1, 7, 2, 5, 4, 6)]
OTHER_BOX_ARCHIVES = [f"example-two-202610{d:02d}T040000Z.zip.age" for d in range(1, 9)]


def jinja_env(**options):
    """Return a Jinja environment that refuses an undefined name and has Ansible's `quote`, as shlex's."""
    env = jinja2.Environment(undefined=jinja2.StrictUndefined, **options)
    env.filters["quote"] = shlex.quote
    return env


def with_role_defaults(values):
    """Return values plus the role's defaults they do not set, each rendered over the names before it."""
    env, scope = jinja_env(), dict(values)

    def resolve(value):
        if isinstance(value, str):
            return env.from_string(value).render(scope)
        if isinstance(value, dict):
            return {k: resolve(v) for k, v in value.items()}
        return [resolve(v) for v in value] if isinstance(value, list) else value

    # A default names only the defaults above it, so one pass in file order resolves them all.
    for name, value in yaml.safe_load(DEFAULTS.read_text()).items():
        if name not in values:
            scope[name] = resolve(value)
    return scope


@pytest.fixture(scope="session")
def hermes():
    return yaml.safe_load((ROOT / "runtimes" / "hermes.yaml").read_text())


@pytest.fixture(scope="session")
def sample_values(hermes):
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
        },
        "box_tailnet_ip": "100.64.0.1",
        "box_recipients": [EXAMPLE_RECIPIENT],
    }


@pytest.fixture(scope="session")
def sample_vars(sample_values):
    return with_role_defaults(sample_values)


@pytest.fixture(scope="session")
def render(sample_values):
    # The template module's defaults; `quote` is Ansible's filter of the same name.
    env = jinja_env(loader=jinja2.FileSystemLoader(TEMPLATES), trim_blocks=True, keep_trailing_newline=True)

    def _render(name, **overrides):
        # The defaults are derived again, so an override of `box` or `box_secrets` reaches them.
        return env.get_template(name).render(with_role_defaults({**sample_values, **overrides}))

    return _render

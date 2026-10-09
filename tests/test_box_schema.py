"""The box.yaml and manifest validators: each fault is named, and the valid input is its twin."""

import pytest

from box_schema import (
    BOX_KEYS,
    MANIFEST_KEYS,
    known_runtimes,
    missing_secrets,
    validate_box,
    validate_manifest,
)
from conftest import VALID_BOX


def test_valid_box_is_accepted():
    assert validate_box(dict(VALID_BOX)) == []


@pytest.mark.parametrize("key", BOX_KEYS)
def test_each_missing_key_is_named(key):
    box = {k: v for k, v in VALID_BOX.items() if k != key}
    assert validate_box(box) == [f"box.yaml: missing key {key}"]


def test_extra_key_is_named():
    assert validate_box({**VALID_BOX, "allowed_users": "1"}) == ["box.yaml: unknown key allowed_users"]


def test_every_fault_is_named_at_once():
    box = {k: v for k, v in VALID_BOX.items() if k != "backup"}
    box["allowed_users"] = "1"
    assert validate_box(box) == ["box.yaml: missing key backup", "box.yaml: unknown key allowed_users"]


def test_unknown_runtime_names_it_and_the_known_ones():
    errors = validate_box({**VALID_BOX, "runtime": "nope"})
    assert errors == ["box.yaml: unknown runtime nope; known: hermes"]


def test_known_runtimes_reads_the_shipped_manifests():
    assert known_runtimes() == ["hermes"]


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("name", "Example"),
        ("name", "x"),
        ("version", ""),
        ("backup", "example-nas:/srv"),
        ("target", 3),
        ("kb", "https://github.com/example/example-kb.git"),
        ("kb", "git@gitlab.com:example/example-kb.git"),
        ("kb", "git@github.com:example/example-kb.git\n"),
        ("kb", 3),
    ],
)
def test_bad_value_is_refused(key, value):
    errors = validate_box({**VALID_BOX, key: value})
    assert len(errors) == 1 and key in errors[0]


def test_box_with_kb_is_accepted():
    assert validate_box({**VALID_BOX, "kb": "git@github.com:example/example-kb.git"}) == []


def test_hermes_manifest_is_valid(hermes):
    assert validate_manifest(hermes) == []
    assert hermes["state"] == ["/opt/data"]
    assert hermes["env"] == [
        "TELEGRAM_BOT_TOKEN",
        "TELEGRAM_ALLOWED_USERS",
        "OPENROUTER_API_KEY",
        "HERMES_DASHBOARD_BASIC_AUTH_USERNAME",
        "HERMES_DASHBOARD_BASIC_AUTH_PASSWORD_HASH",
        "HERMES_DASHBOARD_BASIC_AUTH_SECRET",
    ]
    assert hermes["ports"] == [9119]


# The variables that point the skills and the sync plugin at the KB; the role clones it to <blueprint_mount>/kb.
KB_VARIABLES = ("WIKI_PATH", "OBSIDIAN_VAULT_PATH", "GIT_HOOK_ROOTS")


def kb_path_errors(manifest):
    """Return each KB variable not set to <blueprint_mount>/kb, e.g. {"WIKI_PATH": "/x"} → ["WIKI_PATH"]."""
    kb = f"{manifest['blueprint_mount']}/kb"
    return [k for k in KB_VARIABLES if manifest["environment"].get(k) != kb]


def test_every_kb_path_is_the_cloned_path(hermes):
    assert kb_path_errors(hermes) == []


def test_kb_path_check_catches_a_drifted_path(hermes):
    manifest = {**hermes, "environment": {**hermes["environment"], "WIKI_PATH": "/opt/data/wiki"}}
    assert kb_path_errors(manifest) == ["WIKI_PATH"]


@pytest.mark.parametrize(
    "environment",
    [["HERMES_DASHBOARD=1"], {"hermes_dashboard": "1"}, {"HERMES_DASHBOARD": 1}, {"WIKI_PATH": None}],
)
def test_malformed_environment_is_refused(hermes, environment):
    assert validate_manifest({**hermes, "environment": environment}) == [
        "manifest: environment must map environment variable names to strings"
    ]


@pytest.mark.parametrize("ports", [[0], ["9119"], [65536], [True], 9119])
def test_malformed_ports_are_refused(hermes, ports):
    assert validate_manifest({**hermes, "ports": ports}) == [
        "manifest: ports must be a list of TCP ports from 1 to 65535"
    ]


def test_empty_environment_and_ports_are_accepted(hermes):
    assert validate_manifest({**hermes, "environment": {}, "ports": []}) == []


@pytest.mark.parametrize("image", ["docker.io/nousresearch/hermes-agent:v1", "hermes-agent@sha256:abc"])
def test_tagged_image_is_refused(hermes, image):
    assert validate_manifest({**hermes, "image": image}) == [
        "manifest: image must be a reference without a tag or digest"
    ]


def test_registry_port_is_not_a_tag(hermes):
    assert validate_manifest({**hermes, "image": "registry.example:5000/agent"}) == []


@pytest.mark.parametrize("key", MANIFEST_KEYS)
def test_each_missing_manifest_key_is_named(hermes, key):
    manifest = {k: v for k, v in hermes.items() if k != key}
    assert validate_manifest(manifest) == [f"manifest: missing key {key}"]


def test_extra_manifest_key_is_named(hermes):
    assert validate_manifest({**hermes, "pre_backup": "x"}) == ["manifest: unknown key pre_backup"]


def test_secrets_complete_is_accepted(hermes, sample_vars):
    assert missing_secrets(sample_vars["box_secrets"], hermes, VALID_BOX) == []


def test_kb_requires_its_deploy_key(hermes, sample_vars):
    secrets = sample_vars["box_secrets"]
    box = {**VALID_BOX, "kb": "git@github.com:example/example-kb.git"}
    assert missing_secrets(secrets, hermes, box) == ["secrets.sops.yaml: missing KB_DEPLOY_KEY"]
    assert missing_secrets({**secrets, "KB_DEPLOY_KEY": "v"}, hermes, box) == []


def test_missing_secret_is_named_without_values(hermes):
    secrets = {n: "s3cr3t" for n in hermes["env"] + ["RESTIC_PASSWORD"] if n != "OPENROUTER_API_KEY"}
    errors = missing_secrets(secrets, hermes, VALID_BOX)
    assert errors == [
        "secrets.sops.yaml: missing OPENROUTER_API_KEY",
        "secrets.sops.yaml: missing TAILSCALE_AUTH_KEY",
    ]
    assert "s3cr3t" not in " ".join(errors)

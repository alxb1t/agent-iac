"""The box.yaml and manifest validators: each fault is named, and the valid input is its twin."""

from pathlib import Path

import pytest
import yaml

from box_schema import (
    BOX_KEYS,
    MANIFEST_KEYS,
    known_runtimes,
    missing_secrets,
    validate_box,
    validate_manifest,
)

ROOT = Path(__file__).resolve().parents[1]

VALID_BOX = {
    "name": "example",
    "target": "example-pi",
    "runtime": "hermes",
    "version": "v2026.9.24",
    "backup": "sftp:backup@example-nas:/srv/restic/example",
}


@pytest.fixture
def hermes():
    return yaml.safe_load((ROOT / "runtimes" / "hermes.yaml").read_text())


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
    [("name", "Example"), ("name", "x"), ("version", ""), ("backup", "example-nas:/srv"), ("target", 3)],
)
def test_bad_value_is_refused(key, value):
    errors = validate_box({**VALID_BOX, key: value})
    assert len(errors) == 1 and key in errors[0]


def test_hermes_manifest_is_valid(hermes):
    assert validate_manifest(hermes) == []
    assert hermes["state"] == ["/opt/data"]
    assert hermes["env"] == ["TELEGRAM_BOT_TOKEN", "TELEGRAM_ALLOWED_USERS", "OPENROUTER_API_KEY"]


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


def test_secrets_complete_is_accepted(hermes):
    secrets = {n: "v" for n in hermes["env"] + ["TAILSCALE_AUTH_KEY", "RESTIC_PASSWORD"]}
    assert missing_secrets(secrets, hermes) == []


def test_missing_secret_is_named_without_values(hermes):
    secrets = {n: "s3cr3t" for n in hermes["env"] + ["RESTIC_PASSWORD"] if n != "OPENROUTER_API_KEY"}
    errors = missing_secrets(secrets, hermes)
    assert errors == [
        "secrets.sops.yaml: missing OPENROUTER_API_KEY",
        "secrets.sops.yaml: missing TAILSCALE_AUTH_KEY",
    ]
    assert "s3cr3t" not in " ".join(errors)

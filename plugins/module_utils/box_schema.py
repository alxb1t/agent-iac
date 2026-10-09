"""Validate the box.yaml and runtime manifest contracts, before any connection.

Each function returns every error at once, so one message names every fault.
Why pure functions: 0002-the-box design D3.
"""

from __future__ import annotations

import re
from pathlib import Path

RUNTIMES_DIR = Path(__file__).resolve().parents[2] / "runtimes"

BOX_KEYS = ("name", "target", "runtime", "version", "backup")
BOX_OPTIONAL_KEYS = ("kb",)
MANIFEST_KEYS = ("image", "state", "env", "blueprint_mount", "environment", "ports", "backup", "restore")
HOST_SECRETS = ("TAILSCALE_AUTH_KEY", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY")
KB_SECRET = "KB_DEPLOY_KEY"

NAME = re.compile(r"^[a-z][a-z0-9-]{1,31}$")
ENV_NAME = re.compile(r"^[A-Z_][A-Z0-9_]*$")
# The account id names the endpoint; the bucket follows R2's naming rule (0004-the-handover design D2).
R2_URL = re.compile(r"^r2:[0-9a-f]{32}/[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$")
AGE_RECIPIENT = re.compile(r"^age1[0-9a-z]{58}$")
ARCHIVE = "{archive}"
# GitHub only: its host keys are the ones the base blueprint pins (0003-the-knowledge-base design D3).
KB_URL = re.compile(r"^git@github\.com:[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\.git$")


def known_runtimes(runtimes_dir: Path = RUNTIMES_DIR) -> list[str]:
    """Return the names of the runtime manifests the collection ships, sorted.

    e.g. runtimes/hermes.yaml → ["hermes"]
    """
    return sorted(p.stem for p in runtimes_dir.glob("*.yaml"))


def _key_errors(data: object, keys: tuple[str, ...], what: str, optional: tuple[str, ...] = ()) -> list[str]:
    if not isinstance(data, dict):
        return [f"{what}: must be a mapping"]
    missing = [k for k in keys if k not in data]
    extra = sorted(str(k) for k in data if k not in keys + optional)
    return [f"{what}: missing key {k}" for k in missing] + [f"{what}: unknown key {k}" for k in extra]


def validate_box(box: object, runtimes_dir: Path = RUNTIMES_DIR) -> list[str]:
    """Return every error in a parsed box.yaml; an empty list means it is valid."""
    errors = _key_errors(box, BOX_KEYS, "box.yaml", BOX_OPTIONAL_KEYS)
    if not isinstance(box, dict):
        return errors
    for key in BOX_KEYS:
        if key in box and not (isinstance(box[key], str) and box[key]):
            errors.append(f"box.yaml: {key} must be a non-empty string")
    if isinstance(box.get("name"), str) and box["name"] and not NAME.match(box["name"]):
        errors.append(f"box.yaml: name must match {NAME.pattern}")
    runtime = box.get("runtime")
    known = known_runtimes(runtimes_dir)
    if isinstance(runtime, str) and runtime and runtime not in known:
        errors.append(f"box.yaml: unknown runtime {runtime}; known: {', '.join(known)}")
    backup = box.get("backup")
    # fullmatch: `$` alone lets a trailing newline through.
    if isinstance(backup, str) and backup and not R2_URL.fullmatch(backup):
        errors.append("box.yaml: backup must be an R2 bucket, e.g. r2:<32 hex digits of account id>/example-backups")
    if "kb" in box and not (isinstance(box["kb"], str) and KB_URL.fullmatch(box["kb"])):
        errors.append("box.yaml: kb must be a GitHub SSH URL, e.g. git@github.com:example/example-kb.git")
    return errors


def _is_abs_path(value: object) -> bool:
    return isinstance(value, str) and value.startswith("/")


def _is_command(value: object) -> bool:
    return (
        isinstance(value, list)
        and bool(value)
        and all(isinstance(a, str) for a in value)
        and sum(a.count(ARCHIVE) for a in value) == 1
    )


def _is_port(value: object) -> bool:
    # bool is an int subclass: `True` would pass as port 1.
    return isinstance(value, int) and not isinstance(value, bool) and 1 <= value <= 65535


def validate_manifest(manifest: object) -> list[str]:
    """Return every error in a parsed runtime manifest; an empty list means it is valid."""
    errors = _key_errors(manifest, MANIFEST_KEYS, "manifest")
    if not isinstance(manifest, dict):
        return errors
    if "image" in manifest:
        image = manifest["image"]
        last = image.rsplit("/", 1)[-1] if isinstance(image, str) else ""
        if not (isinstance(image, str) and image) or ":" in last or "@" in image:
            errors.append("manifest: image must be a reference without a tag or digest")
    if "state" in manifest:
        state = manifest["state"]
        if not (isinstance(state, list) and state and all(_is_abs_path(p) for p in state)):
            errors.append("manifest: state must be a non-empty list of absolute paths")
    if "env" in manifest:
        env = manifest["env"]
        if not (isinstance(env, list) and all(isinstance(n, str) and ENV_NAME.match(n) for n in env)):
            errors.append("manifest: env must be a list of environment variable names")
    if "blueprint_mount" in manifest and not _is_abs_path(manifest["blueprint_mount"]):
        errors.append("manifest: blueprint_mount must be an absolute path")
    if "environment" in manifest:
        environment = manifest["environment"]
        if not (
            isinstance(environment, dict)
            and all(isinstance(k, str) and ENV_NAME.match(k) and isinstance(v, str) for k, v in environment.items())
        ):
            errors.append("manifest: environment must map environment variable names to strings")
    if "ports" in manifest:
        ports = manifest["ports"]
        if not (isinstance(ports, list) and all(_is_port(p) for p in ports)):
            errors.append("manifest: ports must be a list of TCP ports from 1 to 65535")
    for key in ("backup", "restore"):
        if key in manifest and not _is_command(manifest[key]):
            errors.append(f"manifest: {key} must be a non-empty list of strings holding {ARCHIVE} exactly once")
    return errors


def missing_secrets(secrets: object, manifest: dict, box: dict) -> list[str]:
    """Return an error per secret name the box needs and the decrypted file lacks; values are never named."""
    have = secrets if isinstance(secrets, dict) else {}
    need = list(manifest.get("env", [])) + list(HOST_SECRETS) + ([KB_SECRET] if "kb" in box else [])
    return [f"secrets.sops.yaml: missing {n}" for n in need if n not in have]


def read_recipients(sops_config: object) -> tuple[list[str], list[str]]:
    """Return the age recipients of a parsed .sops.yaml's first creation rule, and every error.

    e.g. {"creation_rules": [{"age": "age1…,age1…"}]} → (["age1…", "age1…"], [])
    """
    rules = sops_config.get("creation_rules") if isinstance(sops_config, dict) else None
    rule = rules[0] if isinstance(rules, list) and rules and isinstance(rules[0], dict) else {}
    age = rule.get("age")
    # sops takes the keys as one comma-separated string or as a list.
    keys = [k.strip() for k in age.split(",") if k.strip()] if isinstance(age, str) else age
    if not (isinstance(keys, list) and keys):
        return [], [".sops.yaml: the first creation rule names no age recipient"]
    good = [k for k in keys if isinstance(k, str) and AGE_RECIPIENT.fullmatch(k)]
    return good, [f".sops.yaml: {k!r} is not an age public key" for k in keys if k not in good]

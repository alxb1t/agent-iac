"""Validate the box.yaml and runtime manifest contracts, before any connection.

Each function returns every error at once, so one message names every fault.
Why pure functions: 0002-the-box design D3.
"""

from __future__ import annotations

import re
from pathlib import Path

RUNTIMES_DIR = Path(__file__).resolve().parents[2] / "runtimes"

BOX_KEYS = ("name", "target", "runtime", "version", "backup")
MANIFEST_KEYS = ("image", "state", "env", "blueprint_mount")
HOST_SECRETS = ("TAILSCALE_AUTH_KEY", "RESTIC_PASSWORD")

NAME = re.compile(r"^[a-z][a-z0-9-]{1,31}$")
ENV_NAME = re.compile(r"^[A-Z_][A-Z0-9_]*$")
RESTIC_URL = re.compile(r"^(local|sftp|rest|s3|b2|azure|gs|swift|rclone):\S+$")


def known_runtimes(runtimes_dir: Path = RUNTIMES_DIR) -> list[str]:
    """Return the names of the runtime manifests the collection ships, sorted.

    e.g. runtimes/hermes.yaml → ["hermes"]
    """
    return sorted(p.stem for p in runtimes_dir.glob("*.yaml"))


def _key_errors(data: object, keys: tuple[str, ...], what: str) -> list[str]:
    if not isinstance(data, dict):
        return [f"{what}: must be a mapping"]
    missing = [k for k in keys if k not in data]
    extra = sorted(str(k) for k in data if k not in keys)
    return [f"{what}: missing key {k}" for k in missing] + [f"{what}: unknown key {k}" for k in extra]


def validate_box(box: object, runtimes_dir: Path = RUNTIMES_DIR) -> list[str]:
    """Return every error in a parsed box.yaml; an empty list means it is valid."""
    errors = _key_errors(box, BOX_KEYS, "box.yaml")
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
    if isinstance(backup, str) and backup and not RESTIC_URL.match(backup):
        errors.append("box.yaml: backup must be a restic repository URL, e.g. sftp:user@host:/path")
    return errors


def _is_abs_path(value: object) -> bool:
    return isinstance(value, str) and value.startswith("/")


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
    return errors


def missing_secrets(secrets: object, manifest: dict) -> list[str]:
    """Return an error per secret name the box needs and the decrypted file lacks; values are never named."""
    have = secrets if isinstance(secrets, dict) else {}
    need = list(manifest.get("env", [])) + list(HOST_SECRETS)
    return [f"secrets.sops.yaml: missing {n}" for n in need if n not in have]

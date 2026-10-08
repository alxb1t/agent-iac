"""A dict survives a sops round-trip with the committed throwaway age key."""

import os
import shutil
import subprocess
from pathlib import Path

import yaml

KEY = Path(__file__).resolve().parent / "keys" / "example.age"


def _public_key():
    for line in KEY.read_text().splitlines():
        if line.startswith("# public key: "):
            return line.removeprefix("# public key: ")
    raise AssertionError(f"{KEY.name} has no public key line")


def _sops(*args, stdin):
    env = {**os.environ, "SOPS_AGE_KEY_FILE": str(KEY)}
    out = subprocess.run(["sops", *args], input=stdin, capture_output=True, text=True, env=env, check=True)
    return out.stdout


# Fails, never skips: the gate must not pass on a machine that cannot decrypt.
def test_sops_and_age_are_installed():
    assert shutil.which("sops"), "sops is not on PATH"
    assert shutil.which("age"), "age is not on PATH"


def test_round_trip():
    secrets = {"OPENROUTER_API_KEY": "example-key", "RESTIC_PASSWORD": "example password"}
    flags = ["--input-type", "yaml", "--output-type", "yaml"]
    encrypted = _sops("--encrypt", "--age", _public_key(), *flags, "/dev/stdin", stdin=yaml.safe_dump(secrets))
    assert "example-key" not in encrypted
    assert yaml.safe_load(_sops("--decrypt", *flags, "/dev/stdin", stdin=encrypted)) == secrets

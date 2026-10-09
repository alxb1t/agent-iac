"""bootstrap-pi.sh: its usage, the auth key kept off the command line, the keyring checked before apt sees it."""

import re
import subprocess

import pytest

from conftest import ROOT

SCRIPT = ROOT / "contrib" / "bootstrap-pi.sh"


@pytest.mark.parametrize("args", [[], ["tskey-example", "ssh-ed25519 AAAA example"]])
def test_anything_but_one_argument_prints_usage_and_exits_one(args):
    done = subprocess.run(["sh", str(SCRIPT), *args], capture_output=True, text=True, check=False)
    assert done.returncode == 1
    assert done.stderr.startswith("usage: ")


def auth_key_faults(text):
    """Return how the auth key could reach a command line, e.g. `authkey=$1` → ["argument"]."""
    read = re.search(r"read -r (\w+) </dev/tty", text)
    if not read:
        return ["tty"]
    return ["argument"] if re.search(rf"^\s*{read[1]}=\"?\$\{{?[0-9@*]", text, re.M) else []


# An argument shows in ps and the shell history; the terminal does not (0002·R16).
def test_the_auth_key_is_read_from_the_terminal_never_an_argument():
    assert auth_key_faults(SCRIPT.read_text()) == []


def test_auth_key_check_catches_an_argument():
    assert auth_key_faults("authkey=$1\nIFS= read -r authkey </dev/tty\n") == ["argument"]
    assert auth_key_faults("authkey=$1\n") == ["tty"]


def keyring_faults(text):
    """Return how a cut-short download could reach apt's keyring path, e.g. `curl -o "$keyring"` → ["mktemp"]."""
    curl = re.search(r'curl [^\n]*-o "\$(\w+)" [^\n]*\.gpg', text)
    if not curl:
        return ["curl"]
    var = curl[1]
    faults = [] if re.search(rf"^\s*{var}=\$\(mktemp\)$", text, re.M) else ["mktemp"]
    check = text.find("sha256sum -c", curl.end())
    install = text.find(f'install -m 0644 "${var}" "$keyring"', curl.end())
    return faults + ([] if -1 < check < install else ["install after the check"])


# A download cut short never sits where apt trusts keyrings (0002·S8).
def test_the_keyring_is_checked_before_it_is_installed():
    assert keyring_faults(SCRIPT.read_text()) == []


def test_keyring_check_catches_a_download_straight_to_the_keyring():
    text = 'curl -fsSL -o "$keyring" "https://example.invalid/x.gpg"\necho h | sha256sum -c -\n'
    assert keyring_faults(text) == ["mktemp", "install after the check"]

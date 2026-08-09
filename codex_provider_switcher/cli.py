from __future__ import annotations

import argparse
import sys

from .profiles import ProfileRepository
from .secrets import SecretStore
from .windows import codex_home


def auth_command(profile_id: str) -> int:
    home = codex_home()
    store = SecretStore(home / "provider-switcher" / "secrets.json")
    secret = store.get(profile_id)
    if not secret:
        print(f"No API key stored for profile '{profile_id}'", file=sys.stderr)
        return 2
    sys.stdout.write(secret)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(add_help=True)
    subparsers = parser.add_subparsers(dest="command")
    auth = subparsers.add_parser("auth")
    auth.add_argument("--profile", required=True)
    arguments = parser.parse_args(argv)
    if arguments.command == "auth":
        return auth_command(arguments.profile)
    from .gui import run
    run()
    return 0

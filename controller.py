#!/usr/bin/env python3
"""Install demo routes into the BMv2 simple_switch thrift interface."""

from __future__ import annotations

import argparse
import socket
import subprocess
import sys
import time
from pathlib import Path


DEMO_ROUTES = [
    {
        "prefix": "10.0.1.0/24",
        "port": 1,
        "src_mac": "00:aa:bb:00:00:01",
        "dst_mac": "00:04:00:00:01:10",
    },
    {
        "prefix": "10.0.2.0/24",
        "port": 2,
        "src_mac": "00:aa:bb:00:00:02",
        "dst_mac": "00:04:00:00:02:10",
    },
]


def build_commands() -> list[str]:
    commands = ["table_set_default ipv4_lpm drop"]
    for route in DEMO_ROUTES:
        commands.append(
            "table_add ipv4_lpm ipv4_forward {prefix} => {port} {src_mac} {dst_mac}".format(
                **route
            )
        )
    return commands


def install_rules(thrift_port: int, cli_path: str = "simple_switch_CLI") -> subprocess.CompletedProcess[str]:
    commands = "\n".join(build_commands()) + "\n"
    return subprocess.run(
        [cli_path, "--thrift-port", str(thrift_port)],
        input=commands,
        text=True,
        capture_output=True,
        check=True,
    )


def wait_for_thrift(thrift_port: int, wait_seconds: float) -> bool:
    deadline = time.time() + wait_seconds
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.5)
            if sock.connect_ex(("127.0.0.1", thrift_port)) == 0:
                return True
        time.sleep(0.2)
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Install demo BMv2 forwarding rules")
    parser.add_argument("--thrift-port", type=int, default=9090)
    parser.add_argument("--cli-path", default="simple_switch_CLI")
    parser.add_argument("--dry-run", action="store_true", help="Print commands without installing them.")
    parser.add_argument(
        "--wait-seconds",
        type=float,
        default=5.0,
        help="How long to wait for the BMv2 thrift port before failing.",
    )
    parser.add_argument(
        "--write-commands",
        type=Path,
        help="Write the generated BMv2 CLI commands to a file instead of only printing them.",
    )
    args = parser.parse_args()

    commands = build_commands()
    rendered = "\n".join(commands) + "\n"

    if args.write_commands:
        args.write_commands.write_text(rendered, encoding="ascii")

    print(rendered, end="")

    if args.dry_run:
        return 0

    if not wait_for_thrift(args.thrift_port, args.wait_seconds):
        print(
            f"BMv2 switch is not reachable on thrift port {args.thrift_port}. "
            "Start the topology first with `bash run.sh` or `bash run.sh test`.",
            file=sys.stderr,
        )
        print(
            "If you only want to print the commands, use `python3 controller.py --dry-run`.",
            file=sys.stderr,
        )
        return 1

    try:
        result = install_rules(args.thrift_port, args.cli_path)
    except subprocess.CalledProcessError as exc:
        sys.stderr.write(exc.stdout)
        sys.stderr.write(exc.stderr)
        return exc.returncode or 1

    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

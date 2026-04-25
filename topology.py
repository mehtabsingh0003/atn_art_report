#!/usr/bin/env python3
"""Mininet topology for a tiny P4 L3 forwarding demo."""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path
from time import sleep


def locate_p4_mininet() -> Path:
    candidates = [
        Path("/home/mehtabsingh/behavioral-model/mininet"),
        Path("/home/mehtabsingh/mininet/behavioral-model/mininet"),
    ]
    for candidate in candidates:
        if (candidate / "p4_mininet.py").exists():
            return candidate
    raise FileNotFoundError(
        "Could not find p4_mininet.py. Update locate_p4_mininet() with your BMv2 mininet path."
    )


P4_MININET_DIR = locate_p4_mininet()
if str(P4_MININET_DIR) not in sys.path:
    sys.path.append(str(P4_MININET_DIR))

from mininet.cli import CLI
from mininet.log import info, setLogLevel
from mininet.net import Mininet
from mininet.topo import Topo
from p4_mininet import P4Host, P4Switch

from controller import build_decisions, install_rules, render_decision_report


HOSTS = [
    {
        "name": "h1",
        "ip": "10.0.1.10/24",
        "mac": "00:04:00:00:01:10",
        "gw_ip": "10.0.1.1",
        "gw_mac": "00:aa:bb:00:00:01",
    },
    {
        "name": "h2",
        "ip": "10.0.2.10/24",
        "mac": "00:04:00:00:02:10",
        "gw_ip": "10.0.2.1",
        "gw_mac": "00:aa:bb:00:00:02",
    },
]


SCRIPT_DIR = Path(__file__).resolve().parent
BMV2_LIB_DIRS = "/usr/local/lib:/home/mehtabsingh/behavioral-model/targets/simple_switch/.libs"


def ensure_bmv2_library_path() -> None:
    current = os.environ.get("LD_LIBRARY_PATH", "")
    required_parts = BMV2_LIB_DIRS.split(":")
    current_parts = [part for part in current.split(":") if part]

    for part in required_parts:
        if part not in current_parts:
            current_parts.append(part)

    os.environ["LD_LIBRARY_PATH"] = ":".join(current_parts)


def resolve_default_behavioral_exe() -> str | None:
    return shutil.which("simple_switch")


def resolve_default_json() -> str | None:
    candidates = [
        SCRIPT_DIR / "build" / "basic_ml.json",
        SCRIPT_DIR / "basic_ml.json",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return None


class MiniRouterTopo(Topo):
    def __init__(self, sw_path: str, json_path: str, thrift_port: int, **opts) -> None:
        super().__init__(**opts)

        switch = self.addSwitch(
            "s1",
            sw_path=sw_path,
            json_path=json_path,
            thrift_port=thrift_port,
            pcap_dump=False,
            log_console=True,
        )

        for host in HOSTS:
            h = self.addHost(host["name"], ip=host["ip"], mac=host["mac"])
            self.addLink(h, switch)


def configure_hosts(net: Mininet) -> None:
    for host_cfg in HOSTS:
        host = net.get(host_cfg["name"])
        host.setARP(host_cfg["gw_ip"], host_cfg["gw_mac"])
        host.setDefaultRoute(f"dev eth0 via {host_cfg['gw_ip']}")
        host.describe()


def run_smoke_test(net: Mininet) -> None:
    info("\nRunning connectivity test between h1 and h2...\n")
    result = net.get("h1").cmd("ping -c 3 10.0.2.10")
    print(result, end="")

    info("\nRunning a short iperf throughput test...\n")
    server = net.get("h2").popen("iperf3 -s -1")
    sleep(1)
    output = net.get("h1").cmd("iperf3 -c 10.0.2.10 -t 3")
    print(output, end="")
    server.wait(timeout=10)


def main() -> int:
    ensure_bmv2_library_path()

    default_behavioral_exe = resolve_default_behavioral_exe()
    default_json = resolve_default_json()

    parser = argparse.ArgumentParser(description="Run the P4 mini-project topology")
    parser.add_argument("--behavioral-exe", default=default_behavioral_exe)
    parser.add_argument("--json", default=default_json)
    parser.add_argument("--thrift-port", type=int, default=9090)
    parser.add_argument("--no-cli", action="store_true")
    parser.add_argument("--test", action="store_true")
    parser.add_argument("--no-ml", action="store_true", help="Disable ML policy and allow all demo routes.")
    parser.add_argument("--h1-pkt-len", type=int, default=128, help="Packet length feature for h1's prefix.")
    parser.add_argument("--h2-pkt-len", type=int, default=128, help="Packet length feature for h2's prefix.")
    parser.add_argument("--queue-depth", type=int, default=2, help="Queue-depth feature used by the ML model.")
    args = parser.parse_args()

    if not args.behavioral_exe:
        parser.error(
            "Could not find `simple_switch` in PATH. Install BMv2 or run through `bash run.sh`."
        )

    if not args.json:
        parser.error(
            "Could not find a compiled JSON program. Run `bash run.sh` first, or compile with "
            "`p4c --target bmv2 --arch v1model basic_ml.p4 -o build`."
        )

    topo = MiniRouterTopo(args.behavioral_exe, args.json, args.thrift_port)
    net = Mininet(topo=topo, host=P4Host, switch=P4Switch, controller=None)
    net.start()

    try:
        configure_hosts(net)
        sleep(1)

        use_ml = not args.no_ml
        print(
            render_decision_report(
                build_decisions(
                    h1_pkt_len=args.h1_pkt_len,
                    h2_pkt_len=args.h2_pkt_len,
                    queue_depth=args.queue_depth,
                    use_ml=use_ml,
                )
            ),
            end="",
        )
        result = install_rules(
            args.thrift_port,
            h1_pkt_len=args.h1_pkt_len,
            h2_pkt_len=args.h2_pkt_len,
            queue_depth=args.queue_depth,
            use_ml=use_ml,
        )
        if result.stdout:
            print(result.stdout, end="")
        if result.stderr:
            print(result.stderr, end="", file=sys.stderr)

        sleep(1)

        info("\nMini project is ready.\n")
        info("Example checks:\n")
        info("  h1 ping -c 3 10.0.2.10\n")
        info("  h2 tcpdump -enn -i eth0\n")
        info("  h1 traceroute -n 10.0.2.10\n\n")

        if args.test:
            run_smoke_test(net)

        if not args.no_cli:
            CLI(net)
    finally:
        net.stop()

    return 0


if __name__ == "__main__":
    setLogLevel("info")
    raise SystemExit(main())

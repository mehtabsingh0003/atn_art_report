#!/usr/bin/env python3
"""Install ART-style ML policy and routes into the BMv2 simple_switch thrift interface.

The controller trains a compact decision-tree style model, distills its output
into match-action rules, and installs those rules in the P4 data plane. The
P4 program enforces the learned policy in the ml_policy table before applying
the normal ipv4_lpm routing table.
"""

from __future__ import annotations

import argparse
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Route:
    prefix: str
    port: int
    src_mac: str
    dst_mac: str
    pkt_len: int
    queue_depth: int
    flow_count: int


@dataclass(frozen=True)
class Decision:
    route: Route
    packet_class: int
    packet_class_name: str
    action: str
    confidence: float


PACKET_CLASSES = (
    {"id": 0, "name": "small", "sample_len": 128, "range": "<=256 bytes"},
    {"id": 1, "name": "medium", "sample_len": 400, "range": "257-500 bytes"},
    {"id": 2, "name": "large", "sample_len": 800, "range": ">500 bytes"},
)


DEMO_ROUTES = (
    {
        "prefix": "10.0.1.0/24",
        "port": 1,
        "src_mac": "00:aa:bb:00:00:01",
        "dst_mac": "00:04:00:00:01:10",
        "pkt_len": 128,
        "queue_depth": 2,
        "flow_count": 1,
    },
    {
        "prefix": "10.0.2.0/24",
        "port": 2,
        "src_mac": "00:aa:bb:00:00:02",
        "dst_mac": "00:04:00:00:02:10",
        "pkt_len": 128,
        "queue_depth": 2,
        "flow_count": 1,
    },
)


class TinyDecisionTree:
    """Small fallback classifier with the same interface used below.

    scikit-learn is used when it is available. This fallback keeps the project
    runnable on minimal P4/BMv2 VMs where sklearn may not be installed.
    """

    def __init__(self) -> None:
        self.pkt_len_threshold = 500
        self.queue_depth_threshold = 20

    def fit(self, samples: list[list[int]], labels: list[int]) -> "TinyDecisionTree":
        forward_lengths = [sample[0] for sample, label in zip(samples, labels) if label == 0]
        drop_lengths = [sample[0] for sample, label in zip(samples, labels) if label == 1]
        if forward_lengths and drop_lengths:
            self.pkt_len_threshold = (max(forward_lengths) + min(drop_lengths)) // 2
        return self

    def predict(self, samples: list[list[int]]) -> list[int]:
        predictions = []
        for pkt_len, queue_depth, _flow_count in samples:
            should_drop = (
                pkt_len > self.pkt_len_threshold
                or queue_depth > self.queue_depth_threshold
            )
            predictions.append(1 if should_drop else 0)
        return predictions

    def predict_proba(self, samples: list[list[int]]) -> list[list[float]]:
        probabilities = []
        for prediction in self.predict(samples):
            probabilities.append([0.90, 0.10] if prediction == 0 else [0.10, 0.90])
        return probabilities


def train_ml_model():
    samples = [
        [64, 1, 1],
        [128, 3, 2],
        [300, 8, 5],
        [520, 6, 3],
        [800, 18, 8],
        [256, 30, 12],
    ]
    labels = [0, 0, 0, 1, 1, 1]  # 0 = forward, 1 = drop

    try:
        from sklearn.tree import DecisionTreeClassifier
    except ImportError:
        return TinyDecisionTree().fit(samples, labels)

    return DecisionTreeClassifier(max_depth=3, random_state=7).fit(samples, labels)


def packet_class_for_length(pkt_len: int) -> dict[str, int | str]:
    if pkt_len <= 256:
        return PACKET_CLASSES[0]
    if pkt_len <= 500:
        return PACKET_CLASSES[1]
    return PACKET_CLASSES[2]


def ml_decision(model, route: Route) -> Decision:
    features = [[route.pkt_len, route.queue_depth, route.flow_count]]
    prediction = int(model.predict(features)[0])
    confidence = 1.0
    if hasattr(model, "predict_proba"):
        confidence = float(max(model.predict_proba(features)[0]))
    packet_class = packet_class_for_length(route.pkt_len)
    return Decision(
        route=route,
        packet_class=int(packet_class["id"]),
        packet_class_name=str(packet_class["name"]),
        action="DROP" if prediction else "FORWARD",
        confidence=confidence,
    )


def build_routes(h1_pkt_len: int = 128, h2_pkt_len: int = 128, queue_depth: int = 2) -> list[Route]:
    routes = []
    for route in DEMO_ROUTES:
        pkt_len = h1_pkt_len if route["port"] == 1 else h2_pkt_len
        routes.append(
            Route(
                prefix=route["prefix"],
                port=route["port"],
                src_mac=route["src_mac"],
                dst_mac=route["dst_mac"],
                pkt_len=pkt_len,
                queue_depth=queue_depth,
                flow_count=route["flow_count"],
            )
        )
    return routes


def build_decisions(
    h1_pkt_len: int = 128,
    h2_pkt_len: int = 128,
    queue_depth: int = 2,
    use_ml: bool = True,
) -> list[Decision]:
    routes = build_routes(h1_pkt_len=h1_pkt_len, h2_pkt_len=h2_pkt_len, queue_depth=queue_depth)
    if not use_ml:
        return [
            Decision(
                route=route,
                packet_class=int(packet_class_for_length(route.pkt_len)["id"]),
                packet_class_name=str(packet_class_for_length(route.pkt_len)["name"]),
                action="FORWARD",
                confidence=1.0,
            )
            for route in routes
        ]

    model = train_ml_model()
    return [ml_decision(model, route) for route in routes]


def build_policy_commands(decisions: list[Decision]) -> list[str]:
    commands = ["table_set_default ml_policy drop"]
    for decision in decisions:
        route = decision.route
        for packet_class in PACKET_CLASSES:
            action = "allow_route"
            if (
                decision.action == "DROP"
                and int(packet_class["id"]) == decision.packet_class
            ):
                action = "drop"
            commands.append(
                "table_add ml_policy {action} {packet_class} {prefix} =>".format(
                    action=action,
                    packet_class=packet_class["id"],
                    prefix=route.prefix,
                )
            )
    return commands


def build_route_commands(routes: list[Route]) -> list[str]:
    commands = ["table_set_default ipv4_lpm drop"]
    for route in routes:
        commands.append(
            "table_add ipv4_lpm ipv4_forward {prefix} => {port} {src_mac} {dst_mac}".format(
                prefix=route.prefix,
                port=route.port,
                src_mac=route.src_mac,
                dst_mac=route.dst_mac,
            )
        )
    return commands


def build_commands(
    h1_pkt_len: int = 128,
    h2_pkt_len: int = 128,
    queue_depth: int = 2,
    use_ml: bool = True,
) -> list[str]:
    decisions = build_decisions(
        h1_pkt_len=h1_pkt_len,
        h2_pkt_len=h2_pkt_len,
        queue_depth=queue_depth,
        use_ml=use_ml,
    )
    routes = [decision.route for decision in decisions]
    commands = []
    commands.extend(build_policy_commands(decisions))
    commands.extend(build_route_commands(routes))
    return commands


def render_decision_report(decisions: list[Decision]) -> str:
    lines = ["ML controller decisions:"]
    for decision in decisions:
        route = decision.route
        lines.append(
            "  {prefix}: pkt_len={pkt_len}, class={packet_class}, queue_depth={queue_depth}, "
            "flows={flow_count} -> {action} (confidence={confidence:.2f})".format(
                prefix=route.prefix,
                pkt_len=route.pkt_len,
                packet_class=decision.packet_class_name,
                queue_depth=route.queue_depth,
                flow_count=route.flow_count,
                action=decision.action,
                confidence=decision.confidence,
            )
        )
    return "\n".join(lines) + "\n"


def install_rules(
    thrift_port: int,
    cli_path: str = "simple_switch_CLI",
    h1_pkt_len: int = 128,
    h2_pkt_len: int = 128,
    queue_depth: int = 2,
    use_ml: bool = True,
) -> subprocess.CompletedProcess[str]:
    commands = "\n".join(
        build_commands(
            h1_pkt_len=h1_pkt_len,
            h2_pkt_len=h2_pkt_len,
            queue_depth=queue_depth,
            use_ml=use_ml,
        )
    ) + "\n"
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
    parser.add_argument("--no-ml", action="store_true", help="Disable ML and install static forward routes.")
    parser.add_argument("--h1-pkt-len", type=int, default=128, help="Packet length feature for h1's prefix.")
    parser.add_argument("--h2-pkt-len", type=int, default=128, help="Packet length feature for h2's prefix.")
    parser.add_argument("--queue-depth", type=int, default=2, help="Queue-depth feature used by the ML model.")
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

    use_ml = not args.no_ml
    decisions = build_decisions(
        h1_pkt_len=args.h1_pkt_len,
        h2_pkt_len=args.h2_pkt_len,
        queue_depth=args.queue_depth,
        use_ml=use_ml,
    )
    commands = build_commands(
        h1_pkt_len=args.h1_pkt_len,
        h2_pkt_len=args.h2_pkt_len,
        queue_depth=args.queue_depth,
        use_ml=use_ml,
    )
    rendered = "\n".join(commands) + "\n"

    if args.write_commands:
        args.write_commands.write_text(rendered, encoding="ascii")

    print(render_decision_report(decisions), end="")
    print("BMv2 CLI commands:")
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
        result = install_rules(
            args.thrift_port,
            args.cli_path,
            h1_pkt_len=args.h1_pkt_len,
            h2_pkt_len=args.h2_pkt_len,
            queue_depth=args.queue_depth,
            use_ml=use_ml,
        )
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

#!/usr/bin/env python3
"""Generate the updated ATN project PDF with ML results, graph, and architecture."""

from __future__ import annotations

import textwrap
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
PROJECT = Path(__file__).resolve().parent
SCREENSHOT = Path(
    r"C:\Users\MEHTAB SINGH\Pictures\Screenshots\Screenshot 2026-04-25 100754.png"
)
OUTPUT = ROOT / "ATN_updated_report.pdf"

PAGE_SIZE = (8.27, 11.69)  # A4 portrait in inches
BLUE = "#2457C5"
GREEN = "#1E8A5A"
RED = "#C33B3B"
DARK = "#1F2937"
LIGHT = "#EEF2F7"
MUTED = "#6B7280"


def add_page_number(fig: plt.Figure, page: int) -> None:
    fig.text(0.5, 0.025, f"Updated ATN Mini Project Report | Page {page}", ha="center", fontsize=8, color=MUTED)


def add_wrapped_text(
    fig: plt.Figure,
    text: str,
    x: float,
    y: float,
    width: int = 88,
    fontsize: int = 10,
    line_height: float = 0.028,
    color: str = DARK,
) -> float:
    for paragraph in text.split("\n"):
        if not paragraph.strip():
            y -= line_height
            continue
        for line in textwrap.wrap(paragraph, width=width):
            fig.text(x, y, line, fontsize=fontsize, color=color, va="top")
            y -= line_height
    return y


def save_title_page(pdf: PdfPages, page: int) -> int:
    fig = plt.figure(figsize=PAGE_SIZE)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.axis("off")
    ax.add_patch(plt.Rectangle((0, 0.78), 1, 0.22, color=BLUE, transform=ax.transAxes))
    fig.text(0.08, 0.91, "Updated ATN Project Report", fontsize=28, weight="bold", color="white")
    fig.text(
        0.08,
        0.855,
        "P4 + BMv2 + Mininet with ML-Based Control Plane Decisions",
        fontsize=14,
        color="white",
    )
    fig.text(0.08, 0.805, "Generated: 25 April 2026", fontsize=10, color="#DDE7FF")

    y = 0.70
    fig.text(0.08, y, "Project Update", fontsize=17, weight="bold", color=DARK)
    y -= 0.055
    summary = (
        "This updated report documents the latest implementation of the ATN mini project. "
        "The P4 switch remains responsible for high-speed packet processing, while the Python "
        "controller trains the ML decision logic. The controller predicts whether each route "
        "and packet-size class should be FORWARD or DROP, then installs the distilled policy "
        "into the BMv2 ml_policy table before normal ipv4_lpm routing."
    )
    y = add_wrapped_text(fig, summary, 0.08, y, width=92, fontsize=11, line_height=0.032)

    y -= 0.035
    fig.text(0.08, y, "Key Additions in This Version", fontsize=15, weight="bold", color=DARK)
    y -= 0.045
    bullets = [
        "ML controller decisions are printed during execution.",
        "The new result screenshot shows successful compilation, switch startup, rule installation, ping, and iperf3.",
        "A result graph summarizes RTT and throughput measurements from the latest run.",
        "A system architecture diagram clarifies the ART-style split between ML generation and switch enforcement.",
    ]
    for bullet in bullets:
        fig.text(0.105, y, f"- {bullet}", fontsize=10.5, color=DARK, va="top")
        y -= 0.035

    y -= 0.025
    fig.text(0.08, y, "Verified Results", fontsize=15, weight="bold", color=DARK)
    y -= 0.045
    verified = (
        "Ping test: 3 transmitted, 3 received, 0% packet loss, average RTT 0.877 ms.\n"
        "iperf3 sender throughput: 51.7 Mbit/s over 3 seconds.\n"
        "iperf3 receiver throughput: 43.7 Mbit/s over 3.07 seconds.\n"
        "ML default decision: both demo prefixes are forwarded with confidence 0.90."
    )
    add_wrapped_text(fig, verified, 0.08, y, width=92, fontsize=10.5, line_height=0.032)
    add_page_number(fig, page)
    pdf.savefig(fig)
    plt.close(fig)
    return page + 1


def box(ax, xy, wh, label, color=LIGHT, edge=BLUE, fontsize=10):
    x, y = xy
    w, h = wh
    rect = plt.Rectangle((x, y), w, h, facecolor=color, edgecolor=edge, linewidth=1.6)
    ax.add_patch(rect)
    ax.text(x + w / 2, y + h / 2, label, ha="center", va="center", fontsize=fontsize, color=DARK, weight="bold")


def arrow(ax, start, end, label=None, color=DARK):
    ax.annotate("", xy=end, xytext=start, arrowprops=dict(arrowstyle="->", lw=1.6, color=color))
    if label:
        ax.text((start[0] + end[0]) / 2, (start[1] + end[1]) / 2 + 0.03, label, ha="center", fontsize=8.5, color=color)


def save_architecture_page(pdf: PdfPages, page: int) -> int:
    fig = plt.figure(figsize=PAGE_SIZE)
    fig.text(0.08, 0.94, "System Architecture", fontsize=22, weight="bold", color=DARK)
    fig.text(
        0.08,
        0.905,
        "ML is placed in the Python control plane. P4 executes the installed table rules.",
        fontsize=10.5,
        color=MUTED,
    )

    ax = fig.add_axes([0.08, 0.27, 0.84, 0.56])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.add_patch(plt.Rectangle((0.03, 0.08), 0.94, 0.38, facecolor="#F8FAFC", edgecolor="#CBD5E1", linewidth=1.2))
    ax.text(0.05, 0.42, "Data Plane", fontsize=11, weight="bold", color=BLUE)
    ax.add_patch(plt.Rectangle((0.03, 0.55), 0.94, 0.36, facecolor="#F7FFF9", edgecolor="#B7DEC8", linewidth=1.2))
    ax.text(0.05, 0.87, "Control Plane", fontsize=11, weight="bold", color=GREEN)

    box(ax, (0.08, 0.20), (0.16, 0.12), "Host h1\n10.0.1.10", color="#FFFFFF")
    box(ax, (0.42, 0.18), (0.18, 0.16), "BMv2 P4 Switch\nml_policy + ipv4_lpm", color="#EAF1FF")
    box(ax, (0.76, 0.20), (0.16, 0.12), "Host h2\n10.0.2.10", color="#FFFFFF")
    box(ax, (0.12, 0.65), (0.22, 0.13), "Python Controller\ncontroller.py", color="#EBFFF1", edge=GREEN)
    box(ax, (0.42, 0.65), (0.18, 0.13), "Decision Tree\nML Model", color="#EBFFF1", edge=GREEN)
    box(ax, (0.70, 0.65), (0.22, 0.13), "BMv2 Thrift CLI\nRule Install", color="#EBFFF1", edge=GREEN)

    arrow(ax, (0.24, 0.26), (0.42, 0.26), "packet")
    arrow(ax, (0.60, 0.26), (0.76, 0.26), "forward/drop")
    arrow(ax, (0.34, 0.715), (0.42, 0.715), "features")
    arrow(ax, (0.60, 0.715), (0.70, 0.715), "decision")
    arrow(ax, (0.81, 0.65), (0.54, 0.34), "table_add", color=GREEN)
    arrow(ax, (0.50, 0.34), (0.50, 0.65), "stats/demo metrics", color=GREEN)

    y = 0.20
    fig.text(0.08, y, "Decision Flow", fontsize=15, weight="bold", color=DARK)
    y -= 0.04
    flow = (
        "1. Packets enter the BMv2 switch and are classified into small, medium, or large packet classes.\n"
        "2. The Python controller trains a small decision-tree classifier using packet length, queue depth, and flow count.\n"
        "3. The ML model predicts FORWARD or DROP for each prefix.\n"
        "4. The controller installs the distilled policy in ml_policy, then allowed packets continue to ipv4_lpm routing."
    )
    add_wrapped_text(fig, flow, 0.08, y, width=92, fontsize=10, line_height=0.029)
    add_page_number(fig, page)
    pdf.savefig(fig)
    plt.close(fig)
    return page + 1


def save_ml_logic_page(pdf: PdfPages, page: int) -> int:
    fig = plt.figure(figsize=PAGE_SIZE)
    fig.text(0.08, 0.94, "ML Controller Logic", fontsize=22, weight="bold", color=DARK)
    fig.text(0.08, 0.905, "The controller trains ML; the switch enforces the distilled decision tree as table rules.", fontsize=10.5, color=MUTED)

    y = 0.84
    text = (
        "The updated controller trains a compact decision-tree classifier. In a full ART-style system, these "
        "features would come from switch telemetry and network measurements. In this mini-project, they are "
        "provided as reproducible demo inputs so the forwarding policy can be tested deterministically."
    )
    y = add_wrapped_text(fig, text, 0.08, y, width=92, fontsize=10.5, line_height=0.032)

    y -= 0.02
    fig.text(0.08, y, "Input Features", fontsize=14, weight="bold", color=DARK)
    y -= 0.04
    for item in ["Packet length", "Queue depth", "Flow count"]:
        fig.text(0.11, y, f"- {item}", fontsize=10.5, color=DARK)
        y -= 0.033

    y -= 0.02
    fig.text(0.08, y, "Default ML Output", fontsize=14, weight="bold", color=DARK)
    y -= 0.04
    code = (
        "10.0.1.0/24: pkt_len=128, class=small, queue_depth=2, flows=1 -> FORWARD (confidence=0.90)\n"
        "10.0.2.0/24: pkt_len=128, class=small, queue_depth=2, flows=1 -> FORWARD (confidence=0.90)"
    )
    fig.text(0.10, y, code, family="monospace", fontsize=9.4, color=DARK, va="top")

    y -= 0.11
    fig.text(0.08, y, "Drop Demonstration", fontsize=14, weight="bold", color=DARK)
    y -= 0.04
    code = (
        "Command: python3 controller.py --dry-run --h2-pkt-len 800\n"
        "10.0.2.0/24: pkt_len=800, class=large, queue_depth=2, flows=1 -> DROP (confidence=0.90)\n"
        "Installed policy rule: table_add ml_policy drop 2 10.0.2.0/24 =>"
    )
    fig.text(0.10, y, code, family="monospace", fontsize=9.4, color=DARK, va="top")

    y -= 0.16
    conclusion = (
        "This is the important viva point: ML is not inside P4. ML is implemented in the control plane. "
        "The P4 switch applies the controller's decision through table entries."
    )
    add_wrapped_text(fig, conclusion, 0.08, y, width=92, fontsize=11, line_height=0.032, color=BLUE)
    add_page_number(fig, page)
    pdf.savefig(fig)
    plt.close(fig)
    return page + 1


def save_screenshot_page(pdf: PdfPages, page: int) -> int:
    fig = plt.figure(figsize=PAGE_SIZE)
    fig.text(0.08, 0.95, "New Result Screenshot", fontsize=22, weight="bold", color=DARK)
    fig.text(
        0.08,
        0.918,
        "Latest run output showing compilation, Mininet startup, ML decisions, table entries, ping, and iperf3.",
        fontsize=10,
        color=MUTED,
    )
    image = Image.open(SCREENSHOT).convert("RGB")
    ax = fig.add_axes([0.06, 0.08, 0.88, 0.80])
    ax.imshow(image)
    ax.axis("off")
    add_page_number(fig, page)
    pdf.savefig(fig)
    plt.close(fig)
    return page + 1


def save_results_graph_page(pdf: PdfPages, page: int) -> int:
    fig = plt.figure(figsize=PAGE_SIZE)
    fig.text(0.08, 0.95, "Result Graphs", fontsize=22, weight="bold", color=DARK)
    fig.text(0.08, 0.918, "Metrics extracted from the latest successful test run.", fontsize=10, color=MUTED)

    ping_ms = [1.05, 0.803, 0.780]
    throughput = [54.5, 53.5, 47.1]
    labels = ["0-1s", "1-2s", "2-3s"]

    ax1 = fig.add_axes([0.12, 0.58, 0.76, 0.25])
    ax1.plot([1, 2, 3], ping_ms, marker="o", color=BLUE, linewidth=2)
    ax1.set_title("Ping RTT per ICMP Reply", fontsize=12, weight="bold")
    ax1.set_xlabel("ICMP sequence")
    ax1.set_ylabel("RTT (ms)")
    ax1.set_xticks([1, 2, 3])
    ax1.grid(True, alpha=0.25)
    ax1.text(2.1, max(ping_ms) - 0.04, "Average RTT: 0.877 ms", fontsize=9, color=BLUE)

    ax2 = fig.add_axes([0.12, 0.23, 0.76, 0.25])
    bars = ax2.bar(labels, throughput, color=[GREEN, GREEN, "#7AB58D"])
    ax2.axhline(51.7, color=RED, linestyle="--", linewidth=1.5, label="Sender avg: 51.7 Mbit/s")
    ax2.axhline(43.7, color=BLUE, linestyle="--", linewidth=1.5, label="Receiver avg: 43.7 Mbit/s")
    ax2.set_title("iperf3 Throughput by Interval", fontsize=12, weight="bold")
    ax2.set_xlabel("Interval")
    ax2.set_ylabel("Mbit/s")
    ax2.set_ylim(0, 65)
    ax2.grid(axis="y", alpha=0.25)
    ax2.legend(fontsize=8, loc="upper right")
    for bar, value in zip(bars, throughput):
        ax2.text(bar.get_x() + bar.get_width() / 2, value + 1, f"{value:.1f}", ha="center", fontsize=9)

    fig.text(
        0.12,
        0.135,
        "Observation: the P4/BMv2 forwarding path is functional, with 0% packet loss and stable throughput "
        "during the 3-second iperf3 run.",
        fontsize=10.5,
        color=DARK,
    )
    add_page_number(fig, page)
    pdf.savefig(fig)
    plt.close(fig)
    return page + 1


def save_conclusion_page(pdf: PdfPages, page: int) -> int:
    fig = plt.figure(figsize=PAGE_SIZE)
    fig.text(0.08, 0.94, "Conclusion", fontsize=22, weight="bold", color=DARK)
    y = 0.875
    text = (
        "The updated implementation now demonstrates a clearer ART-inspired split between the data plane "
        "and control plane. The P4 program parses packets, applies ipv4_lpm table rules, rewrites MAC "
        "addresses, decrements TTL, and recomputes checksums. The Python controller contains the ML logic, "
        "classifies route behavior as FORWARD or DROP, and installs the selected action into BMv2's ml_policy table."
    )
    y = add_wrapped_text(fig, text, 0.08, y, width=92, fontsize=11, line_height=0.034)

    y -= 0.04
    fig.text(0.08, y, "Final Verification Summary", fontsize=15, weight="bold", color=DARK)
    y -= 0.045
    final_points = [
        "P4 compilation completed successfully.",
        "BMv2 switch started with the compiled JSON program.",
        "ML controller printed route decisions and installed table entries.",
        "Ping from h1 to h2 completed with 0% packet loss.",
        "iperf3 completed successfully with sender throughput of 51.7 Mbit/s.",
    ]
    for point in final_points:
        fig.text(0.105, y, f"- {point}", fontsize=10.5, color=DARK, va="top")
        y -= 0.035

    y -= 0.04
    viva = (
        "Viva answer: ML training is implemented in the Python control plane. The distilled decision tree is enforced "
        "inside the P4 data plane through the ml_policy table, and allowed packets are routed by ipv4_lpm."
    )
    add_wrapped_text(fig, viva, 0.08, y, width=88, fontsize=12, line_height=0.038, color=BLUE)
    add_page_number(fig, page)
    pdf.savefig(fig)
    plt.close(fig)
    return page + 1


def main() -> int:
    if not SCREENSHOT.exists():
        raise FileNotFoundError(f"Missing screenshot: {SCREENSHOT}")

    page = 1
    with PdfPages(OUTPUT) as pdf:
        page = save_title_page(pdf, page)
        page = save_architecture_page(pdf, page)
        page = save_ml_logic_page(pdf, page)
        page = save_screenshot_page(pdf, page)
        page = save_results_graph_page(pdf, page)
        save_conclusion_page(pdf, page)

    print(OUTPUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

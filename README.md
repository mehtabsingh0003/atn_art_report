# P4 Mini Project

This mini project implements a small IPv4 router in P4 and runs it on BMv2 with Mininet.

## What It Does

- parses Ethernet and IPv4 packets
- performs an IPv4 LPM lookup in ingress
- uses a Python ML controller to generate ART-style forward/drop policy entries
- enforces the distilled ML policy in a P4 `ml_policy` table before routing
- forwards packets between two subnets
- rewrites source and destination MAC addresses
- decrements IPv4 TTL
- recomputes the IPv4 header checksum
- drops unmatched traffic by default

The demo topology is:

- `h1` on `10.0.1.10/24`
- `h2` on `10.0.2.10/24`
- `s1` as the BMv2 P4 switch/router

## Files

- `basic_ml.p4`: P4 program
- `topology.py`: Mininet topology launcher
- `controller.py`: runs a small ML classifier and installs BMv2 policy/routing entries over the thrift CLI
- `run.sh`: compile + run helper

## Prerequisites

- `p4c`
- `simple_switch`
- `simple_switch_CLI`
- `python3`
- `Mininet`
- `iperf3`
- the BMv2 Mininet helper `p4_mininet.py`

## Run

Interactive demo:

```bash
cd /mnt/e/ATN/p4-mini-project
bash run.sh
```

Run a smoke test and exit:

```bash
cd /mnt/e/ATN/p4-mini-project
bash run.sh test
```

## Useful Mininet Commands

Inside the Mininet CLI:

```bash
h1 ping -c 3 10.0.2.10
h2 tcpdump -enn -i eth0
h1 traceroute -n 10.0.2.10
```

## ML Controller

The heavy ML logic is in `controller.py`, where a small decision-tree classifier uses traffic features such as packet length and queue depth to decide whether each prefix should be forwarded or dropped. The controller then distills that decision into switch rules for the P4 `ml_policy` table.

The data plane enforces the policy in two stages:

1. `ml_policy`: checks the packet-size class and destination prefix, then allows or drops the packet.
2. `ipv4_lpm`: forwards allowed packets to the correct output port.

Print the ML decisions and generated BMv2 commands:

```bash
python3 controller.py --dry-run
```

Simulate a large packet/flow metric for `h2` and make the controller install a drop rule:

```bash
python3 controller.py --dry-run --h2-pkt-len 800
```

Run the full topology with the same ART-style policy input:

```bash
bash run.sh test --h2-pkt-len 800
```

With the default demo metrics, the controller inserts two forward LPM routes:

- `10.0.1.0/24 -> port 1`
- `10.0.2.0/24 -> port 2`

Each route also sets the outgoing source MAC and destination MAC so the switch behaves like a small router between the two subnets.
# atn_art_report

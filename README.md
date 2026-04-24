# P4 Mini Project

This mini project implements a small IPv4 router in P4 and runs it on BMv2 with Mininet.

## What It Does

- parses Ethernet and IPv4 packets
- performs an IPv4 LPM lookup in ingress
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
- `controller.py`: installs BMv2 table entries over the thrift CLI
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

## Installed Demo Routes

The controller inserts two LPM routes:

- `10.0.1.0/24 -> port 1`
- `10.0.2.0/24 -> port 2`

Each route also sets the outgoing source MAC and destination MAC so the switch behaves like a small router between the two subnets.
# atn_art_report

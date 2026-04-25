# Consolidated Report
## Simplified Reproduction of "Routing with ART: Adaptive Routing for P4 Switches With In-Network Decision Trees"

### 1. Introduction

This report presents a simplified implementation inspired by the paper **"Routing with ART: Adaptive Routing for P4 Switches With In-Network Decision Trees"**, published at IEEE GLOBECOM 2024. The paper addresses a key challenge in programmable networking: how to bring machine-learning-driven routing into the data plane of P4 switches, even though switches have limited computation, restricted control flow, and strict per-packet processing constraints.

The central motivation of the paper is that traditional routing protocols are often too static to respond quickly to changing traffic conditions, while modern learning-based routing approaches are often too complex to execute directly inside a P4-programmable switch. ART solves this gap by placing the heavy learning process in the control plane and distilling the learned behavior into a lightweight decision structure that can be enforced in the switch data plane.

For this assignment, the implemented system is a **mini-project version** of the ART idea. Instead of implementing the full DRL-to-decision-tree pipeline from the paper, the project focuses on the most important switch-side part: a correct P4 forwarding program running on BMv2 with Mininet, plus a controller script that installs routing entries. This provides a working and reproducible programmable routing prototype that demonstrates understanding of the paper and practical use of P4.

### 2. Selected Paper and Its Core Idea

The selected paper proposes **ART (Adaptive Routing with Trees)**, a routing framework for P4 switches. The paper starts from the observation that machine-learning-based routing can react more intelligently to congestion and changing network conditions than conventional routing protocols, but full learning models such as Deep Reinforcement Learning (DRL) are too large and computationally expensive for direct execution inside switch pipelines.

The paper's core idea is to separate the learning and execution stages:

- A DRL model is trained in the control plane using network measurements and packet-related information.
- The learned policy is then distilled into a **Decision Tree (DT)**.
- The distilled tree is translated into simple forwarding logic or switch rules that can fit the constraints of a P4 switch.

This approach allows the system to keep the adaptive behavior of machine learning while still respecting the hardware and language limitations of the data plane.

The paper architecture includes three major elements:

- **P4 switches**, which collect packet and traffic information and enforce forwarding decisions.
- **A controller**, which communicates with switches and updates rules using P4Runtime.
- **A DRL/DT module**, which learns the routing policy and converts it into a switch-friendly decision structure.

The paper evaluates ART on a Mininet-based data-center environment and compares it with OSPF, QR-SDN, and an in-network RL baseline. According to the paper, ART improves metrics such as RTT, throughput, and packet loss by enabling more adaptive routing behavior.

### 3. Implemented Functionality and Design Choices

The implemented project is a **simplified ART-inspired programmable routing system**. It does not implement the full DRL training, decision-tree distillation, or P4Runtime-based adaptive control loop from the paper. Instead, it implements a small but functional programmable router using:

- a P4 program for packet parsing and forwarding,
- a Mininet topology,
- a Python ML controller script for selecting and installing forwarding or drop entries,
- and a shell script to compile and run the complete setup.

This design was chosen for three reasons.

First, a correct switch pipeline is the foundation of the full ART architecture. Before adaptive learning can be added, the switch must already be able to parse packets, perform routing lookups, rewrite headers, and forward traffic correctly.

Second, a small two-host, one-switch topology is easier to debug and reproduce than a larger multi-switch topology. Since this is a mini-project, correctness and reproducibility were prioritized over scale.

Third, the P4 program was designed to stay close to router behavior rather than just simple switching. Therefore, the implementation includes TTL decrement and checksum recomputation, which are essential router functions.

The resulting mini-project contains the following components:

- `basic_ml.p4`: the P4 data-plane program.
- `topology.py`: a Mininet topology with two hosts and one BMv2 switch.
- `controller.py`: a Python script that installs IPv4 LPM forwarding entries through `simple_switch_CLI`.
- `run.sh`: a helper script that compiles the P4 program and launches the topology.

The topology used in the implementation is:

- `h1` in subnet `10.0.1.0/24`
- `h2` in subnet `10.0.2.0/24`
- `s1` as a BMv2 software switch acting as a router between the two subnets

This topology demonstrates inter-subnet forwarding, which is more appropriate for a routing project than placing both hosts in the same subnet.

### 4. Explanation of the P4 Program

The P4 program is written for the **BMv2 `v1model` architecture** and implements a standard router-style packet-processing pipeline.

#### 4.1 Headers and Metadata

The program defines two headers:

- `ethernet_t`
- `ipv4_t`

These are grouped in a `headers` struct. A `metadata` struct is also defined, although it is currently empty. This empty metadata struct is still useful because it creates a clean extension point for future work, such as adding congestion indicators, route scores, or decision-tree outputs.

#### 4.2 Parser

The parser begins by extracting the Ethernet header. It then checks the EtherType field:

- if the packet is IPv4 (`0x0800`), it extracts the IPv4 header,
- otherwise, it accepts the packet without further parsing.

This parser design is efficient and realistic because it only parses IPv4 packets in detail and avoids unnecessary work for unsupported packet types.

#### 4.3 Verify Checksum Control

The `MyVerifyChecksum` control is currently empty. This is acceptable for the mini-project because the main objective is forwarding and recomputing the checksum after modifying the packet. The architecture still includes the block because `v1model` expects a checksum verification stage in the complete switch package.

#### 4.4 Ingress Pipeline

The ingress pipeline contains the main forwarding logic. Two actions are defined:

- `drop()`: marks the packet to be dropped using `mark_to_drop(standard_metadata)`.
- `ipv4_forward(port, srcMac, dstMac)`: selects the egress port, rewrites Ethernet source and destination MAC addresses, and decrements the IPv4 TTL.

The ingress pipeline now contains two important tables. The first table is `ml_policy`, which acts as the switch-resident distilled decision-tree policy. The P4 program classifies packets into size classes using the IPv4 total length:

- class `0`: small packets up to 256 bytes,
- class `1`: medium packets from 257 to 500 bytes,
- class `2`: large packets above 500 bytes.

The `ml_policy` table matches on the packet-size class and destination prefix. Its actions either allow the packet to continue to routing or drop it immediately. This is the closest practical implementation of the ART paper's in-network decision-tree idea in this mini-project.

The second table is `ipv4_lpm`, which performs a longest-prefix-match lookup on `hdr.ipv4.dstAddr`. This is the core routing table of the switch. The table supports:

- `ipv4_forward`
- `drop`
- `NoAction`

The default action is `drop()`, which is a safe design choice because it prevents accidental forwarding of packets that do not match any route.

In the `apply` block, the switch checks if the IPv4 header is valid. If the packet is IPv4, the packet-size class is computed, `ml_policy` is applied first, and only allowed packets continue to `ipv4_lpm`. If the packet is not IPv4, it is dropped. This makes the behavior deterministic and closer to ART's design: learned policy first, forwarding table second.

#### 4.5 Egress Pipeline

The `MyEgress` control is empty in this implementation. All forwarding decisions happen during ingress, so egress processing is not required for the current functionality. In future extensions, the egress stage could be used for queue-based decisions, telemetry marking, or policy enforcement.

#### 4.6 Checksum Recomputation

Since the ingress pipeline decrements the IPv4 TTL, the checksum must be updated. This is handled in `MyComputeChecksum`, which recomputes the IPv4 checksum using `update_checksum(..., HashAlgorithm.csum16)`.

This is an important part of the program because real routers update the checksum whenever header fields such as TTL change. Including this stage makes the implementation more realistic and protocol-correct.

#### 4.7 Deparser

The deparser emits the Ethernet header followed by the IPv4 header. Since the project only processes these headers, the deparser remains compact and easy to verify.

#### 4.8 Switch Instantiation

The program uses the full `V1Switch` package:

- parser
- verify checksum
- ingress
- egress
- compute checksum
- deparser

This is important because the latest `v1model` definition expects all these blocks during package instantiation.

### 5. Controller and ML Logic

The mini-project includes a Python controller script, `controller.py`, which installs entries into the BMv2 switch at runtime. The important architectural point is that training and policy generation are implemented in the control plane. The P4 data plane enforces the distilled decision-tree policy through match-action rules in `ml_policy`.

The controller trains a small decision-tree classifier using traffic features:

- packet length,
- queue depth,
- flow count.

The classifier predicts `FORWARD` or `DROP` for each destination prefix and packet-size class. The controller translates the prediction into `ml_policy` entries. Allowed packets then use `ipv4_lpm` to select the output port. This mirrors ART's teacher-student idea in simplified form: the model is trained in Python, then the resulting decision policy is pushed into the switch as table rules.

With the default demo metrics, the controller forwards both demo prefixes:

- `10.0.1.0/24 -> port 1`
- `10.0.2.0/24 -> port 2`

For each forwarded route, the controller also provides:

- the source MAC address that the switch should use on the outgoing interface,
- the destination MAC address of the host connected to that subnet.

This allows the BMv2 switch to behave like a small IPv4 router between the two subnets.

The controller interacts with the switch using `simple_switch_CLI` over the thrift interface. Although the ART paper uses richer controller-switch interaction through P4Runtime and digests, this project now demonstrates the same separation of responsibility: ML-based policy selection in Python and fast rule execution in P4/BMv2.

### 6. Experimental Setup

The paper evaluates ART in a larger data-center topology, but the implemented mini-project uses a reduced and reproducible environment.

#### 6.1 Topology

The topology consists of:

- 1 BMv2 P4 switch: `s1`
- 2 hosts: `h1` and `h2`

IP and MAC assignments:

- `h1`: `10.0.1.10/24`, MAC `00:04:00:00:01:10`
- `h2`: `10.0.2.10/24`, MAC `00:04:00:00:02:10`
- gateway for `h1`: `10.0.1.1`, MAC `00:aa:bb:00:00:01`
- gateway for `h2`: `10.0.2.1`, MAC `00:aa:bb:00:00:02`

Each host is configured with a default route through the switch-facing gateway address for its subnet.

#### 6.2 Software and Environment

The implementation was executed in a **WSL Ubuntu environment** with the following tools:

- `p4c`
- `simple_switch`
- `simple_switch_CLI`
- `Mininet`
- `/usr/bin/python3`
- `iperf3`

The P4 target is:

- BMv2 software switch
- `v1model` architecture

The project was executed from:

- `/mnt/e/ATN/p4-mini-project` in WSL

All commands in the reproducibility section are intended to be run inside the Ubuntu/WSL shell. They should not be executed from Git Bash on Windows. In addition, Mininet commands such as `pingall` are only available after the topology is running and the user is inside the `mininet>` prompt.

#### 6.3 Traffic Generation and Testing

Two kinds of tests were used:

- `ping` for connectivity and functional routing verification
- `iperf3` for a simple throughput check

The topology launcher includes an optional smoke test that:

- pings `h2` from `h1`
- starts an `iperf3` server on `h2`
- runs an `iperf3` client from `h1`

### 7. Reproducibility Section

This section provides complete steps to reproduce the mini-project.

#### 7.1 Source Code

The source code to submit with the report is the folder:

- `p4-mini-project/`

It includes:

- `basic_ml.p4`
- `topology.py`
- `controller.py`
- `run.sh`
- `README.md`
- `submission_report.md`

If a repository is used later, the same project folder can be uploaded to GitHub and the repository link can be inserted here.

#### 7.2 Steps to Compile and Run the P4 Program

Open Ubuntu/WSL and run:

```bash
cd /mnt/e/ATN/p4-mini-project
sudo mn -c
bash run.sh
```

This script performs two tasks:

- compiles `basic_ml.p4` into BMv2 JSON using `p4c`
- launches Mininet and the BMv2 switch, then installs routing entries
- uses `/usr/bin/python3` so the Mininet package is available even if a virtual environment is active

To run the project together with the automated verification test:

```bash
cd /mnt/e/ATN/p4-mini-project
sudo mn -c
bash run.sh test
```

To run the topology while installing a policy that drops the large-packet class for `h2`:

```bash
cd /mnt/e/ATN/p4-mini-project
bash run.sh test --h2-pkt-len 800
```

This is the recommended command for the evaluator because it performs compilation, switch startup, rule installation, ping testing, and a short `iperf3` throughput test in one run.

#### 7.3 Manual Compilation Command

If manual compilation is preferred, use:

```bash
cd /mnt/e/ATN/p4-mini-project
sudo mn -c
mkdir -p build
p4c --target bmv2 --arch v1model basic_ml.p4 -o build
```

This creates:

- `build/basic_ml.json`
- `build/basic_ml.p4i`

To start the topology directly after compilation:

```bash
cd /mnt/e/ATN/p4-mini-project
sudo /usr/bin/python3 topology.py
```

To start the topology and immediately run the built-in verification test:

```bash
cd /mnt/e/ATN/p4-mini-project
sudo /usr/bin/python3 topology.py --test
```

#### 7.4 Topology Setup

The topology is created by `topology.py` using Mininet and the BMv2 helper classes from the installed `p4_mininet.py` module. It creates:

- host `h1`
- host `h2`
- switch `s1`
- links `h1-s1` and `h2-s1`

The switch is launched with the generated BMv2 JSON file and a thrift port used by the controller script.

When the topology is running successfully, the user should see a `mininet>` prompt. This prompt indicates that the virtual network is live and ready for interactive testing.

#### 7.5 Controller / Rule Installation

The rule installation logic is implemented in `controller.py`. To print the commands without pushing them to the switch:

```bash
python3 controller.py --dry-run
```

To demonstrate a drop decision from the ML controller, a larger packet-length feature can be supplied:

```bash
python3 controller.py --dry-run --h2-pkt-len 800
```

If `controller.py` is run without the topology already running, it will fail because no BMv2 switch is listening on thrift port `9090`. Therefore, the correct order is:

1. start the topology with `bash run.sh`, `bash run.sh test`, or `sudo /usr/bin/python3 topology.py`
2. allow the switch to start on thrift port `9090`
3. then run the controller, or let `topology.py` call it automatically

With the default metrics, the generated ML decisions and commands are:

```text
ML controller decisions:
  10.0.1.0/24: pkt_len=128, class=small, queue_depth=2, flows=1 -> FORWARD (confidence=0.90)
  10.0.2.0/24: pkt_len=128, class=small, queue_depth=2, flows=1 -> FORWARD (confidence=0.90)
BMv2 CLI commands:
table_set_default ml_policy drop
table_add ml_policy allow_route 0 10.0.1.0/24 =>
table_add ml_policy allow_route 1 10.0.1.0/24 =>
table_add ml_policy allow_route 2 10.0.1.0/24 =>
table_add ml_policy allow_route 0 10.0.2.0/24 =>
table_add ml_policy allow_route 1 10.0.2.0/24 =>
table_add ml_policy allow_route 2 10.0.2.0/24 =>
table_set_default ipv4_lpm drop
table_add ipv4_lpm ipv4_forward 10.0.1.0/24 => 1 00:aa:bb:00:00:01 00:04:00:00:01:10
table_add ipv4_lpm ipv4_forward 10.0.2.0/24 => 2 00:aa:bb:00:00:02 00:04:00:00:02:10
```

With `--h2-pkt-len 800`, the controller instead produces:

```text
ML controller decisions:
  10.0.1.0/24: pkt_len=128, class=small, queue_depth=2, flows=1 -> FORWARD (confidence=0.90)
  10.0.2.0/24: pkt_len=800, class=large, queue_depth=2, flows=1 -> DROP (confidence=0.90)
BMv2 CLI commands:
table_set_default ml_policy drop
table_add ml_policy allow_route 0 10.0.1.0/24 =>
table_add ml_policy allow_route 1 10.0.1.0/24 =>
table_add ml_policy allow_route 2 10.0.1.0/24 =>
table_add ml_policy allow_route 0 10.0.2.0/24 =>
table_add ml_policy allow_route 1 10.0.2.0/24 =>
table_add ml_policy drop 2 10.0.2.0/24 =>
table_set_default ipv4_lpm drop
table_add ipv4_lpm ipv4_forward 10.0.1.0/24 => 1 00:aa:bb:00:00:01 00:04:00:00:01:10
table_add ipv4_lpm ipv4_forward 10.0.2.0/24 => 2 00:aa:bb:00:00:02 00:04:00:00:02:10
```

#### 7.6 Commands Used for Traffic Generation and Testing

Inside the Mininet CLI, the following commands can be used:

```bash
pingall
h1 ping -c 3 10.0.2.10
h2 tcpdump -enn -i eth0
h1 traceroute -n 10.0.2.10
```

For throughput testing:

```bash
h2 iperf3 -s -1
h1 iperf3 -c 10.0.2.10 -t 3
```

These commands verify both correctness and basic data-path performance. The `pingall` command must be executed inside the `mininet>` CLI, not in a normal shell.

#### 7.7 Expected Outputs or Observations for Verification

The following observations are expected:

- the P4 program compiles successfully,
- the `build/` directory contains `basic_ml.json` and `basic_ml.p4i`,
- BMv2 loads the generated JSON program correctly,
- the controller successfully installs the `ml_policy` and `ipv4_lpm` entries,
- `h1` can ping `h2`,
- returned ICMP packets show `ttl=63`, indicating that the router decremented the TTL,
- `iperf3` completes successfully between the two hosts,
- unmatched traffic is dropped due to the default `drop()` action.

Typical successful output includes lines such as:

```text
P4 switch s1 has been started.
Entry has been added with handle 0
Entry has been added with handle 1
3 packets transmitted, 3 received, 0% packet loss
64 bytes from 10.0.2.10: icmp_seq=1 ttl=63 time=...
iperf Done.
```

During verified testing, the project produced successful ping responses and working `iperf3` transfers in the approximate range of **44-59 Mbit/s sender throughput** and **36-47 Mbit/s receiver throughput**, depending on the run. This confirms that the forwarding path is functioning correctly in the emulated environment.

It is also normal to observe some dropped packets in the BMv2 log during startup. This happens because the switch begins with a default `drop()` action before all routing entries are installed. As long as the final connectivity and throughput tests succeed, these early drops are not considered a failure.

### 8. Results and Discussion

The implemented mini-project successfully demonstrates the following:

- correct parsing of Ethernet and IPv4 packets,
- correct LPM-based forwarding in the ingress pipeline,
- proper rewrite of Layer 2 addresses for routed forwarding,
- TTL decrement,
- checksum recomputation,
- default drop behavior,
- runtime installation of forwarding rules.

This is an important result because it shows that the switch-side behavior required by ART can be implemented cleanly in P4 and tested on BMv2. The current project also includes a compact ML controller that selects forward or drop behavior and distills that behavior into the switch-resident `ml_policy` table. While it does not reproduce the full DRL training and P4Runtime pipeline of the paper, it now captures the essential control-plane/data-plane split and the decision-tree-in-switch enforcement idea on which ART depends.

The main limitation of the current implementation is that the ML features are supplied as demo inputs rather than collected from live switch telemetry through P4Runtime digests. As a result, this project should be described as a **simplified reproduction inspired by ART**, not as a full reproduction of the complete research system.

### 9. Conclusion

This project studied the paper **"Routing with ART: Adaptive Routing for P4 Switches With In-Network Decision Trees"** and implemented a compact programmable-routing prototype based on its data-plane goals. The paper's core contribution is the conversion of complex learning-based routing logic into a simple switch-executable form. The implemented mini-project reflects that direction by building a working BMv2 router in P4, connecting it to a Mininet topology, and controlling it through a Python-based rule installer.

The project successfully compiles, runs, and forwards traffic between two subnets. It also demonstrates ML-based control-plane decision making through `controller.py`, where the learned policy selects `FORWARD` or `DROP` before BMv2 table entries are installed. It therefore provides a reproducible and practical demonstration of programmable routing with P4, along with a solid foundation for future work such as live telemetry collection, P4Runtime/gRPC rule updates, richer topologies, or a controller that more closely matches the full ART architecture.

# All Commands Used In This Project

Run all commands below inside **Ubuntu/WSL**.

Project folder:

```bash
cd /mnt/e/ATN/p4-mini-project
```

## 0. Environment Setup From Scratch

These commands are useful if the evaluator needs to rebuild the toolchain in WSL/Ubuntu. They are not required every time once the environment is already prepared.

### 0.1 Update Ubuntu

```bash
sudo apt update && sudo apt upgrade -y
```

### 0.2 Install Base Dependencies

```bash
sudo apt install -y git build-essential cmake \
python3 python3-pip python3-venv \
libboost-all-dev libpcap-dev libssl-dev \
bison flex pkg-config
```

### 0.3 Create Python Virtual Environment

```bash
python3 -m venv ~/p4env
source ~/p4env/bin/activate
```

Optional Python packages mentioned for a broader paper-style setup:

```bash
pip install grpcio protobuf scikit-learn p4runtime-shell numpy
```

Note: the current mini-project does **not** depend on `p4runtime-shell` or `scikit-learn` at runtime.

### 0.4 Install Mininet
```bash
sudo apt install -y mininet
```
Quick Mininet check:
```bash
sudo mn --test pingall --switch user
```

### 0.5 Install BMv2 From Source

```bash
cd ~
git clone https://github.com/p4lang/behavioral-model.git
cd behavioral-model
mkdir build && cd build
cmake ..
make -j1
sudo make install
```

Verify:

```bash
simple_switch --version
```

### 0.6 Install p4c From Source

```bash
cd ~
git clone https://github.com/p4lang/p4c.git
cd p4c
mkdir build && cd build
cmake ..
make -j1
sudo make install
```

Verify:
```bash
p4c --version
```

### 0.7 Create Project Directory

```bash
cd ~
mkdir -p p4-ml-project
cd p4-ml-project
```

## 1. Clean Old Mininet State

```bash
sudo mn -c
```

## 2. Compile The P4 Program

```bash
cd /mnt/e/ATN/p4-mini-project
mkdir -p build
p4c --target bmv2 --arch v1model basic_ml.p4 -o build
```

Alternative generic BMv2 compile form:

```bash
p4c --target bmv2 --arch v1model basic_ml.p4 -o build
```

## 3. Check Compile Output
```bash
ls -l build
```

Expected files:

```text
build/basic_ml.json
build/basic_ml.p4i
```

Note: this mini-project uses BMv2 JSON output and does **not** rely on a generated `.p4info` file in its verified workflow.

## 4. Run Full Project Automatically

Smoke test mode:

```bash
cd /mnt/e/ATN/p4-mini-project
bash run.sh test
```

Interactive Mininet mode:

```bash
cd /mnt/e/ATN/p4-mini-project
bash run.sh
```

## 5. Run Topology Manually

Start topology only:

```bash
cd /mnt/e/ATN/p4-mini-project
sudo /usr/bin/python3 topology.py
```
Start topology with built-in test:

```bash
cd /mnt/e/ATN/p4-mini-project
sudo /usr/bin/python3 topology.py --test
```

## 6. Controller Commands

Print controller commands without connecting:

```bash
cd /mnt/e/ATN/p4-mini-project
python3 controller.py --dry-run
```

Install rules into a running BMv2 switch:

```bash
cd /mnt/e/ATN/p4-mini-project
python3 controller.py
```

Commands To Use Inside `mininet>`
After running `bash run.sh` or `sudo /usr/bin/python3 topology.py`, you will get a `mininet>` prompt.
Run all-host connectivity test:
```bash
pingall
```
Ping from `h1` to `h2`:
```bash
h1 ping -c 3 10.0.2.10
```
Watch packets at `h2`:
```bash
h2 tcpdump -enn -i eth0
```
Trace route from `h1` to `h2`:
```bash
h1 traceroute -n 10.0.2.10
```

## 8. Throughput Test Commands

Start `iperf3` server on `h2`:

```bash
h2 iperf3 -s -1
```

Run `iperf3` client from `h1`:

```bash
h1 iperf3 -c 10.0.2.10 -t 3
```

Alternative background server:

```bash
h2 iperf3 -s -1 &
h1 iperf3 -c 10.0.2.10 -t 3
```

## 9. BMv2 Table And Runtime Checks

Dump installed `ipv4_lpm` entries while the switch is running:

```bash
echo "table_dump ipv4_lpm" | simple_switch_CLI --thrift-port 9090
```

Check whether thrift port `9090` is listening:

```bash
sudo ss -ltnp | grep 9090
```

## 10. Log And Debug Commands

Read BMv2 switch log:

```bash
sudo cat /tmp/p4s.s1.log
```

Watch switch log live:

```bash
sudo tail -f /tmp/p4s.s1.log
```

Save full automatic run output to a file:

```bash
cd /mnt/e/ATN/p4-mini-project
bash run.sh test 2>&1 | tee run_output.txt
```

## 11. Source Files Included In This Project

List project files:

```bash
cd /mnt/e/ATN/p4-mini-project
ls -l
```

Main source files:

```text
basic_ml.p4
topology.py
controller.py
run.sh
README.md
submission_report.md
all_commands.md
```

## 12. Exit Commands

Exit Mininet:

```bash
exit
```

Clean Mininet after finishing:

```bash
sudo mn -c
```

## 13. Expected Successful Output Indicators

These lines indicate a correct run:

```text
P4 switch s1 has been started.
Entry has been added with handle 0
Entry has been added with handle 1
3 packets transmitted, 3 received, 0% packet loss
64 bytes from 10.0.2.10: icmp_seq=1 ttl=63
iperf Done.
```

## 14. Commands Not Used In This Mini-Project

The following commands belong to a different P4Runtime / `simple_switch_grpc` workflow and are **not** part of the verified implementation in this project:

```bash
simple_switch_grpc basic.json
```

```bash
p4c --target bmv2 --arch v1model --p4runtime-files basic_ml.p4info basic_ml.p4
```

This mini-project uses:

- `simple_switch`
- `simple_switch_CLI`
- thrift port `9090`
- static LPM rule installation through `controller.py`

It does **not** implement:

- `simple_switch_grpc`
- P4Runtime gRPC controller setup
- packet-size-based drop logic
- ML decision output such as `Packet size: 650 -> DROP`

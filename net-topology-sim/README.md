# Cisco Network Topology Builder & Simulator (Starter)

This is a **beginner‑friendly** starter project that solves the core parts of the Cisco Virtual Internship Networking problem:
- Builds a topology from router/switch config files
- Validates configs (duplicate IPs, MTU mismatches, VLAN mismatches, loops, missing devices)
- Estimates link load vs bandwidth and gives **load balancing recommendations**
- Simulates **Day‑1 discovery** (hello/ARP-ish) and simple **fault injection** (link down)
- Uses **multithreading** (each device = a thread) and **FIFO queues** for IPC
- Can **pause/resume** the simulation

> Tip: Open this folder in VS Code or any IDE.

## 1) Prerequisites
- Install Python 3.10+
- Open a terminal (Windows PowerShell or macOS/Linux shell)

## 2) Create and activate a virtual env (recommended)

**Windows (PowerShell):**
```powershell
cd "/mnt/data/net-topology-sim"
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

**macOS/Linux:**
```bash
cd "/mnt/data/net-topology-sim"
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 3) Project layout
```
net-topology-sim/
├─ conf/                     # Put your router/switch config files here
│  ├─ R1/config.dump
│  ├─ R2/config.dump
│  └─ R3/config.dump
├─ outputs/
│  ├─ graphs/                # Topology images (future extension)
│  └─ reports/               # JSON/Markdown reports
├─ src/
│  ├─ main.py                # CLI entry
│  ├─ parser.py              # Parses Cisco-like configs
│  ├─ topology.py            # Builds graph, bandwidth, paths
│  ├─ validators.py          # Checks: duplicate IPs, VLAN/MTU mismatch, loops, missing devices
│  ├─ utils.py               # Helpers
│  └─ simulator/
│       ├─ __init__.py
│       ├─ core.py           # Multithread node + FIFO IPC + pause/resume
│       └─ messages.py       # Message dataclasses
├─ requirements.txt
└─ README.md
```

## 4) Try it quickly (uses the sample configs already in `conf/`)
```bash
# from project root (this folder)
python -m src.main parse --conf ./conf --out ./outputs/reports/parsed.json
python -m src.main validate --conf ./conf --out ./outputs/reports/validate.json
python -m src.main plan-load --conf ./conf --traffic ./conf/traffic.json --out ./outputs/reports/loadplan.json
python -m src.main simulate --conf ./conf --seconds 5
python -m src.main fail-link --conf ./conf --a R1 --b R2 --seconds 5
python -m src.main pause-resume --conf ./conf --seconds 6
```

### What these do
- **parse**: read configs → structured JSON
- **validate**: run configuration checks and write a report
- **plan-load**: compute link utilization vs bandwidth and suggest alternates if overloaded
- **simulate**: start Day‑1 discovery (hello messages) between neighbors
- **fail-link**: drop a link temporarily and observe logs
- **pause-resume**: pause all nodes for a moment (like Day‑2 change), then resume

Logs are printed to the console and also written per-device to `outputs/reports/*.log`.

## 5) Bring your own configs later
Put your real config dumps under `conf/<DEVICE>/config.dump`. The parser is intentionally simple and looks for lines like:
```
hostname R1
interface Gig0/0
 ip address 10.0.12.1 255.255.255.252
 description to R2 Gig0/0
 bandwidth 100000
 mtu 1500
!
router ospf 1
!
```
If two interfaces are in the **same subnet** or if an interface `description` says `to <Neighbor>`, the tool links them.

## 6) Extend it
- Add more validators (gateway checks, VLAN database, etc.)
- Emit Graphviz diagrams
- Replace the FIFO with sockets (TCP/IP) if you want true IPC over localhost
- Integrate `scapy` to craft real IP packets (optional)

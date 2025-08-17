from __future__ import annotations
import argparse, json, os, time
from typing import List, Tuple
from rich import print as rprint
import networkx as nx

from .parser import parse_conf_dir
from .topology import build_topology, compute_link_loads
from .validators import validate_all
from .simulator.core import Simulation

def cmd_parse(args):
    devices = parse_conf_dir(args.conf)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(devices, f, indent=2)
    rprint(f"[green]Parsed {len(devices)} devices. Wrote[/green] {args.out}")

def cmd_validate(args):
    devices = parse_conf_dir(args.conf)
    G = build_topology(devices)
    issues = validate_all(G, devices)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        json.dump({"issues": issues}, f, indent=2)
    rprint(f"[yellow]{len(issues)}[/yellow] findings written to {args.out}")
    for i in issues[:10]:
        rprint(i)

def _load_traffic(path: str) -> List[Tuple[str,str,int]]:
    data = json.load(open(path))
    use_peak = data.get("assumptions",{}).get("use_peak", True)
    eps = data.get("endpoints", [])
    # naive: pair endpoints by order
    pairs: List[Tuple[str,str,int]] = []
    if len(eps) >= 2:
        for i in range(0, len(eps), 2):
            if i+1 < len(eps):
                a, b = eps[i], eps[i+1]
                demand = int((a.get("peak_mbps") if use_peak else a.get("avg_mbps", 0)) or 0)
                pairs.append((a["device"], b["device"], demand))
    return pairs

def cmd_plan_load(args):
    devices = parse_conf_dir(args.conf)
    G = build_topology(devices)
    pairs = _load_traffic(args.traffic)
    loads = compute_link_loads(G, pairs)

    # summarize and recommend
    recs = []
    for u,v in G.edges():
        e = tuple(sorted((u,v)))
        bw = int(G[u][v].get("bandwidth", 0) or 0) // 1000  # kbps->Mbps if needed
        load = loads.get(e, 0)
        status = "OK" if load <= bw else "OVERLOADED"
        if load > bw:
            recs.append({
                "type":"load_balance_recommendation",
                "link": [u,v],
                "reason": f"Demand {load} Mbps > capacity {bw} Mbps",
                "suggestion": "Use secondary path / shift lower-priority flows"
            })
    out = {"link_loads_mbps": {f"{a}-{b}": loads.get(tuple(sorted((a,b))),0) for a,b in G.edges()}, "recommendations": recs}
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    json.dump(out, open(args.out,"w"), indent=2)
    rprint(f"Wrote load plan to {args.out}")

def cmd_simulate(args):
    devices = parse_conf_dir(args.conf)
    G = build_topology(devices)
    sim = Simulation(G, logs_dir="./outputs/reports")
    sim.start()
    time.sleep(args.seconds)
    sim.stop()

def cmd_fail_link(args):
    devices = parse_conf_dir(args.conf)
    G = build_topology(devices)
    sim = Simulation(G, logs_dir="./outputs/reports")
    sim.start()
    time.sleep(1.0)
    ok = sim.fail_link(args.a, args.b, down=True)
    if ok:
        from rich import print as rprint
        rprint(f"[red]Link {args.a}<->{args.b} DOWN[/red]")
    time.sleep(args.seconds)
    sim.stop()

def cmd_pause_resume(args):
    devices = parse_conf_dir(args.conf)
    G = build_topology(devices)
    sim = Simulation(G, logs_dir="./outputs/reports")
    sim.start()
    time.sleep(args.seconds // 2)
    sim.pause()
    from rich import print as rprint
    rprint("[yellow]PAUSED[/yellow]")
    time.sleep(2)
    sim.resume()
    rprint("[green]RESUMED[/green]")
    time.sleep(args.seconds // 2)
    sim.stop()

def build_argparse():
    ap = argparse.ArgumentParser(prog="net-sim")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("parse")
    sp.add_argument("--conf", required=True)
    sp.add_argument("--out", required=True)
    sp.set_defaults(func=cmd_parse)

    sv = sub.add_parser("validate")
    sv.add_argument("--conf", required=True)
    sv.add_argument("--out", required=True)
    sv.set_defaults(func=cmd_validate)

    sl = sub.add_parser("plan-load")
    sl.add_argument("--conf", required=True)
    sl.add_argument("--traffic", required=True)
    sl.add_argument("--out", required=True)
    sl.set_defaults(func=cmd_plan_load)

    ss = sub.add_parser("simulate")
    ss.add_argument("--conf", required=True)
    ss.add_argument("--seconds", type=int, default=5)
    ss.set_defaults(func=cmd_simulate)

    sf = sub.add_parser("fail-link")
    sf.add_argument("--conf", required=True)
    sf.add_argument("--a", required=True)
    sf.add_argument("--b", required=True)
    sf.add_argument("--seconds", type=int, default=5)
    sf.set_defaults(func=cmd_fail_link)

    spr = sub.add_parser("pause-resume")
    spr.add_argument("--conf", required=True)
    spr.add_argument("--seconds", type=int, default=6)
    spr.set_defaults(func=cmd_pause_resume)

    return ap

def main():
    ap = build_argparse()
    args = ap.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()

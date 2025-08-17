from __future__ import annotations
import networkx as nx
from typing import Dict, Any, Tuple, List
import itertools, re
from .utils import same_subnet

def _neighbor_from_desc(desc: str) -> str:
    # naive: look for 'to <NAME>'
    m = re.search(r'\bto\s+([A-Za-z0-9_-]+)', desc or "", re.I)
    if m:
        return m.group(1)
    return ""

def build_topology(devices: Dict[str, Any]) -> nx.Graph:
    G = nx.Graph()
    for dname, dev in devices.items():
        G.add_node(dname, kind="router-or-switch")

    # edges: by description and by same subnet
    # index subnets
    subnet_map = {}  # (network) -> list[(device, iface dict)]
    for dname, dev in devices.items():
        for iface in dev.get("interfaces", []):
            net = iface.get("network", "")
            if net:
                subnet_map.setdefault(net, []).append((dname, iface))

    # connect by same subnet
    for net, lst in subnet_map.items():
        if len(lst) >= 2:
            for (a, ia), (b, ib) in itertools.combinations(lst, 2):
                bw = min(ia.get("bandwidth", 0) or 0, ib.get("bandwidth", 0) or 0)
                mtu = min(ia.get("mtu", 1500), ib.get("mtu", 1500))
                G.add_edge(a, b, network=net, bandwidth=bw, mtu=mtu)

    # connect by description hints (if not already connected)
    for dname, dev in devices.items():
        for iface in dev.get("interfaces", []):
            n = _neighbor_from_desc(iface.get("description", ""))
            if n and n in devices and not G.has_edge(dname, n):
                bw = iface.get("bandwidth", 0) or 0
                mtu = iface.get("mtu", 1500)
                G.add_edge(dname, n, network=iface.get("network", ""), bandwidth=bw, mtu=mtu)

    return G

def compute_link_loads(G: nx.Graph, traffic_pairs: List[Tuple[str,str,int]]) -> Dict[Tuple[str,str], int]:
    # traffic_pairs: list of (src_device, dst_device, demand_mbps)
    loads = { tuple(sorted((u,v))): 0 for u,v in G.edges() }
    for src, dst, demand in traffic_pairs:
        if src not in G or dst not in G:
            continue
        try:
            path = nx.shortest_path(G, src, dst)
            for u,v in zip(path, path[1:]):
                e = tuple(sorted((u,v)))
                loads[e] = loads.get(e, 0) + demand
        except nx.NetworkXNoPath:
            pass
    return loads

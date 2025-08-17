from __future__ import annotations
import networkx as nx
from typing import Dict, Any, List, Tuple, Set
from collections import defaultdict
from .utils import same_subnet

def duplicate_ips(devices: Dict[str, Any]) -> List[Dict[str, Any]]:
    seen = defaultdict(list)  # ip -> list[(dev, iface)]
    for d, dev in devices.items():
        for i in dev.get("interfaces", []):
            ip = i.get("ip", "")
            if ip:
                seen[ip].append((d, i.get("name", "")))
    issues = []
    for ip, lst in seen.items():
        if len(lst) > 1:
            issues.append({"type": "duplicate_ip", "ip": ip, "locations": lst})
    return issues

def vlan_mismatches(G: nx.Graph, devices: Dict[str, Any]) -> List[Dict[str, Any]]:
    issues = []
    # For each edge, if both sides have an interface on same subnet but different VLAN -> mismatch
    # (Simplified heuristic)
    for u,v,data in G.edges(data=True):
        net = data.get("network","")
        if not net: 
            continue
        u_vlans = set()
        v_vlans = set()
        for i in devices[u]["interfaces"]:
            if i.get("network","") == net:
                u_vlans.add(i.get("vlan",0))
        for i in devices[v]["interfaces"]:
            if i.get("network","") == net:
                v_vlans.add(i.get("vlan",0))
        if u_vlans and v_vlans and u_vlans != v_vlans:
            issues.append({"type":"vlan_mismatch","link":(u,v),"u_vlans":list(u_vlans),"v_vlans":list(v_vlans)})
    return issues

def mtu_mismatches(G: nx.Graph) -> List[Dict[str, Any]]:
    issues = []
    for u,v,data in G.edges(data=True):
        # We stored a single MTU per edge (min). We can't directly compare both sides
        # so we flag if mtu < 1500 as a potential mismatch condition in demo.
        if data.get("mtu",1500) < 1500:
            issues.append({"type":"mtu_mismatch_warning","link":(u,v),"edge_mtu":data.get("mtu")})
    return issues

def loops(G: nx.Graph) -> List[Dict[str, Any]]:
    cycles = list(nx.cycle_basis(G))
    if cycles:
        return [{"type":"loop_detected","cycle":c} for c in cycles]
    return []

def missing_devices_by_description(devices: Dict[str, Any]) -> List[Dict[str, Any]]:
    import re
    issues = []
    for d, dev in devices.items():
        for i in dev.get("interfaces", []):
            desc = i.get("description","")
            m = re.search(r'\bto\s+([A-Za-z0-9_-]+)', desc, re.I)
            if m:
                neighbor = m.group(1)
                if neighbor not in devices:
                    issues.append({"type":"missing_neighbor_config","device":d,"iface":i.get("name"),"neighbor":neighbor})
    return issues

def recommend_protocols(devices: Dict[str, Any]) -> List[Dict[str, Any]]:
    # Toy rule: if any device runs BGP with ASN and others run OSPF, suggest segmenting domains
    bgp_asns = set()
    ospf = False
    for d, dev in devices.items():
        for b in dev.get("routing",{}).get("bgp",[]):
            bgp_asns.add(b.get("asn"))
        if dev.get("routing",{}).get("ospf"):
            ospf = True
    recs = []
    if len(bgp_asns) >= 1 and ospf:
        recs.append({"type":"protocol_recommendation","advice":"Use BGP for inter-domain and OSPF for intra-domain boundaries."})
    return recs

def aggregate_nodes(G: nx.Graph) -> List[Dict[str, Any]]:
    # Toy suggestion: degree-1 routers with same subnet as parent could be aggregated
    recs = []
    for n in G.nodes():
        if G.degree(n) == 1:
            recs.append({"type":"aggregation_opportunity","node":n,"reason":"Leaf node; consider collapsing if not needed."})
    return recs

def validate_all(G: nx.Graph, devices: Dict[str, Any]) -> List[Dict[str, Any]]:
    issues = []
    issues += duplicate_ips(devices)
    issues += vlan_mismatches(G, devices)
    issues += mtu_mismatches(G)
    issues += loops(G)
    issues += missing_devices_by_description(devices)
    issues += recommend_protocols(devices)
    issues += aggregate_nodes(G)
    return issues

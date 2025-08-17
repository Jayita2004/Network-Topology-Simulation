from __future__ import annotations
import os, re, json
from typing import Dict, Any, List
from .utils import ip_mask_to_network

IFACE_RE = re.compile(r'^\s*interface\s+([\w\/\.]+)', re.I)
IP_RE = re.compile(r'^\s*ip\s+address\s+(\d+\.\d+\.\d+\.\d+)\s+(\d+\.\d+\.\d+\.\d+)', re.I)
DESC_RE = re.compile(r'^\s*description\s+(.+)$', re.I)
BW_RE = re.compile(r'^\s*bandwidth\s+(\d+)', re.I)
MTU_RE = re.compile(r'^\s*mtu\s+(\d+)', re.I)
HOST_RE = re.compile(r'^\s*hostname\s+(\S+)', re.I)
OSPF_RE = re.compile(r'^\s*router\s+ospf\s+(\d+)', re.I)
BGP_RE = re.compile(r'^\s*router\s+bgp\s+(\d+)', re.I)
VLAN_RE = re.compile(r'vlan\s+(\d+)|encapsulation\s+dot1q\s+(\d+)|access\s+vlan\s+(\d+)', re.I)

def parse_device_config(path: str) -> Dict[str, Any]:
    device = {
        "hostname": None,
        "interfaces": [],
        "routing": {"ospf": [], "bgp": []},
    }
    if not os.path.exists(path):
        return device

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    hostname = None
    cur = None
    for line in lines:
        m = HOST_RE.match(line)
        if m:
            hostname = m.group(1)

        mi = IFACE_RE.match(line)
        if mi:
            if cur:
                device["interfaces"].append(cur)
            cur = {
                "name": mi.group(1),
                "description": "",
                "ip": "",
                "mask": "",
                "bandwidth": 0,
                "mtu": 1500,
                "vlan": 0,
                "network": ""
            }
            continue

        if cur:
            m = IP_RE.match(line)
            if m:
                cur["ip"], cur["mask"] = m.group(1), m.group(2)
                cur["network"] = ip_mask_to_network(cur["ip"], cur["mask"])
                continue
            m = DESC_RE.match(line)
            if m:
                cur["description"] = m.group(1).strip()
                continue
            m = BW_RE.match(line)
            if m:
                cur["bandwidth"] = int(m.group(1))
                continue
            m = MTU_RE.match(line)
            if m:
                cur["mtu"] = int(m.group(1))
                continue
            m = VLAN_RE.search(line)
            if m:
                for g in m.groups():
                    if g:
                        try:
                            cur["vlan"] = int(g)
                        except:
                            pass

        mo = OSPF_RE.match(line)
        if mo:
            device["routing"]["ospf"].append({"process": int(mo.group(1))})
        mb = BGP_RE.match(line)
        if mb:
            device["routing"]["bgp"].append({"asn": int(mb.group(1))})

    if cur:
        device["interfaces"].append(cur)

    if not hostname:
        # fallback to folder name as hostname
        hostname = os.path.basename(os.path.dirname(path)) or "UNKNOWN"
    device["hostname"] = hostname
    return device

def parse_conf_dir(conf_root: str) -> Dict[str, Any]:
    devices: Dict[str, Any] = {}
    for name in os.listdir(conf_root):
        d = os.path.join(conf_root, name)
        cfg = os.path.join(d, "config.dump")
        if os.path.isdir(d) and os.path.exists(cfg):
            dev = parse_device_config(cfg)
            devices[dev["hostname"]] = dev
    return devices

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--conf", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    data = parse_conf_dir(args.conf)
    with open(args.out, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Wrote {args.out}")

if __name__ == "__main__":
    main()

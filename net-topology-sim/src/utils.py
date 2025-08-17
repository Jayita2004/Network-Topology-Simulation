from __future__ import annotations
from dataclasses import dataclass
import ipaddress
from typing import Optional, Tuple

def ip_mask_to_network(ip: str, mask: str) -> str:
    try:
        net = ipaddress.IPv4Network((ip, mask), strict=False)
        return str(net)
    except Exception:
        return ""

def same_subnet(ip1: str, mask1: str, ip2: str, mask2: str) -> bool:
    try:
        n1 = ipaddress.IPv4Network((ip1, mask1), strict=False)
        n2 = ipaddress.IPv4Network((ip2, mask2), strict=False)
        return n1.network_address == n2.network_address and n1.prefixlen == n2.prefixlen
    except Exception:
        return False

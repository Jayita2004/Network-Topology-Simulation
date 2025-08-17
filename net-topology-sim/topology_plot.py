import networkx as nx
import matplotlib.pyplot as plt
import json

# Load parsed.json (generated earlier by parse command)
with open("./outputs/reports/parsed.json") as f:
    devices = json.load(f)

# Build graph
G = nx.Graph()
for dev in devices:
    G.add_node(dev)

subnet_map = {}
for d, dev in devices.items():
    for iface in dev.get("interfaces", []):
        net = iface.get("network", "")
        if net:
            subnet_map.setdefault(net, []).append(d)

for net, lst in subnet_map.items():
    if len(lst) > 1:
        for i in range(len(lst)):
            for j in range(i+1, len(lst)):
                G.add_edge(lst[i], lst[j], label=net)

# Draw graph
pos = nx.spring_layout(G, seed=42)
nx.draw(G, pos, with_labels=True, node_color="lightblue", node_size=2000, font_size=12, font_weight="bold")
labels = nx.get_edge_attributes(G, 'label')
nx.draw_networkx_edge_labels(G, pos, edge_labels=labels, font_size=8)

plt.title("Generated Network Topology", fontsize=14)
plt.savefig("topology_diagram.png")
plt.show()

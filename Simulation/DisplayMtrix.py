# import json
# import networkx as nx
# import matplotlib.pyplot as plt

# # Load the RSSI matrix
# with open("matrix.json", "r") as f:
#     rssi_matrix = json.load(f)

# # Convert string keys to integers
# rssi_matrix = {int(k): {int(kk): vv for kk, vv in v.items()} for k, v in rssi_matrix.items()}

# # Define label map (case switch style)
# node_labels = {
#     0: "FAMILY",
#     1: "KITCHEN",
#     2: "MASTER SUITE",
#     3: "GARAGE",
#     4: "BEDROOM 2",
#     5: "BEDROOM 3",
#     6: "Laundry",
#     7: "FAMILY Router"
# }

# def visualize_fspl_layout(rssi_matrix):
#     G = nx.Graph()
#     for node_id, links in rssi_matrix.items():
#         for other_id, fspl in links.items():
#             if abs(fspl) >= 74.9:
#                 continue
#             if node_id < other_id:
#                 G.add_edge(node_id, other_id, weight=1 / (fspl + 1e-3))

#     pos = nx.spring_layout(G, weight='weight', seed=42)

#     plt.figure(figsize=(8, 8))
#     nx.draw(G, pos, labels=node_labels, with_labels=True, node_color='skyblue', edge_color='gray')
#     edge_weights = nx.get_edge_attributes(G, 'weight')
#     edge_labels = {k: f"{1/v:.1f}" for k, v in edge_weights.items()}
#     nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels)
#     plt.title("Relative Node Layout Based on FSPL Distances")
#     plt.axis("equal")
#     plt.savefig("fspl_network.png", dpi=300)
#     print("Saved layout as fspl_network.png")

#     plt.show()

# visualize_fspl_layout(rssi_matrix)
import json
import networkx as nx
import matplotlib.pyplot as plt

# Load the RSSI matrix with per-TX power levels
with open("matrix.json", "r") as f:
    raw_matrix = json.load(f)

MIN_RSSI = -53  # cutoff
pwlvl = 16

# Convert keys to int properly
rssi_matrix = {
    int(src): {
        int(dst): {int(pwr): rssi for pwr, rssi in levels.items()}
        for dst, levels in targets.items()
    }
    for src, targets in raw_matrix.items()
}

# Label map
node_labels = {
    0: "FAMILY",
    1: "KITCHEN",
    2: "MASTER SUITE",
    3: "GARAGE",
    4: "BEDROOM 2",
    5: "BEDROOM 3",
    6: "Laundry",
    7: "FAMILY Router"
}

def visualize_min_power_routing(rssi_matrix):
    G = nx.Graph()

    for src, targets in rssi_matrix.items():
        for dst, levels in targets.items():
            if src >= dst:
                continue  # avoid duplicate edges

            # Find minimum TX power with acceptable RSSI
            best_power = None
            for pwr in sorted(levels.keys()):
                if levels[pwr] >= MIN_RSSI:
                    best_power = pwr
                    break
            
            if best_power is not None:
                if best_power > pwlvl:
                    continue
                rssi = levels[best_power]
                G.add_edge(src, dst, weight=1 / (rssi + 1e-3), label=f"{best_power} dBm")

    pos = nx.spring_layout(G, weight='weight', seed=42)

    plt.figure(figsize=(8, 8))
    nx.draw(G, pos, labels=node_labels, with_labels=True, node_color='skyblue', edge_color='gray')
    
    edge_labels = nx.get_edge_attributes(G, 'label')
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels)
    
    plt.title(f"Links Using Minimum TX Power to Reach RSSI ≥ {MIN_RSSI} dBm")
    plt.axis("equal")
    plt.savefig("min_power_network.png", dpi=300)
    print("Saved layout as min_power_network.png")

    plt.show()

visualize_min_power_routing(rssi_matrix)

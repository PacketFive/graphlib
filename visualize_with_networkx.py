import networkx as nx
import matplotlib.pyplot as plt
from mygraphlib import Graph

# Build a simple graph using mygraphlib
g = Graph()
g.add_edge("0", "1")
g.add_edge("1", "2")
g.add_edge("1", "3")
g.add_edge("3", "4")

# Convert internal graph to networkx Graph
G = nx.Graph()
for node, neighbors in g.adjacency.items():
    for neighbor in neighbors:
        G.add_edge(node, neighbor)

# Draw the graph using circular layout
plt.figure(figsize=(6, 6))
nx.draw_circular(
    G,
    with_labels=True,
    node_color="lightblue",
    edge_color="gray",
    node_size=800,
    font_size=10,
    font_weight="bold",
)
plt.title("Graph Visualization (networkx)")
plt.tight_layout()
plt.show()

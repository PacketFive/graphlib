from mygraphlib import Graph


def test_graph_basics():
    # Create simple graph
    g = Graph()
    g.add_edge("A", "B")
    g.add_edge("B", "C")
    g.add_node("D")

    # Check neighbors of node B
    assert sorted(g.get_neighbors("B")) == ["A", "C"]

    # Check path between connected and unconnected nodes
    assert g.has_path("A", "C") is True
    assert g.has_path("A", "D") is False

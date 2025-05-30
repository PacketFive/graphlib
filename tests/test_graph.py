import pytest
from graph_lib.graph import Graph


class TestGraph:
    def test_add_node(self):
        g = Graph()
        g.add_node("A")
        assert "A" in g
        assert len(g) == 1
        assert g.get_nodes_count() == 1

    def test_add_node_with_data(self):
        g = Graph()
        node_data = {"name": "Alice", "age": 30}
        g.add_node("A", data=node_data)
        assert g.get_node_data("A") == node_data

    def test_add_existing_node_raises_value_error(self):
        g = Graph()
        g.add_node("A")
        with pytest.raises(ValueError, match="Node A already exists."):
            g.add_node("A")

    def test_get_node_data_non_existent_node_raises_value_error(self):
        g = Graph()
        with pytest.raises(ValueError, match="Node Z does not exist."):
            g.get_node_data("Z")

    def test_add_edge(self):
        g = Graph()
        g.add_edge("A", "B", weight=2.5)
        assert "A" in g
        assert "B" in g
        assert g.get_edge_weight("A", "B") == 2.5
        assert list(g.neighbors("A")) == ["B"]
        assert g.get_edges_count() == 1

    def test_add_edge_creates_nodes(self):
        g = Graph()
        g.add_edge("X", "Y")
        assert "X" in g
        assert "Y" in g
        assert g.get_edge_weight("X", "Y") == 1.0 # Default weight
        assert g.get_nodes_count() == 2
        assert g.get_edges_count() == 1

    def test_get_edge_weight_non_existent_edge(self):
        g = Graph()
        g.add_node("A")
        g.add_node("B")
        assert g.get_edge_weight("A", "B") is None
        assert g.get_edge_weight("A", "C") is None # C doesn't exist

    def test_neighbors(self):
        g = Graph()
        g.add_edge("A", "B")
        g.add_edge("A", "C")
        g.add_edge("B", "C")
        assert sorted(list(g.neighbors("A"))) == sorted(["B", "C"])
        assert list(g.neighbors("B")) == ["C"]
        assert list(g.neighbors("C")) == []

    def test_neighbors_non_existent_node_raises_value_error(self):
        g = Graph()
        with pytest.raises(ValueError, match="Node Z does not exist."):
            list(g.neighbors("Z"))

    def test_get_all_nodes(self):
        g = Graph()
        nodes = {"A", "B", "C", "D"}
        for node in nodes:
            g.add_node(node)
        assert set(g.get_all_nodes()) == nodes
        g.add_edge("D", "E") # Add one more node via edge creation
        assert set(g.get_all_nodes()) == nodes.union({"E"})

    def test_get_all_nodes_empty_graph(self):
        g = Graph()
        assert list(g.get_all_nodes()) == []

    def test_contains_node(self):
        g = Graph()
        g.add_node("A")
        assert "A" in g
        assert "Z" not in g

    def test_len_graph(self):
        g = Graph()
        assert len(g) == 0
        g.add_node("A")
        assert len(g) == 1
        g.add_node("B")
        assert len(g) == 2
        g.add_edge("C", "D") # Nodes C, D created
        assert len(g) == 4

    def test_get_nodes_count(self):
        g = Graph()
        assert g.get_nodes_count() == 0
        g.add_node(1)
        g.add_node(2)
        assert g.get_nodes_count() == 2

    def test_get_edges_count(self):
        g = Graph()
        assert g.get_edges_count() == 0
        g.add_edge("A", "B")
        assert g.get_edges_count() == 1
        g.add_edge("A", "C")
        assert g.get_edges_count() == 2
        g.add_edge("B", "C")
        assert g.get_edges_count() == 3
        g.add_edge("D", "E", weight=0.5) # New nodes, new edge
        assert g.get_edges_count() == 4
        g.add_edge("A", "B", weight=5) # Update existing edge, count should not change
        assert g.get_edges_count() == 4

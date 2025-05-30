import pytest
from graph_lib.graph import Graph
from graph_lib.algorithms import dijkstra
from graph_lib.algorithms import bfs
from graph_lib.algorithms import dfs

class TestDijkstra:
    def test_dijkstra_simple_path(self):
        g = Graph()
        g.add_edge("A", "B", 10)
        g.add_edge("B", "C", 5)
        g.add_edge("A", "C", 20)

        dist, path = dijkstra(g, "A", "C")
        assert dist == 15
        assert path == ["A", "B", "C"]

    def test_dijkstra_no_path(self):
        g = Graph()
        g.add_node("A")
        g.add_node("B")
        g.add_node("C")
        g.add_edge("A", "B", 1)
        # No path from A to C

        dist, path = dijkstra(g, "A", "C")
        assert dist is None
        assert path == []

    def test_dijkstra_start_node_is_end_node(self):
        g = Graph()
        g.add_node("A")
        dist, path = dijkstra(g, "A", "A")
        assert dist == 0
        assert path == ["A"]

    def test_dijkstra_all_nodes(self):
        g = Graph()
        g.add_edge("A", "B", 1)
        g.add_edge("A", "C", 4)
        g.add_edge("B", "C", 2)
        g.add_edge("B", "D", 5)
        g.add_edge("C", "D", 1)
        g.add_node("E") # Unconnected node

        distances, predecessors = dijkstra(g, "A")
        
        expected_distances = {"A": 0, "B": 1, "C": 3, "D": 4}
        assert distances == expected_distances

        # Check predecessors to reconstruct paths (optional, but good for verification)
        # Path to D: A -> B -> C -> D (cost 4)
        assert predecessors["D"] == "C"
        assert predecessors["C"] == "B"
        assert predecessors["B"] == "A"
        assert predecessors["A"] is None
        assert "E" not in distances # E is unreachable

    def test_dijkstra_graph_with_cycles(self):
        g = Graph()
        g.add_edge("A", "B", 1)
        g.add_edge("B", "C", 1)
        g.add_edge("C", "A", 1) # Cycle
        g.add_edge("B", "D", 3)

        dist, path = dijkstra(g, "A", "D")
        assert dist == 4
        assert path == ["A", "B", "D"]

        distances_all, _ = dijkstra(g, "A")
        assert distances_all == {"A": 0, "B": 1, "C": 2, "D": 4}

    def test_dijkstra_non_existent_start_node(self):
        g = Graph()
        g.add_node("A")
        with pytest.raises(ValueError, match="Start node Z not found in the graph."):
            dijkstra(g, "Z", "A")

    def test_dijkstra_non_existent_end_node(self):
        g = Graph()
        g.add_node("A")
        with pytest.raises(ValueError, match="End node Z not found in the graph."):
            dijkstra(g, "A", "Z")

    def test_dijkstra_empty_graph(self):
        g = Graph()
        with pytest.raises(ValueError, match="Start node A not found in the graph."):
            dijkstra(g, "A")
        # If nodes were added but no start node exists for path finding
        g.add_node("X")
        with pytest.raises(ValueError, match="Start node A not found in the graph."):
            dijkstra(g, "A", "X")

    def test_dijkstra_single_node_graph_all_nodes(self):
        g = Graph()
        g.add_node("A")
        distances, predecessors = dijkstra(g, "A")
        assert distances == {"A": 0}
        assert predecessors["A"] is None

    def test_dijkstra_path_to_self_complex_graph(self):
        g = Graph()
        g.add_edge("A", "B", 1)
        g.add_edge("B", "C", 1)
        dist, path = dijkstra(g, "A", "A")
        assert dist == 0
        assert path == ["A"]

    def test_dijkstra_multiple_paths_selects_shortest(self):
        g = Graph()
        g.add_edge("S", "A", 1)
        g.add_edge("S", "B", 4)
        g.add_edge("A", "B", 2) # S->A->B = 1+2=3
        g.add_edge("A", "C", 5)
        g.add_edge("B", "C", 1) # S->A->B->C = 1+2+1=4; S->B->C = 4+1=5

        dist_s_c, path_s_c = dijkstra(g, "S", "C")
        assert dist_s_c == 4
        assert path_s_c == ["S", "A", "B", "C"]

        dist_s_b, path_s_b = dijkstra(g, "S", "B")
        assert dist_s_b == 3
        assert path_s_b == ["S", "A", "B"]

    def test_dijkstra_unreachable_end_node_in_larger_graph(self):
        g = Graph()
        g.add_edge("A", "B", 1)
        g.add_edge("C", "D", 1)
        g.add_node("E")

        dist, path = dijkstra(g, "A", "D")
        assert dist is None
        assert path == []

        # Test all nodes from A
        distances, _ = dijkstra(g, "A")
        assert distances == {"A": 0, "B": 1} 
        # C, D, E should not be in distances as they are unreachable from A
        assert "C" not in distances
        assert "D" not in distances
        assert "E" not in distances

class TestBFS:
    def test_bfs_path_found(self):
        g = Graph()
        g.add_edge("A", "B")
        g.add_edge("A", "C")
        g.add_edge("B", "D")
        g.add_edge("C", "E")
        g.add_edge("D", "E")
        g.add_edge("D", "F")

        path, predecessors = bfs(g, "A", "F")
        assert path == ["A", "B", "D", "F"]
        # Check some predecessors
        assert predecessors["F"] == "D"
        assert predecessors["D"] == "B"
        assert predecessors["B"] == "A"
        assert predecessors["A"] is None

    def test_bfs_no_path_to_target(self):
        g = Graph()
        g.add_node("A")
        g.add_node("B")
        g.add_node("C")
        g.add_edge("A", "B")

        path, _ = bfs(g, "A", "C")
        assert path is None

    def test_bfs_start_node_is_target_node(self):
        g = Graph()
        g.add_node("A")
        path, _ = bfs(g, "A", "A")
        assert path == ["A"]

    def test_bfs_all_visited_nodes_order(self):
        g = Graph()
        #    A
        #   / \
        #  B   C
        # /   / \
        #D   E   F
        g.add_edge("A", "B")
        g.add_edge("A", "C")
        g.add_edge("B", "D")
        g.add_edge("C", "E")
        g.add_edge("C", "F")
        g.add_node("G") # Unconnected

        visited_nodes = bfs(g, "A")
        # Expected order can vary based on neighbor iteration if not sorted,
        # but for a simple list, we expect levels. A, then B,C (order may vary), then D,E,F
        assert visited_nodes[0] == "A"
        assert set(visited_nodes[1:3]) == {"B", "C"}
        assert set(visited_nodes[3:6]) == {"D", "E", "F"}
        assert len(visited_nodes) == 6 # A, B, C, D, E, F
        assert "G" not in visited_nodes

    def test_bfs_all_visited_complex_graph(self):
        g = Graph()
        g.add_edge(0, 1)
        g.add_edge(0, 2)
        g.add_edge(1, 2)
        g.add_edge(2, 0) # Cycle
        g.add_edge(2, 3)
        g.add_edge(3, 3) # Self-loop
        
        visited_nodes = bfs(g, 2)
        # Possible orders from 2: [2,0,3,1] or [2,0,1,3] or [2,3,0,1] etc.
        assert set(visited_nodes) == {0, 1, 2, 3}
        assert visited_nodes[0] == 2
        assert len(visited_nodes) == 4

    def test_bfs_empty_graph(self):
        g = Graph()
        with pytest.raises(ValueError, match="Start node A not found in the graph."):
            bfs(g, "A")
        g.add_node("X")
        with pytest.raises(ValueError, match="Start node A not found in the graph."):
            bfs(g, "A", "X")

    def test_bfs_non_existent_start_node(self):
        g = Graph()
        g.add_node("A")
        with pytest.raises(ValueError, match="Start node Z not found in the graph."):
            bfs(g, "Z")

    def test_bfs_non_existent_target_node(self):
        g = Graph()
        g.add_node("A")
        with pytest.raises(ValueError, match="Target node Z not found in the graph."):
            bfs(g, "A", "Z")

    def test_bfs_disconnected_component_target_unreachable(self):
        g = Graph()
        g.add_edge("A", "B")
        g.add_node("C") # C is in a different component
        path, _ = bfs(g, "A", "C")
        assert path is None

    def test_bfs_disconnected_component_all_nodes(self):
        g = Graph()
        g.add_edge("A", "B")
        g.add_node("C")
        visited = bfs(g, "A")
        assert set(visited) == {"A", "B"}
        assert "C" not in visited

class TestDFS:
    def test_dfs_path_found(self):
        g = Graph()
        g.add_edge("A", "B")
        g.add_edge("A", "C")
        g.add_edge("B", "D")
        g.add_edge("C", "E")
        g.add_edge("D", "F") # A -> B -> D -> F
        g.add_edge("E", "F") # A -> C -> E -> F (alternative path)

        # Iterative DFS path can vary. The first one found is returned.
        path, predecessors = dfs(g, "A", "F")
        assert path is not None
        assert path[0] == "A"
        assert path[-1] == "F"
        # Verify path validity using predecessors
        for i in range(len(path) - 1, 0, -1):
            assert predecessors[path[i]] == path[i-1]

    def test_dfs_no_path_to_target(self):
        g = Graph()
        g.add_node("A")
        g.add_node("B")
        g.add_node("C")
        g.add_edge("A", "B")

        path, _ = dfs(g, "A", "C")
        assert path is None

    def test_dfs_start_node_is_target_node(self):
        g = Graph()
        g.add_node("A")
        path, _ = dfs(g, "A", "A")
        assert path == ["A"]

    def test_dfs_all_visited_nodes_order(self):
        g = Graph()
        #    A
        #   / \
        #  B   C
        # /   / \
        #D   E   F
        g.add_edge("A", "B")
        g.add_edge("A", "C")
        g.add_edge("B", "D")
        g.add_edge("C", "E")
        g.add_edge("C", "F")
        g.add_node("G") # Unconnected

        # DFS order depends on neighbor iteration and stack behavior.
        # For iterative DFS processing neighbors in reversed order of discovery:
        # Stack: A -> C,B (reversed) -> C pops, Dfs(C), stack: B -> C,E,F (rev) -> F pops, Dfs(F) etc.
        # A typical pre-order might be A, B, D, C, E, F (if B is processed before C)
        # Or A, C, E, F, B, D (if C is processed before B)
        visited_nodes = dfs(g, "A")
        assert len(visited_nodes) == 6
        assert set(visited_nodes) == {"A", "B", "C", "D", "E", "F"}
        assert visited_nodes[0] == "A" # Start node is always first in this pre-order collection
        assert "G" not in visited_nodes

    def test_dfs_all_visited_complex_graph_with_cycle(self):
        g = Graph()
        g.add_edge(0, 1)
        g.add_edge(0, 2)
        g.add_edge(1, 3) 
        g.add_edge(2, 3)
        g.add_edge(3, 0) # Cycle back to 0
        g.add_node(4) # Disconnected node
        
        visited_nodes = dfs(g, 0)
        assert len(visited_nodes) == 4 # 0, 1, 2, 3
        assert set(visited_nodes) == {0, 1, 2, 3}
        assert visited_nodes[0] == 0
        assert 4 not in visited_nodes

    def test_dfs_empty_graph(self):
        g = Graph()
        with pytest.raises(ValueError, match="Start node A not found in the graph."):
            dfs(g, "A")

    def test_dfs_non_existent_start_node(self):
        g = Graph()
        g.add_node("A")
        with pytest.raises(ValueError, match="Start node Z not found in the graph."):
            dfs(g, "Z")

    def test_dfs_non_existent_target_node(self):
        g = Graph()
        g.add_node("A")
        with pytest.raises(ValueError, match="Target node Z not found in the graph."):
            dfs(g, "A", "Z")

    def test_dfs_path_to_self_in_path(self):
        g = Graph()
        g.add_edge("A", "B")
        g.add_edge("B", "A") # Cycle that includes start/target if A is target
        path, _ = dfs(g, "A", "A")
        assert path == ["A"]

    def test_dfs_disconnected_component_target_unreachable(self):
        g = Graph()
        g.add_edge("A", "B")
        g.add_node("C")
        path, _ = dfs(g, "A", "C")
        assert path is None

    def test_dfs_disconnected_component_all_nodes(self):
        g = Graph()
        g.add_edge("A", "B")
        g.add_node("C")
        visited = dfs(g, "A")
        assert set(visited) == {"A", "B"}
        assert "C" not in visited 
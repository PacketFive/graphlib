from typing import Dict, List, Set


class Graph:
    def __init__(self) -> None:
        # Adjacency list to store graph: node_id -> list of neighbors
        self.adjacency: Dict[str, List[str]] = {}

    def add_node(self, node_id: str) -> None:
        # Adds a node to the graph if it doesn't already exist
        if node_id not in self.adjacency:
            self.adjacency[node_id] = []

    def add_edge(self, from_node: str, to_node: str) -> None:
        # Adds an edge between two nodes(undirected)
        self.add_node(from_node)
        self.add_node(to_node)
        self.adjacency[from_node].append(to_node)
        self.adjacency[to_node].append(from_node)

    def get_neighbors(self, node_id: str) -> List[str]:
        # Returns a list of neghbors for the given node
        return self.adjacency.get(node_id, [])

    def has_path(self, start: str, end: str) -> bool:
        # Checks if there is a path between two nodes using DFS
        visited: Set[str] = set()
        return self._dfs(start, end, visited)

    def _dfs(self, current: str, target: str, visited: Set[str]) -> bool:
        # Helper recursive function for dfs traversal
        if current == target:
            return True
        visited.add(current)
        for neighbor in self.adjacency.get(current, []):
            if neighbor not in visited:
                if self._dfs(neighbor, target, visited):
                    return True
        return False

    def __str__(self) -> str:
        # Returns a string representation of the graph
        return "\n".join(
            f"{node}: {neighbors}" for node, neighbors in self.adjacency.items()
        )

from typing import Any, Dict, Hashable, Iterator, Optional, Set

class Graph:
    """
    A simple graph implementation that allows storing objects (data) with nodes
    and weighted edges.
    """

    def __init__(self) -> None:
        self._nodes: Dict[Hashable, Any] = {}  # Stores node IDs and their associated data
        self._adjacency_list: Dict[Hashable, Dict[Hashable, float]] = {}  # Stores node -> {neighbor: weight}

    def add_node(self, node_id: Hashable, data: Optional[Any] = None) -> None:
        """
        Adds a node to the graph.

        Args:
            node_id: The unique identifier for the node.
            data: Optional data to associate with the node.

        Raises:
            ValueError: If the node already exists.
        """
        if node_id in self._nodes:
            raise ValueError(f"Node {node_id} already exists.")
        self._nodes[node_id] = data
        self._adjacency_list[node_id] = {}

    def get_node_data(self, node_id: Hashable) -> Optional[Any]:
        """
        Retrieves the data associated with a node.

        Args:
            node_id: The ID of the node.

        Returns:
            The data associated with the node, or None if the node doesn't exist
            or has no data.
        
        Raises:
            ValueError: If the node does not exist.
        """
        if node_id not in self._nodes:
            raise ValueError(f"Node {node_id} does not exist.")
        return self._nodes.get(node_id)

    def add_edge(self, u: Hashable, v: Hashable, weight: float = 1.0) -> None:
        """
        Adds a directed edge from node u to node v with a given weight.
        If the nodes do not exist, they will be added to the graph.

        Args:
            u: The starting node of the edge.
            v: The ending node of the edge.
            weight: The weight of the edge (default is 1.0).
        """
        if u not in self._nodes:
            self.add_node(u)
        if v not in self._nodes:
            self.add_node(v)
        
        self._adjacency_list[u][v] = weight

    def get_edge_weight(self, u: Hashable, v: Hashable) -> Optional[float]:
        """
        Gets the weight of the edge between u and v.

        Args:
            u: The starting node.
            v: The ending node.

        Returns:
            The weight of the edge if it exists, otherwise None.
        """
        if u in self._adjacency_list and v in self._adjacency_list.get(u, {}):
            return self._adjacency_list[u][v]
        return None

    def neighbors(self, node_id: Hashable) -> Iterator[Hashable]:
        """
        Returns an iterator over the neighbors of a given node.

        Args:
            node_id: The ID of the node.

        Yields:
            Neighboring node IDs.

        Raises:
            ValueError: If the node does not exist.
        """
        if node_id not in self._nodes:
            raise ValueError(f"Node {node_id} does not exist.")
        return iter(self._adjacency_list[node_id])

    def get_all_nodes(self) -> Iterator[Hashable]:
        """Returns an iterator over all node IDs in the graph."""
        return iter(self._nodes)

    def __contains__(self, node_id: Hashable) -> bool:
        """Checks if a node exists in the graph."""
        return node_id in self._nodes

    def __len__(self) -> int:
        """Returns the number of nodes in the graph."""
        return len(self._nodes)

    def get_nodes_count(self) -> int:
        """Returns the number of nodes in the graph."""
        return len(self._nodes)

    def get_edges_count(self) -> int:
        """Returns the number of edges in the graph."""
        count = 0
        for node in self._adjacency_list:
            count += len(self._adjacency_list[node])
        return count 
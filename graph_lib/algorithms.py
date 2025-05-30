import heapq
from typing import Any, Dict, Hashable, List, Optional, Tuple, Union
from collections import deque

from .graph import Graph


def dijkstra(
    graph: Graph,
    start_node: Hashable,
    end_node: Optional[Hashable] = None
) -> Union[Tuple[Dict[Hashable, float], Dict[Hashable, Optional[Hashable]]], 
             Tuple[Optional[float], List[Hashable]]]:
    """
    Calculates the shortest path from a start_node to all other nodes or to a specific end_node
    using Dijkstra's algorithm.

    Args:
        graph: The graph on which to perform the algorithm.
        start_node: The starting node for the path.
        end_node: Optional. If provided, the algorithm will find the shortest path
                  to this specific node. Otherwise, it finds paths to all reachable nodes.

    Returns:
        If end_node is None:
            A tuple containing two dictionaries:
            - distances: A dictionary mapping each reachable node to its shortest distance
                         from the start_node.
            - predecessors: A dictionary mapping each reachable node to its predecessor
                            in the shortest path from the start_node.
        If end_node is specified:
            A tuple containing:
            - distance: The shortest distance to the end_node (float), or None if not reachable.
            - path: A list of nodes representing the shortest path from start_node to
                    end_node. Empty if not reachable or if start_node is end_node.

    Raises:
        ValueError: If the start_node does not exist in the graph.
        ValueError: If the end_node (if specified) does not exist in the graph.
    """
    if start_node not in graph:
        raise ValueError(f"Start node {start_node} not found in the graph.")
    if end_node is not None and end_node not in graph:
        raise ValueError(f"End node {end_node} not found in the graph.")

    distances: Dict[Hashable, float] = {node: float('inf') for node in graph.get_all_nodes()}
    predecessors: Dict[Hashable, Optional[Hashable]] = {node: None for node in graph.get_all_nodes()}
    distances[start_node] = 0

    # Priority queue stores (distance, node_id)
    priority_queue: List[Tuple[float, Hashable]] = [(0, start_node)]

    while priority_queue:
        current_distance, current_node = heapq.heappop(priority_queue)

        # If we found a shorter path already, skip
        if current_distance > distances[current_node]:
            continue

        # If we are looking for a specific end_node and we found it
        if end_node is not None and current_node == end_node:
            break 

        for neighbor in graph.neighbors(current_node):
            weight = graph.get_edge_weight(current_node, neighbor)
            if weight is None: # Should not happen if graph is well-formed
                continue 
            
            distance = current_distance + weight
            if distance < distances[neighbor]:
                distances[neighbor] = distance
                predecessors[neighbor] = current_node
                heapq.heappush(priority_queue, (distance, neighbor))

    if end_node is not None:
        path: List[Hashable] = []
        if distances[end_node] == float('inf'):
            return None, []  # Not reachable
        
        curr = end_node
        while curr is not None:
            path.insert(0, curr)
            if curr == start_node: # Path reconstruction complete
                break
            curr = predecessors[curr]
        
        # Ensure the path actually starts with start_node if found
        if not path or path[0] != start_node:
             return None, [] # Should ideally not happen if end_node is reachable and not start_node itself

        return distances[end_node], path
    else:
        # Filter out unreachable nodes for the general case
        reachable_distances = {k: v for k, v in distances.items() if v != float('inf')}
        return reachable_distances, predecessors


def bfs(
    graph: Graph,
    start_node: Hashable,
    target_node: Optional[Hashable] = None
) -> Union[List[Hashable], Tuple[Optional[List[Hashable]], Dict[Hashable, Optional[Hashable]]]]:
    """
    Performs a Breadth-First Search on the graph starting from start_node.

    Args:
        graph: The graph to traverse.
        start_node: The node to start the BFS from.
        target_node: Optional. If provided, BFS will stop once the target is found,
                     and the path to the target will be returned. Otherwise, all reachable
                     nodes in BFS order are returned (as a simple list of visited nodes).

    Returns:
        If target_node is None:
            A list of all nodes visited in BFS order from start_node.
        If target_node is specified:
            A tuple containing:
            - path: A list of nodes representing the shortest path (in terms of number of edges)
                    from start_node to target_node. None if not reachable.
            - predecessors: A dictionary mapping each visited node to its predecessor
                            in the BFS tree (useful for reconstructing other paths).

    Raises:
        ValueError: If the start_node does not exist in the graph.
        ValueError: If the target_node (if specified) does not exist in the graph.
    """
    if start_node not in graph:
        raise ValueError(f"Start node {start_node} not found in the graph.")
    if target_node is not None and target_node not in graph:
        raise ValueError(f"Target node {target_node} not found in the graph.")

    queue = deque()
    visited: Set[Hashable] = set()
    predecessors: Dict[Hashable, Optional[Hashable]] = {start_node: None}
    
    queue.append(start_node)
    visited.add(start_node)
    
    # For returning all visited nodes if no target is specified
    visited_in_order: List[Hashable] = [] 

    path_found = False
    while queue:
        current_node = queue.popleft()
        
        if not target_node:
            visited_in_order.append(current_node)

        if target_node is not None and current_node == target_node:
            path_found = True
            break # Target found

        for neighbor in graph.neighbors(current_node):
            if neighbor not in visited:
                visited.add(neighbor)
                predecessors[neighbor] = current_node
                queue.append(neighbor)

    if target_node is not None:
        if path_found:
            path: List[Hashable] = []
            curr = target_node
            while curr is not None:
                path.insert(0, curr)
                if curr == start_node: # Should break once start_node is prepended
                    break
                curr = predecessors.get(curr) # Use .get() to be safe, though curr should be in predecessors
            return path, predecessors
        else:
            return None, predecessors # Target not found
    else:
        return visited_in_order 


def dfs(
    graph: Graph,
    start_node: Hashable,
    target_node: Optional[Hashable] = None,
    # path_found_flag: Optional[List[bool]] = None # Internal helper for recursion if needed
) -> Union[List[Hashable], Tuple[Optional[List[Hashable]], Dict[Hashable, Optional[Hashable]]]]:
    """
    Performs a Depth-First Search on the graph starting from start_node.

    Args:
        graph: The graph to traverse.
        start_node: The node to start the DFS from.
        target_node: Optional. If provided, DFS will stop once the target is found,
                     and the path to the target will be returned. Otherwise, all reachable
                     nodes in one possible DFS order are returned.

    Returns:
        If target_node is None:
            A list of all nodes visited in one possible DFS order from start_node.
        If target_node is specified:
            A tuple containing:
            - path: A list of nodes representing the first path found from start_node
                    to target_node. None if not reachable.
            - predecessors: A dictionary mapping each visited node in the current DFS traversal
                            path up to finding the target (or full traversal) to its predecessor.

    Raises:
        ValueError: If the start_node does not exist in the graph.
        ValueError: If the target_node (if specified) does not exist in the graph.
    """
    if start_node not in graph:
        raise ValueError(f"Start node {start_node} not found in the graph.")
    if target_node is not None and target_node not in graph:
        raise ValueError(f"Target node {target_node} not found in the graph.")

    visited: Set[Hashable] = set()
    dfs_order_visited: List[Hashable] = [] 
    predecessors: Dict[Hashable, Optional[Hashable]] = {}
    
    # Stack for iterative DFS. Stores node to visit.
    stack: List[Hashable] = [start_node]

    path_found_to_target = False

    while stack:
        current_node = stack.pop() # Pop from the end for DFS

        if current_node not in visited:
            visited.add(current_node)
            if not target_node:
                dfs_order_visited.append(current_node)
            
            # For path reconstruction, predecessor is set when node is added to stack IF it was from another node.
            # This is slightly tricky in iterative DFS if not careful. 
            # An alternative for path finding is to store (node, path_so_far) on stack, but can be memory intensive.
            # Let's stick to predecessors dict. The predecessor for start_node is None.
            if current_node == start_node:
                predecessors[current_node] = None

            if target_node is not None and current_node == target_node:
                path_found_to_target = True
                break # Target found, exit DFS loop

            # Add neighbors to stack in reverse order to process them in typical recursive DFS order
            # (e.g., if neighbors are [N1, N2, N3], stack gets N3, N2, N1, so N1 is processed first)
            # However, graph.neighbors() returns an iterator, so order might not be fixed unless sorted.
            # For path finding, any order is fine. For specific traversal order, sorting neighbors might be needed.
            # Let's add them in the order they come for simplicity for now.
            # To mimic recursive call order more closely (often processing first neighbor in list):
            # process neighbors in reverse if you want the first one to be popped and processed first by stack.pop()
            neighbors = list(graph.neighbors(current_node)) # Get all neighbors first
            for neighbor in reversed(neighbors): # Add to stack in reverse order
                if neighbor not in visited: # Add to stack only if not visited
                    # When adding to stack, we know its predecessor
                    predecessors[neighbor] = current_node
                    stack.append(neighbor)
                # If already visited, do nothing - standard DFS for unweighted graphs

    if target_node is not None:
        if path_found_to_target:
            path: List[Hashable] = []
            curr = target_node
            while curr is not None:
                path.insert(0, curr)
                if curr == start_node: break
                curr = predecessors.get(curr)
            # If path doesn't start with start_node (e.g. target was start_node but loop broke before path was just [start_node])
            # or if curr became None before reaching start_node (should not happen if path_found_to_target is True and graph connected)
            if not path or path[0] != start_node:
                 if start_node == target_node: return [start_node], predecessors # Handle s == t explicitly
                 # This case implies target was found but path reconstruction failed, which is an issue.
                 # For now, assume predecessors are correctly built up to the target.
                 pass # Fall through to return reconstructed path if valid
            return path, predecessors
        else:
            return None, predecessors # Target not found
    else:
        return dfs_order_visited 
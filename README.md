# Graph Library

A Python library for graph manipulation and algorithms, with a focus on network-related applications including conceptual OSPF data structures and topology building.

## Features

-   **Core Graph Structure**: A flexible `Graph` class supporting directed graphs, weighted edges, and storage of arbitrary Python objects as node data.
-   **Graph Algorithms**:
    -   Dijkstra's Algorithm: For finding the shortest paths in a weighted graph.
    -   Breadth-First Search (BFS): For shortest path in terms of edges and graph traversal.
    -   Depth-First Search (DFS): For pathfinding, cycle detection, and graph traversal.
-   **OSPF Functionality (Conceptual)**:
    -   Data structures for OSPF Link State Advertisements (LSAs - Type 1 Router LSA, Type 2 Network LSA).
    -   Representations for OSPF Routers, Interfaces, and Areas.
    -   Function to build an OSPF intra-area topology graph from router configurations (currently P2P links).
-   **Unit Tests**: Comprehensive test suite using `pytest` to ensure reliability.
-   **Pip Installable**: Packaged using `setuptools` and `pyproject.toml` for easy installation.

## Installation

Currently, the library can be installed from source or used directly in a project.

To install dependencies for development (like `pytest`):
```bash
# Ensure you are in your project's virtual environment
pip install -r requirements.txt
```

(Once published to PyPI, installation will be via `pip install graph-lib`)

## Usage Examples

### Basic Graph Operations

```python
from graph_lib import Graph

# Create a graph
g = Graph()

# Add nodes
g.add_node("RouterA", data={"model": "Cisco 123", "location": "NY"})
g.add_node("RouterB")
g.add_node("RouterC", data={"location": "LA"})

# Add weighted edges
g.add_edge("RouterA", "RouterB", weight=10)
g.add_edge("RouterB", "RouterC", weight=5)
g.add_edge("RouterA", "RouterC", weight=20) # A direct, more expensive link

# Get node data
print(f"Router A Data: {g.get_node_data('RouterA')}")

# Get neighbors
print(f"Neighbors of RouterA: {list(g.neighbors('RouterA'))}")

# Check if a node exists
if "RouterB" in g:
    print("RouterB exists in the graph.")

# Get number of nodes and edges
print(f"Number of nodes: {len(g)}")
print(f"Number of edges: {g.get_edges_count()}")
```

### Using Graph Algorithms

```python
from graph_lib import Graph, dijkstra, bfs, dfs

# (Assuming graph 'g' is created and populated as above)

# Dijkstra's Algorithm (shortest path by weight)
# Path from RouterA to RouterC
dist_ac, path_ac_dijkstra = dijkstra(g, "RouterA", "RouterC")
if dist_ac is not None:
    print(f"Dijkstra: Shortest path from RouterA to RouterC is {path_ac_dijkstra} with cost {dist_ac}")
    # Expected: ['RouterA', 'RouterB', 'RouterC'] with cost 15

# All shortest paths from RouterA
distances_from_a, predecessors_a = dijkstra(g, "RouterA")
print(f"Distances from RouterA: {distances_from_a}")

# Breadth-First Search (BFS - shortest path by number of edges)
path_ac_bfs, _ = bfs(g, "RouterA", "RouterC")
if path_ac_bfs:
    print(f"BFS: Path from RouterA to RouterC is {path_ac_bfs}")
    # Expected: Can be ['RouterA', 'RouterC'] if it explores that first, or ['RouterA', 'RouterB', 'RouterC']
    # If ['RouterA', 'RouterC'] is found, len=2. If ['RouterA', 'RouterB', 'RouterC'], len=3.
    # BFS finds shortest in terms of *number of edges*.

# Get all nodes reachable by BFS from RouterA
visited_bfs = bfs(g, "RouterA")
print(f"Nodes reachable from RouterA (BFS order): {visited_bfs}")

# Depth-First Search (DFS - finds a path)
path_ac_dfs, _ = dfs(g, "RouterA", "RouterC")
if path_ac_dfs:
    print(f"DFS: Path from RouterA to RouterC is {path_ac_dfs}")

# Get all nodes reachable by DFS from RouterA
visited_dfs = dfs(g, "RouterA")
print(f"Nodes reachable from RouterA (DFS order): {visited_dfs}")
```

### OSPF Functionality (Conceptual Example)

```python
from graph_lib import (
    OSPFRouter, OSPFInterface, OSPFArea, 
    RouterID, IPAddress, AreaID, OSPFInterfaceState,
    build_ospf_graph_from_routers, dijkstra
)

# Define Routers and their OSPF interfaces
r1 = OSPFRouter(router_id=RouterID("1.1.1.1"))
r1.add_interface(OSPFInterface(
    ip_address=IPAddress("10.0.1.1"), 
    network_mask=IPAddress("255.255.255.252"), 
    area_id=AreaID("0.0.0.0"), 
    cost=10, 
    network_type=OSPFInterfaceState.POINT_TO_POINT, 
    neighbor_router_id=RouterID("2.2.2.2")
))

r2 = OSPFRouter(router_id=RouterID("2.2.2.2"))
r2.add_interface(OSPFInterface(
    ip_address=IPAddress("10.0.1.2"), 
    network_mask=IPAddress("255.255.255.252"), 
    area_id=AreaID("0.0.0.0"), 
    cost=10, 
    network_type=OSPFInterfaceState.POINT_TO_POINT, 
    neighbor_router_id=RouterID("1.1.1.1")
))
r2.add_interface(OSPFInterface(
    ip_address=IPAddress("10.0.2.1"), 
    network_mask=IPAddress("255.255.255.252"), 
    area_id=AreaID("0.0.0.0"), 
    cost=5, 
    network_type=OSPFInterfaceState.POINT_TO_POINT, 
    neighbor_router_id=RouterID("3.3.3.3")
))

r3 = OSPFRouter(router_id=RouterID("3.3.3.3"))
r3.add_interface(OSPFInterface(
    ip_address=IPAddress("10.0.2.2"), 
    network_mask=IPAddress("255.255.255.252"), 
    area_id=AreaID("0.0.0.0"), 
    cost=5, 
    network_type=OSPFInterfaceState.POINT_TO_POINT, 
    neighbor_router_id=RouterID("2.2.2.2")
))

all_routers = [r1, r2, r3]

# Create an OSPF Area object
area0 = OSPFArea(area_id=AreaID("0.0.0.0"))

# Build the intra-area topology graph
area0.build_intra_area_topology(all_domain_routers=all_routers)
ospf_topology_graph = area0.topology_graph

if ospf_topology_graph:
    print(f"OSPF Area 0 has {len(ospf_topology_graph)} routers in its topology.")
    # Calculate shortest path from R1 to R3 in Area 0
    dist_r1_r3, path_r1_r3 = dijkstra(ospf_topology_graph, RouterID("1.1.1.1"), RouterID("3.3.3.3"))
    if dist_r1_r3 is not None:
        print(f"Shortest path from R1 to R3 in Area 0: {path_r1_r3} with OSPF cost {dist_r1_r3}")
        # Expected: ['1.1.1.1', '2.2.2.2', '3.3.3.3'] with cost 15
```

## API Reference

### `graph_lib.Graph`

Represents a directed graph.

-   `__init__(self)`: Initializes an empty graph.
-   `add_node(self, node_id: Hashable, data: Optional[Any] = None)`: Adds a node. Raises `ValueError` if node exists.
-   `get_node_data(self, node_id: Hashable) -> Optional[Any]`: Retrieves data for a node. Raises `ValueError` if node doesn't exist.
-   `add_edge(self, u: Hashable, v: Hashable, weight: float = 1.0)`: Adds a directed edge from `u` to `v`. Creates nodes if they don't exist.
-   `get_edge_weight(self, u: Hashable, v: Hashable) -> Optional[float]`: Returns weight of edge `u`->`v`, or `None`.
-   `neighbors(self, node_id: Hashable) -> Iterator[Hashable]`: Iterator over neighbors of `node_id`. Raises `ValueError` if node doesn't exist.
-   `get_all_nodes(self) -> Iterator[Hashable]`: Iterator over all node IDs.
-   `__contains__(self, node_id: Hashable) -> bool`: Checks if `node_id` is in the graph (`node in graph`).
-   `__len__(self) -> int`: Returns number of nodes (`len(graph)`).
-   `get_nodes_count(self) -> int`: Returns number of nodes.
-   `get_edges_count(self) -> int`: Returns number of edges.

### `graph_lib.algorithms`

-   `dijkstra(graph: Graph, start_node: Hashable, end_node: Optional[Hashable] = None)`:
    -   Calculates shortest paths using Dijkstra's algorithm.
    -   If `end_node` is `None`: returns `(distances_dict, predecessors_dict)` for all reachable nodes.
    -   If `end_node` is specified: returns `(cost, path_list)`. `cost` is `None` if not reachable.
-   `bfs(graph: Graph, start_node: Hashable, target_node: Optional[Hashable] = None)`:
    -   Performs Breadth-First Search.
    -   If `target_node` is `None`: returns a list of visited nodes in BFS order.
    -   If `target_node` is specified: returns `(path_list, predecessors_dict)`. `path_list` is `None` if not reachable.
-   `dfs(graph: Graph, start_node: Hashable, target_node: Optional[Hashable] = None)`:
    -   Performs Depth-First Search.
    -   If `target_node` is `None`: returns a list of visited nodes in DFS (pre-order) traversal.
    -   If `target_node` is specified: returns `(path_list, predecessors_dict)`. `path_list` is `None` if not reachable.

### `graph_lib.ospf` (Conceptual OSPF Structures)

**Type Aliases:**
-   `IPAddress = NewType("IPAddress", str)`
-   `RouterID = NewType("RouterID", str)` (Typically an IPv4 formatted string)
-   `AreaID = NewType("AreaID", str)` (Typically an IPv4 formatted string or uint32)

**Enums:**
-   `LSAType(Enum)`: OSPF LSA types (e.g., `ROUTER_LSA`, `NETWORK_LSA`).
-   `RouterLSALinkType(Enum)`: Types of links in a Router LSA (e.g., `POINT_TO_POINT`, `TRANSIT_NETWORK`).
-   `OSPFInterfaceState(Enum)`: OSPF network types and interface states (e.g., `POINT_TO_POINT`, `BROADCAST`, `DR`, `BDR`).

**Dataclasses:**
-   `LSAHeader`: Base class for LSA headers. Fields: `ls_age`, `options`, `ls_type`, `link_state_id`, `advertising_router`, `ls_sequence_number`, `ls_checksum`, `length`.
-   `RouterLSALink`: Represents a link in a Router LSA. Fields: `link_id`, `link_data`, `link_type`, `metric`.
-   `RouterLSA(LSAHeader)`: Represents a Type 1 Router LSA. Fields: `is_virtual_link_endpoint`, `is_asbr`, `is_abr`, `links: List[RouterLSALink]`.
-   `NetworkLSA(LSAHeader)`: Represents a Type 2 Network LSA. Fields: `network_mask`, `attached_routers: List[RouterID]`.
-   `OSPFInterface`: Configuration for an OSPF interface. Fields: `ip_address`, `network_mask`, `area_id`, `network_type`, `cost`, `current_ospf_state`, `hello_interval`, `dead_interval`, `priority`, `neighbor_router_id`, `neighbor_interface_ip`.
-   `OSPFRouter`: Represents an OSPF router. Fields: `router_id`, `interfaces: List[OSPFInterface]`.
    -   `add_interface(self, interface: OSPFInterface)`
    -   `originate_router_lsa(self, area_id: AreaID) -> Optional[RouterLSA]` (Conceptual placeholder)
    -   `originate_network_lsa(self, interface_ip: IPAddress) -> Optional[NetworkLSA]` (Conceptual placeholder)
-   `OSPFArea`: Represents an OSPF area. Fields: `area_id`, `routers_in_area: List[OSPFRouter]`, `topology_graph: Optional[Graph]`, `lsdb`.
    -   `build_intra_area_topology(self, all_domain_routers: Optional[List[OSPFRouter]] = None)`
    -   `add_lsa_to_lsdb(self, lsa: Union[RouterLSA, NetworkLSA, LSAHeader])`

**Functions:**
-   `build_ospf_graph_from_routers(routers: List[OSPFRouter], target_area_id: AreaID) -> Graph`:
    -   Constructs an intra-area OSPF topology graph from router configurations.
    -   Currently supports Point-to-Point links.

## Running Tests

To run the unit tests, ensure `pytest` is installed (see Installation) and then run from the project root directory:

```bash
pytest
```

## Contributing

(Placeholder for contribution guidelines - e.g., fork, branch, PR)

## License

This project is licensed under the MIT License - see the `LICENSE` file for details (if one is created).
(Currently, `pyproject.toml` specifies MIT License classification). 
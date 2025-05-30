# GraphLib Developer Guide

This guide provides information for developers working on or contributing to the GraphLib project. It covers the codebase structure, key modules, development practices, and how to extend the library.

## Table of Contents

1.  [Introduction](#introduction)
2.  [Codebase Structure](#codebase-structure)
3.  [Key Modules and Components](#key-modules-and-components)
    *   [3.1. `graph_lib/graph.py`](#31-graph_libgraphpy)
    *   [3.2. `graph_lib/algorithms.py`](#32-graph_libalgorithmspy)
    *   [3.3. `graph_lib/ospf.py`](#33-graph_libospfpy)
    *   [3.4. `graph_lib/mininet_importer.py`](#34-graph_libmininet_importerpy)
4.  [Development Environment](#development-environment)
5.  [Coding Conventions and Style](#coding-conventions-and-style)
6.  [Running Tests](#running-tests)
7.  [Contribution Guidelines](#contribution-guidelines)
8.  [Areas for Future Development](#areas-for-future-development)

## 1. Introduction

GraphLib aims to provide a simple yet effective set of tools for graph manipulation and network protocol simulation, particularly OSPF. The design emphasizes clarity and modularity to facilitate understanding and extension.

## 2. Codebase Structure

The project is organized as follows:

```
graphlib/
├── graph_lib/            # Main library source code
│   ├── __init__.py       # Makes graph_lib a Python package
│   ├── algorithms.py   # Graph algorithms (Dijkstra)
│   ├── graph.py        # Core Graph class and related types
│   ├── mininet_importer.py # Mininet topology and OSPF simulation script
│   └── ospf.py         # OSPF data structures and simulation logic
├── tests/                # Directory for unit and integration tests
│   └── ...               # (Test files, e.g., test_graph.py, test_ospf.py)
├── docs/                 # Documentation files
│   ├── user_guide.md     # Guide for end-users
│   └── developer_guide.md # This guide
├── README.md             # Project overview and entry point
└── requirements.txt      # Python package dependencies (if any beyond Mininet)
```

## 3. Key Modules and Components

### 3.1. `graph_lib/graph.py`

*   **Purpose:** Defines the fundamental `Graph` class.
*   **Core Class:** `Graph`
    *   **Representation:** Uses dictionaries to store nodes (`_nodes`) and an adjacency list (`_adjacency_list`).
        *   `_nodes: Dict[Hashable, Any]` maps node IDs to their associated data.
        *   `_adjacency_list: Dict[Hashable, Dict[Hashable, float]]` maps a node ID to a dictionary of its neighbors, where each neighbor is mapped to the edge weight.
    *   **Key Methods:**
        *   `add_node(node_id, data=None)`: Adds a node.
        *   `get_node_data(node_id)`: Retrieves data for a node.
        *   `add_edge(u, v, weight=1.0)`: Adds a directed edge with a weight.
        *   `get_edge_weight(u, v)`: Gets the weight of an edge.
        *   `has_node(node_id)`: Checks for node existence.
        *   `has_edge(u, v)`: Checks for edge existence.
        *   `neighbors(node_id)`: Iterates over neighbors of a node.
        *   `get_all_nodes()`: Iterates over all nodes.
        *   `get_all_edges(include_weights=False)`: Iterates over all edges (optionally with weights).
        *   `get_nodes_count()`, `get_edges_count()`: Return counts.
*   **Type Aliases:** Basic types like `NodeID` might be defined here or in `__init__.py` if shared more broadly.

### 3.2. `graph_lib/algorithms.py`

*   **Purpose:** Contains implementations of common graph algorithms.
*   **Key Functions:**
    *   `dijkstra(graph, start_node, end_node=None)`: Implements Dijkstra's algorithm. Returns path cost and path list to a specific end node, or dictionaries of distances and predecessors if no end node is specified.

### 3.3. `graph_lib/ospf.py`

*   **Purpose:** Implements OSPF-specific data structures and simulation logic for an intra-area OSPF network.
*   **Key Dataclasses & Enums:**
    *   `IPAddress`, `RouterID`, `NetworkID`, `PseudoNodeID`, `NodeID`, `AreaID`: `NewType` aliases for type hinting.
    *   `LSAType`: Enum for LSA types (Router, Network).
    *   `LSAHeader`: Dataclass for common LSA header fields.
    *   `RouterLSALinkType`, `RouterLSALink`: For links within a Router LSA.
    *   `RouterLSA`, `NetworkLSA`: Dataclasses for Type 1 and Type 2 LSAs, including methods to calculate their length.
    *   `OSPFInterfaceState`: Enum for OSPF interface types/states (P2P, Broadcast, DR, etc.).
    *   `OSPFInterface`: Dataclass for OSPF interface configuration (IP, mask, area, cost, state, etc.).
    *   `OSPFRouter`: Dataclass representing an OSPF router, its interfaces, and methods to originate LSAs (`originate_router_lsa`, `originate_network_lsa`).
    *   `SPFResult`: `namedtuple` (`cost`, `next_hop_router_id`) for storing SPF results.
    *   `OSPFArea`: Core class managing an OSPF area.
        *   `lsdb`: Stores the Link State Database for the area.
        *   `topology_graph`: The graph built from the LSDB for SPF calculation.
        *   `routing_table`: Stores the results of SPF (source router -> destination -> SPFResult).
        *   `add_lsa_to_lsdb()`: Adds/updates LSAs, implementing basic LSA preference rules and triggering SPF.
        *   `build_area_topology_from_lsdb()`: Calls `build_ospf_graph_from_lsdb`.
        *   `recalculate_spf()`: Runs Dijkstra on the `topology_graph` and populates `routing_table`.
*   **Key Functions:**
    *   `build_ospf_graph_from_lsdb()`: Constructs the SPF graph. Routers are nodes. Transit networks are represented by pseudo-nodes. Edges are weighted by OSPF cost.
    *   `get_network_address()`: Utility to calculate network address from IP and mask.

### 3.4. `graph_lib/mininet_importer.py`

*   **Purpose:** Serves as an executable script to demonstrate OSPF simulation using Mininet.
*   **Key Functions:**
    *   `create_custom_topology()`: Defines and creates a specific Mininet network topology.
    *   `enable_ip_forwarding()`: Helper to enable IP forwarding on Mininet hosts acting as routers.
    *   `extract_topology_for_ospf()`: The core logic that:
        *   Initializes `OSPFRouter` and `OSPFArea` objects.
        *   Performs a simplified DR election for broadcast segments connected via Mininet switches.
        *   Populates `OSPFInterface` details for each router based on Mininet link/interface info.
        *   Triggers LSA origination from `OSPFRouter` instances.
        *   Adds generated LSAs to the `OSPFArea`'s LSDB, which in turn triggers graph building and SPF.
    *   `mininet_to_generic_graph()`: Converts the Mininet router topology to a basic `graph_lib.Graph` object.
    *   **Main Block (`if __name__ == '__main__':`)**: Orchestrates the setup, Mininet start, OSPF simulation, output printing, and Mininet cleanup.

## 4. Development Environment

*   **Python Version:** Python 3.x (as used by Mininet).
*   **Mininet:** A working Mininet installation is crucial for running and testing `mininet_importer.py`.
*   **Virtual Environment:** Strongly recommended (see [User Guide](./user_guide.md#setup)).
*   **Linters/Formatters:** Consider using tools like Black for code formatting and Flake8 or Pylint for linting to maintain code quality and consistency.

## 5. Coding Conventions and Style

*   Follow [PEP 8 -- Style Guide for Python Code](https://www.python.org/dev/peps/pep-0008/).
*   Use type hints extensively (as currently practiced in the codebase) for better readability and static analysis.
*   Write clear and concise docstrings for modules, classes, and functions (Google Style or reStructuredText preferred).
*   Aim for modular design where components are loosely coupled and have well-defined responsibilities.

## 6. Running Tests

(Assuming tests are or will be written, e.g., using `pytest`)

1.  Ensure your development virtual environment is activated.
2.  Install testing dependencies (e.g., `pip install pytest`).
3.  Navigate to the project root directory.
4.  Run tests using:
    ```bash
    pytest
    ```
    Or specify a particular test file:
    ```bash
    pytest tests/test_graph.py
    ```

## 7. Contribution Guidelines

1.  **Fork the Repository:** If contributing to a shared project.
2.  **Create a Feature Branch:** `git checkout -b feature/your-new-feature` or `bugfix/issue-number`.
3.  **Develop your Changes:** Implement new features or bug fixes.
    *   Write clean, well-documented code.
    *   Add unit tests for new functionality or bug fixes.
    *   Ensure all existing tests pass.
4.  **Commit your Changes:** Use clear and descriptive commit messages.
5.  **Push to your Branch:** `git push origin feature/your-new-feature`.
6.  **Open a Pull Request (PR):** Against the main development branch of the original repository.
    *   Provide a clear description of the changes in the PR.
    *   Reference any relevant issues.

## 8. Areas for Future Development

*   **Enhanced OSPF Features:**
    *   Support for more LSA types (Summary LSAs, AS-External LSAs).
    *   Multi-area OSPF simulations.
    *   More realistic DR/BDR election (considering priority, Hello protocol simulation).
    *   LSA aging and flushing mechanisms in the LSDB.
    *   More robust checksum calculation for LSAs.
*   **Graph Algorithms:** Implementation of other relevant graph algorithms (e.g., Bellman-Ford, Floyd-Warshall, cycle detection).
*   **Testing:**
    *   Comprehensive unit tests for all modules, especially `ospf.py` logic.
    *   Integration tests for `mininet_importer.py`.
*   **Usability & API:**
    *   Refine the API of `graph.py` and `ospf.py` for easier external use.
    *   More sophisticated network visualization capabilities.
*   **Error Handling and Logging:** More granular error handling and configurable logging throughout the library.
*   **Packaging:** If intended for wider distribution, ensure robust packaging and potential publication to PyPI.

---
This guide should help developers understand and contribute to GraphLib effectively. 
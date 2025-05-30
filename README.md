# GraphLib: A Network Graph and OSPF Simulation Library

GraphLib is a Python library for creating, manipulating, and analyzing network graphs. It includes a foundational graph module, implementations of graph algorithms like Dijkstra's, and a module for simulating the Open Shortest Path First (OSPF) routing protocol. Additionally, it features an importer to create network topologies using Mininet and simulate OSPF on them.

## Features

*   **Generic Graph Library (`graph_lib/graph.py`):**
    *   Create directed graphs.
    *   Add nodes and weighted edges.
    *   Store arbitrary data with nodes.
    *   Basic graph inspection methods (node count, edge count, neighbors, etc.).
*   **Graph Algorithms (`graph_lib/algorithms.py`):**
    *   Dijkstra's algorithm for finding shortest paths.
*   **OSPF Simulation (`graph_lib/ospf.py`):**
    *   Dataclasses for OSPF concepts: LSAs (Router, Network), Interfaces, Routers, Areas.
    *   LSA origination (Router LSA, Network LSA).
    *   LSDB management within an OSPF Area.
    *   Construction of an OSPF topology graph from an LSDB.
    *   SPF (Dijkstra's) calculation to produce routing tables.
*   **Mininet Importer & OSPF Simulation Runner (`graph_lib/mininet_importer.py`):**
    *   Defines a sample Mininet topology.
    *   Extracts topology information and converts it to OSPF data structures.
    *   Performs a simplified Designated Router (DR) election.
    *   Runs an OSPF simulation on the Mininet topology:
        *   LSA generation and LSDB population.
        *   SPF calculation.
        *   Displays resulting routing tables.
    *   Optionally converts the Mininet topology to a generic `Graph` object.
    *   Allows control over Mininet CLI interaction via the `INTERACTIVE_MININET_CLI` environment variable.

## Project Structure

```
graphlib/
├── graph_lib/
│   ├── __init__.py
│   ├── algorithms.py   # Graph algorithms (Dijkstra)
│   ├── graph.py        # Core graph data structure
│   ├── mininet_importer.py # Mininet topology creation and OSPF simulation
│   └── ospf.py         # OSPF protocol simulation components
├── tests/
│   └── ...             # Unit tests (structure may vary)
├── docs/
│   ├── user_guide.md
│   └── developer_guide.md
├── README.md           # This file
└── requirements.txt    # Project dependencies (if any beyond standard Mininet)
```

## Getting Started

### Prerequisites

*   Python 3.x
*   Mininet (for running `mininet_importer.py`)
*   A Python virtual environment is recommended.

### Installation / Setup

1.  **Clone the repository (if applicable):**
    ```bash
    git clone <repository_url>
    cd graphlib
    ```

2.  **Set up a Python virtual environment:**
    ```bash
    python3 -m venv /opt/pyvenv  # Or your preferred path
    source /opt/pyvenv/bin/activate
    ```
    If you have a `requirements.txt`, install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

### Running the Mininet OSPF Simulation

The main demonstration script is `graph_lib/mininet_importer.py`. It creates a Mininet topology, configures OSPF on the routers, and simulates the protocol.

To run the simulation (from the project root directory, e.g., `graphlib/`):

*   **If your virtual environment is at `/opt/pyvenv/` and not activated:**
    ```bash
    sudo /opt/pyvenv/bin/python -m graph_lib.mininet_importer
    ```
*   **If your virtual environment is activated in the current shell:**
    ```bash
    sudo python -m graph_lib.mininet_importer
    ```

To interact with the Mininet CLI after the script runs the simulation, set the environment variable:
```bash
sudo INTERACTIVE_MININET_CLI=1 /opt/pyvenv/bin/python -m graph_lib.mininet_importer
```

## Documentation

For more detailed information, please refer to:

*   **[User Guide](./docs/user_guide.md):** Instructions on using the library and running simulations.
*   **[Developer Guide](./docs/developer_guide.md):** Information for contributors and those looking to understand the internals.

## Contributing

Please refer to the [Developer Guide](./docs/developer_guide.md) for contribution guidelines.

## License

(Specify your project's license here, e.g., MIT, Apache 2.0) 
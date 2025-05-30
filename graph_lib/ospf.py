from dataclasses import dataclass, field
from enum import Enum
from typing import List, Union, NewType, Optional, Dict, Tuple

# Represents an IP address, typically stored as a string for simplicity here.
# In a more complete implementation, this might be an IPv4Address or IPv6Address object.
IPAddress = NewType("IPAddress", str)
RouterID = NewType("RouterID", str) # OSPF Router ID, typically in IPv4 format

class LSAType(Enum):
    ROUTER_LSA = 1
    NETWORK_LSA = 2
    SUMMARY_LSA_NET = 3
    SUMMARY_LSA_ASBR = 4
    AS_EXTERNAL_LSA = 5
    # Other types (NSSA, Opaque LSAs) can be added as needed

@dataclass
class LSAHeader:
    ls_age: int = 0               # In seconds, max 3600 (LSMaxAge)
    options: int = 0              # Options field (e.g., E-bit for AS-external-LSA)
    ls_type: LSAType = LSAType.ROUTER_LSA
    link_state_id: Union[IPAddress, RouterID] = field(default_factory=str) # Meaning depends on LSA type
    advertising_router: RouterID = field(default_factory=str) # Router ID of the originator
    ls_sequence_number: int = 0   # Signed 32-bit integer, starts with 0x80000001
    ls_checksum: int = 0          # Fletcher checksum of the LSA content (excluding ls_age)
    length: int = 0               # Length in bytes, including the header

    def __post_init__(self):
        # Basic validation or default setting
        if not isinstance(self.ls_type, LSAType):
            raise TypeError("ls_type must be an instance of LSAType Enum")
        # Length of header is typically 20 bytes
        # Actual length is header (20) + body. Specific LSA types will set this.
        if self.length == 0 and type(self) == LSAHeader:
            self.length = 20 # Default for a bare header

# --- Router LSA (Type 1) --- #

class RouterLSALinkType(Enum):
    POINT_TO_POINT = 1
    TRANSIT_NETWORK = 2  # Connection to a transit network (DR exists)
    STUB_NETWORK = 3     # Connection to a stub network (no other routers)
    VIRTUAL_LINK = 4

@dataclass
class RouterLSALink:
    link_id: Union[RouterID, IPAddress] # Neighbor Router ID or IP Address of DR or Network IP
    link_data: Union[IPAddress, int] # Interface IP Address or Subnet Mask (if stub, then network IP)
                                     # For unnumbered P2P, this is Interface ID / MIB-II ifIndex
    link_type: RouterLSALinkType
    metric: int # Cost of this link
    # TOS (Type of Service) metrics can be added if needed

@dataclass
class RouterLSA(LSAHeader):
    # Flags: V (Virtual Link endpoint), E (ASBR), B (ABR)
    is_virtual_link_endpoint: bool = False
    is_asbr: bool = False 
    is_abr: bool = False
    links: List[RouterLSALink] = field(default_factory=list)

    def __post_init__(self):
        super().__post_init__()
        self.ls_type = LSAType.ROUTER_LSA
        # Link State ID for Router LSA is the originating Router ID itself
        if not self.link_state_id: # if not set by user
            self.link_state_id = self.advertising_router
        self._calculate_length()

    def _calculate_length(self):
        # Header (20 bytes) + flags (2 bytes, though OSPFv2 packs it in 1 for V,E,B + 1 reserved) + num_links (2 bytes) + links data
        # For simplicity, assume flags and num_links are part of the body calc
        # OSPF Router LSA body starts with 2 bytes for flags (V, E, B, and 5 reserved bits) and 2 bytes for # links
        # Then each link is 12 bytes: Link ID (4), Link Data (4), Type (1), #TOS (1), Metric (2)
        # (We are simplifying TOS for now, so Type(1), Reserved(1), Metric(2))
        body_length = 4 # V/E/B flags (simplified as bools, but would be bitmask) + Number of Links (implicit from list len)
        body_length += sum(12 for _ in self.links) # Each link approx 12 bytes
        self.length = 20 + body_length

    def add_link(self, link: RouterLSALink):
        self.links.append(link)
        self._calculate_length()

# --- Network LSA (Type 2) --- #

@dataclass
class NetworkLSA(LSAHeader):
    network_mask: IPAddress = field(default_factory=str) # Subnet mask of the transit network
    attached_routers: List[RouterID] = field(default_factory=list) # RIDs of routers on this network (incl. DR)

    def __post_init__(self):
        super().__post_init__()
        self.ls_type = LSAType.NETWORK_LSA
        # Link State ID for Network LSA is the IP Interface Address of the DR
        # (Here, we expect it to be set appropriately by the caller, or derived)
        self._calculate_length()

    def _calculate_length(self):
        # Header (20 bytes) + Network Mask (4 bytes) + Attached Routers (4 bytes each)
        body_length = 4 # Network Mask
        body_length += len(self.attached_routers) * 4 # Each RouterID
        self.length = 20 + body_length

    def add_attached_router(self, router_id: RouterID):
        if router_id not in self.attached_routers:
            self.attached_routers.append(router_id)
            self._calculate_length()

# --- OSPF Router and Interface Configuration --- #

AreaID = NewType("AreaID", str) # Typically an IP address or a 32-bit number

class OSPFInterfaceState(Enum):
    DOWN = 0
    LOOPBACK = 1
    WAITING = 2
    POINT_TO_POINT = 3 # Indicates the network type is P2P for OSPF
    BROADCAST = 4      # Indicates the network type is Broadcast (DR/BDR election occurs)
    NBMA = 5           # Non-Broadcast Multi-Access (DR/BDR election occurs)
    POINT_TO_MULTIPOINT = 6
    # Interface states on a segment (result of DR election etc.)
    DR_OTHER = 7 # OSPF state machine state on interface
    BDR = 8
    DR = 9

@dataclass
class OSPFInterface:
    ip_address: IPAddress
    network_mask: IPAddress
    area_id: AreaID
    network_type: OSPFInterfaceState = OSPFInterfaceState.BROADCAST # Default to broadcast
    cost: int = 10
    # State after DR election, or for P2P link FSM.
    # For simplicity, we might just use network_type to decide link formation for now.
    current_ospf_state: OSPFInterfaceState = OSPFInterfaceState.DR_OTHER 
    hello_interval: int = 10 # seconds
    dead_interval: int = 40  # seconds
    priority: int = 1        # Router priority for DR/BDR election
    
    # For point-to-point links, explicitly define the peer
    # This helps in manually constructing the topology graph
    neighbor_router_id: Optional[RouterID] = None
    neighbor_interface_ip: Optional[IPAddress] = None # For matching P2P if needed

@dataclass
class OSPFRouter:
    router_id: RouterID
    interfaces: List[OSPFInterface] = field(default_factory=list)
    # Link State Database (LSDB) for this router, could be per area
    # lsdb: Dict[AreaID, Dict[Tuple[LSAType, RouterID, IPAddress], Union[RouterLSA, NetworkLSA, ...]]] = field(default_factory=dict)

    def add_interface(self, interface: OSPFInterface):
        self.interfaces.append(interface)

    # Conceptual: A real OSPF implementation would build LSAs from its interface states and LSDB
    def originate_router_lsa(self, area_id: AreaID) -> Optional[RouterLSA]:
        """Conceptual: Originates a Router LSA for its links in a given area."""
        links_in_area = []
        # This is highly simplified. Real LSA generation is complex.
        for iface in self.interfaces:
            if iface.area_id == area_id:
                # Determine link type, link_id, link_data based on interface state, network type, neighbors
                # This requires a more dynamic view of the network which we don't have yet
                # For now, let's imagine a point-to-point link for simplicity if we had a neighbor concept here
                pass # Placeholder
        
        if not links_in_area: # No interfaces in this area or no links formed
            # Still, a router LSA might be originated if the router itself is in the area,
            # possibly with no links or just stub links if configured
            pass 

        # For now, this function is a placeholder for the complex LSA generation logic.
        # Actual LSA generation would involve checking adjacencies, DR status, etc.
        # For example, a link to a transit network involves the DR's IP as Link ID.
        # A link to a P2P neighbor involves the neighbor's Router ID.
        # A stub link involves the network IP/mask.
        
        # Example of how one might start building it:
        # router_lsa = RouterLSA(
        #     advertising_router=self.router_id, 
        #     link_state_id=self.router_id, # For Router LSA, LSID is its own RID
        #     # ... other header fields ...
        #     links=links_in_area
        # )
        # router_lsa._calculate_length() # Ensure length is set
        # return router_lsa
        return None # Placeholder until more logic is added

    def originate_network_lsa(self, interface_ip: IPAddress) -> Optional[NetworkLSA]:
        """Conceptual: Originates a Network LSA if this router is DR on that segment."""
        # Find the interface
        target_iface = next((iface for iface in self.interfaces if iface.ip_address == interface_ip), None)
        if not target_iface or target_iface.current_ospf_state != OSPFInterfaceState.DR:
            return None # Only DR originates Network LSAs

        # Attached routers would be discovered via Hello protocol on this segment
        # For now, this list would need to be populated manually or by a higher-level process
        attached_routers_on_segment: List[RouterID] = [] # Placeholder
        # if self.router_id not in attached_routers_on_segment: # DR includes itself
        #    attached_routers_on_segment.append(self.router_id)

        # network_lsa = NetworkLSA(
        #     advertising_router=self.router_id,
        #     link_state_id=target_iface.ip_address, # For Network LSA, LSID is DR's interface IP
        #     network_mask=target_iface.network_mask,
        #     attached_routers=attached_routers_on_segment
        #     # ... other header fields ...
        # )
        # network_lsa._calculate_length()
        # return network_lsa
        return None # Placeholder 

# --- OSPF Topology Building --- #

from graph_lib.graph import Graph # Ensure Graph is imported if not already at top level of module

def build_ospf_graph_from_routers(routers: List[OSPFRouter], target_area_id: AreaID) -> Graph:
    """
    Builds a topology graph for a specific OSPF area from a list of OSPFRouter objects.
    Nodes in the graph are RouterIDs. Node data is the OSPFRouter object.
    Edges represent OSPF links with costs as weights.

    Currently focuses on Point-to-Point links based on neighbor_router_id.
    Transit networks (Broadcast/NBMA) with DRs and pseudo-nodes will be a future addition.
    """
    g = Graph()

    # Add all routers in the target area as nodes
    routers_in_area_map: Dict[RouterID, OSPFRouter] = {}
    for router in routers:
        # A router is considered part of the area if any of its interfaces are in that area.
        # For graph construction, we add the router if it *could* participate.
        # The LSAs it generates would be area-specific.
        is_in_target_area = any(iface.area_id == target_area_id for iface in router.interfaces)
        if is_in_target_area:
            if router.router_id not in g:
                g.add_node(router.router_id, data=router)
            routers_in_area_map[router.router_id] = router

    # Add edges for point-to-point links within the target area
    for router_id, router_obj in routers_in_area_map.items():
        for iface in router_obj.interfaces:
            if iface.area_id == target_area_id and \
               iface.network_type == OSPFInterfaceState.POINT_TO_POINT and \
               iface.neighbor_router_id:
                
                # Check if neighbor is also in the target area and exists in our map
                if iface.neighbor_router_id in routers_in_area_map:
                    # Add directed edge from current router to neighbor
                    # Cost is taken from the current router's interface
                    g.add_edge(router_id, iface.neighbor_router_id, weight=iface.cost)
                    
                    # Conceptual: In real OSPF, an adjacency requires bidirectional checks
                    # and matching interface parameters. Here we assume if one side is defined
                    # to point to a known router, the link is up for graph purposes.
                    # A more robust check would find the neighbor's corresponding interface
                    # and ensure it also points back and parameters match.

    # TODO: Handle Transit Networks (Broadcast, NBMA)
    # This would involve: 
    # 1. Identifying DR for each transit segment in the target area.
    # 2. Creating a pseudo-node for each transit segment (Network LSA representation).
    #    - Node ID for pseudo-node could be f"net_{DR_IP_on_segment}"
    #    - Node data could be the Network LSA itself (if we generate/store it).
    # 3. Connecting DR to its pseudo-node with cost 0.
    # 4. Connecting other routers on that segment to the pseudo-node with their interface cost.
    # 5. (Implicitly, SPF runs from router, through pseudo-node (cost 0 from DR, or if_cost from other), then 0 to other routers on segment)

    return g

@dataclass
class OSPFArea:
    area_id: AreaID
    # Routers that have at least one interface in this area.
    # This might be populated by a higher-level OSPF domain manager.
    routers_in_area: List[OSPFRouter] = field(default_factory=list) 
    # Intra-area topology graph for this area.
    topology_graph: Optional[Graph] = None
    # Link State Database for this area. Maps (LSAType, LSID, AdvRouter) -> LSA
    # This is a simplified key; official LSDBs are more complex to index.
    lsdb: Dict[Tuple[LSAType, Union[IPAddress, RouterID], RouterID], Union[LSAHeader, RouterLSA, NetworkLSA]] = field(default_factory=dict)

    def build_intra_area_topology(self, all_domain_routers: Optional[List[OSPFRouter]] = None) -> None:
        """
        Builds the intra-area topology graph for this specific area.
        If all_domain_routers is provided, it filters them for this area.
        Otherwise, it uses its own routers_in_area list.
        """
        routers_to_consider = self.routers_in_area
        if all_domain_routers:
            # Filter all_domain_routers to include only those relevant to this area
            # A router is relevant if it has any interface in this area_id
            routers_to_consider = [r for r in all_domain_routers if any(iface.area_id == self.area_id for iface in r.interfaces)]
            # Update self.routers_in_area if it was empty or to ensure consistency
            # This line might be too assertive depending on desired behavior, consider if self.routers_in_area
            # should be the single source of truth once set.
            self.routers_in_area = routers_to_consider 
        
        if not routers_to_consider:
            self.topology_graph = Graph() # Empty graph if no routers for this area
            return

        self.topology_graph = build_ospf_graph_from_routers(routers_to_consider, self.area_id)

    def add_lsa_to_lsdb(self, lsa: Union[RouterLSA, NetworkLSA, LSAHeader]) -> None:
        """Adds or updates an LSA in the area's LSDB."""
        # Basic LSDB key: (LSAType, LinkStateID, AdvertisingRouter)
        lsa_key = (lsa.ls_type, lsa.link_state_id, lsa.advertising_router)
        
        # Rudimentary LSDB update logic ( fresher LSA replaces older/same)
        # Real OSPF LSDB update is more complex (sequence numbers, age, checksum)
        if lsa_key not in self.lsdb or \
           lsa.ls_sequence_number > self.lsdb[lsa_key].ls_sequence_number or \
           (lsa.ls_sequence_number == self.lsdb[lsa_key].ls_sequence_number and lsa.ls_age < self.lsdb[lsa_key].ls_age) or \
           lsa.ls_age == 3600: # MaxAge LSAs should be accepted to be flushed
            self.lsdb[lsa_key] = lsa
            # Potentially trigger SPF recalculation for this area if topology_graph exists
            # self.recalculate_spf() 

    # Placeholder for SPF calculation on the area's graph
    # def recalculate_spf(self):
    #     if self.topology_graph:
    #         # For each router in the graph, run Dijkstra
    #         for node_id in self.topology_graph.get_all_nodes():
    #             distances, predecessors = dijkstra(self.topology_graph, node_id)
    #             # Store these results, perhaps in the OSPFRouter object's data within the graph
    #             # or in a separate routing table structure for the area.
    #             pass

# REMOVE THE MISPLACED return g at the end of the file by ensuring the file ends after the OSPFArea class definition. 
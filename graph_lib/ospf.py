from dataclasses import dataclass, field
from enum import Enum
from typing import List, Union, NewType, Optional, Dict, Tuple
import ipaddress # Import the ipaddress module
from graph_lib.graph import Graph # Ensure Graph is imported if not already at top level of module
from .algorithms import dijkstra # Import dijkstra
from collections import namedtuple, defaultdict # Ensure namedtuple and defaultdict are imported

# Represents an IP address, typically stored as a string for simplicity here.
# In a more complete implementation, this might be an IPv4Address or IPv6Address object.
IPAddress = NewType("IPAddress", str)
RouterID = NewType("RouterID", str) # OSPF Router ID, typically in IPv4 format
NetworkID = NewType("NetworkID", str) # Represents a network segment, e.g., "10.0.1.0/24"
PseudoNodeID = NewType("PseudoNodeID", str) # Represents a pseudo-node, e.g., "transit_10.0.1.3"
NodeID = Union[RouterID, NetworkID, PseudoNodeID] # General ID for nodes in SPF graph

# Define SPFResult named tuple for storing routing information
SPFResult = namedtuple("SPFResult", ["cost", "next_hop_router_id"])

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
                                     # For transit network, this is router's own IP on that network.
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
        # OSPF Router LSA body: flags (2 bytes), num_links (2 bytes), links data (12 bytes each)
        body_length = 4 # V/E/B flags + Number of Links
        body_length += sum(12 for _ in self.links) # Each link is 12 bytes
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
        self._calculate_length()

    def _calculate_length(self):
        # Header (20 bytes) + Network Mask (4 bytes) + Attached Routers (4 bytes each)
        body_length = 4 # Network Mask
        body_length += len(self.attached_routers) * 4 # Each RouterID is 4 bytes
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
    POINT_TO_POINT = 3 
    BROADCAST = 4      
    NBMA = 5           
    POINT_TO_MULTIPOINT = 6
    # Interface states on a segment (result of DR election etc.)
    DR_OTHER = 7 
    BDR = 8
    DR = 9

@dataclass
class OSPFInterface:
    ip_address: IPAddress
    network_mask: IPAddress
    area_id: AreaID
    network_type: OSPFInterfaceState = OSPFInterfaceState.BROADCAST 
    cost: int = 10
    current_ospf_state: OSPFInterfaceState = OSPFInterfaceState.DR_OTHER 
    hello_interval: int = 10 
    dead_interval: int = 40  
    priority: int = 1        
    
    neighbor_router_id: Optional[RouterID] = None # For P2P links
    neighbor_interface_ip: Optional[IPAddress] = None # For P2P or DR's IP on multi-access
    # Helper: if this interface is on a segment where a DR exists, this is the DR's Router ID
    # This would be learned via Hello protocol or configuration
    designated_router_id: Optional[RouterID] = None 
    # Helper: IP address of the DR on this segment (used as Link ID in Router LSA's transit link)
    designated_router_ip_on_segment: Optional[IPAddress] = None


@dataclass
class OSPFRouter:
    router_id: RouterID
    is_abr: bool = False # Area Border Router
    is_asbr: bool = False # Autonomous System Boundary Router
    interfaces: List[OSPFInterface] = field(default_factory=list)
    
    # Store generated LSAs, perhaps useful for inspection or flooding simulation
    generated_lsas: List[Union[RouterLSA, NetworkLSA]] = field(default_factory=list)


    def add_interface(self, interface: OSPFInterface):
        self.interfaces.append(interface)

    def originate_router_lsa(self, area_id: AreaID) -> Optional[RouterLSA]:
        links_for_lsa: List[RouterLSALink] = []
        active_in_area = False

        for iface in self.interfaces:
            if iface.area_id != area_id or iface.current_ospf_state == OSPFInterfaceState.DOWN:
                continue
            active_in_area = True

            if iface.network_type == OSPFInterfaceState.POINT_TO_POINT:
                if iface.neighbor_router_id: # Assuming adjacency is up
                    links_for_lsa.append(RouterLSALink(
                        link_id=iface.neighbor_router_id,
                        link_data=iface.ip_address, # Router's own interface IP
                        link_type=RouterLSALinkType.POINT_TO_POINT,
                        metric=iface.cost
                    ))
            elif iface.network_type in [OSPFInterfaceState.BROADCAST, OSPFInterfaceState.NBMA]:
                if iface.designated_router_ip_on_segment: # DR exists on this segment
                    links_for_lsa.append(RouterLSALink(
                        link_id=iface.designated_router_ip_on_segment, # Link ID is DR's IP address
                        link_data=iface.ip_address, # Link Data is router's own IP address
                        link_type=RouterLSALinkType.TRANSIT_NETWORK,
                        metric=iface.cost
                    ))
                else: # No DR, maybe a stub? (Simplified: consider it stub if no DR)
                      # Or if it's a segment where this router is the only one.
                      # Real stub networks are identified differently (e.g. passive-interface or network type)
                      # For simplicity, if it's a broadcast/NBMA interface but no DR info, treat as stub link.
                      # This needs careful definition of what a "stub network" means in this context.
                      # A true stub network (Type 3 link in Router LSA) has no other routers.
                      # If it's a segment like 192.168.1.0/24 with only this router, it's a stub.
                      # Link ID: Network IP, Link Data: Network Mask
                    network_addr = get_network_address(iface.ip_address, iface.network_mask)
                    links_for_lsa.append(RouterLSALink(
                        link_id=network_addr, # Network IP
                        link_data=iface.network_mask, # Network Mask
                        link_type=RouterLSALinkType.STUB_NETWORK,
                        metric=iface.cost
                    ))
            # TODO: Add logic for STUB_NETWORK links if an interface is explicitly a stub
            # (e.g. loopbacks, or configured as passive and part of OSPF)
            # For a loopback, typically advertised as a stub link.
            elif iface.network_type == OSPFInterfaceState.LOOPBACK:
                 links_for_lsa.append(RouterLSALink(
                    link_id=iface.ip_address, # Network number (host route)
                    link_data=IPAddress("255.255.255.255"), # Mask for host route
                    link_type=RouterLSALinkType.STUB_NETWORK,
                    metric=iface.cost 
                 ))


        if not active_in_area and not self.is_abr and not self.is_asbr : # Only generate if active or special router type
             # A router might still generate an LSA if it's an ABR/ASBR even with no active links in *this* specific area
             # but for intra-area graph, it needs links or being special.
             # If no links and not ABR/ASBR, it might not need to advertise a router LSA for this area.
             # However, OSPF usually requires router LSA if router is in the area.
             # Let's assume it should always generate if it has interfaces in the area.
             pass


        # Create the Router LSA
        router_lsa = RouterLSA(
            ls_age=0, # Will be set by LSDB aging
            options=0, # Simplified
            advertising_router=self.router_id,
            link_state_id=self.router_id, # Router LSA's LSID is its own RID
            is_abr=self.is_abr,
            is_asbr=self.is_asbr,
            is_virtual_link_endpoint=False, # Simplified
            links=links_for_lsa
        )
        # _calculate_length is called in __post_init__
        self.generated_lsas.append(router_lsa)
        return router_lsa

    def originate_network_lsa(self, dr_interface: OSPFInterface, attached_router_ids: List[RouterID]) -> Optional[NetworkLSA]:
        if dr_interface.current_ospf_state != OSPFInterfaceState.DR or \
           dr_interface.network_type not in [OSPFInterfaceState.BROADCAST, OSPFInterfaceState.NBMA]:
            return None # Only DR on broadcast/NBMA originates Network LSAs

        # Ensure DR itself is in the list of attached routers
        all_attached_rids = list(set(attached_router_ids + [self.router_id]))

        network_lsa = NetworkLSA(
            ls_age=0,
            options=0,
            advertising_router=self.router_id,
            link_state_id=dr_interface.ip_address, # Network LSA's LSID is DR's interface IP
            network_mask=dr_interface.network_mask,
            attached_routers=all_attached_rids
        )
        # _calculate_length is called in __post_init__
        self.generated_lsas.append(network_lsa)
        return network_lsa

# --- OSPF Topology Building --- #

def build_ospf_graph_from_lsdb(
    lsdb: Dict[Tuple[LSAType, Union[IPAddress, RouterID], RouterID], Union[LSAHeader, RouterLSA, NetworkLSA]],
    target_area_id: AreaID # Not strictly needed if LSDB is already area-specific, but good for clarity
    ) -> Graph:
    """
    Builds an OSPF topology graph for a specific area from its Link State Database (LSDB).
    Nodes in the graph are RouterIDs and pseudo-nodes for transit networks (derived from Network LSAs).
    Edges represent OSPF links with costs as weights.
    """
    g = Graph()
    router_nodes: Dict[RouterID, Dict] = {} # Stores router_id -> data (e.g. ABR/ASBR status)

    # Pass 1: Add all routers from Router LSAs and Network LSAs as nodes
    for lsa_key, lsa_content in lsdb.items():
        lsa_type, ls_id, adv_router = lsa_key
        
        # Add advertising router if not already present
        if adv_router not in g:
            g.add_node(adv_router, data={'type': 'router', 'is_abr': False, 'is_asbr': False}) # Initial flags

        if isinstance(lsa_content, RouterLSA):
            # Update ABR/ASBR flags for the advertising router
            node_data = g.get_node_data(adv_router)
            if node_data: # Should exist
                node_data['is_abr'] = lsa_content.is_abr
                node_data['is_asbr'] = lsa_content.is_asbr

            for link in lsa_content.links:
                if link.link_type == RouterLSALinkType.POINT_TO_POINT:
                    neighbor_router_id = link.link_id
                    # For P2P links, link_id is RouterID (a str). Add if not in graph.
                    # Removed problematic isinstance(neighbor_router_id, RouterID) check.
                    # We assume it's a str because RouterID = NewType("RouterID", str)
                    if neighbor_router_id not in g: # Check if node_id (str) is already a node
                        g.add_node(neighbor_router_id, data={'type': 'router', 'is_abr': False, 'is_asbr': False})
                # Other link types might also imply router existence, but P2P is explicit.
        
        elif isinstance(lsa_content, NetworkLSA):
            # Network LSA's Link State ID is the DR's interface IP, which acts as pseudo-node ID
            pseudo_node_id = f"transit_{ls_id}" # ls_id here is DR's IP
            if pseudo_node_id not in g:
                g.add_node(pseudo_node_id, data={'type': 'pseudo_node', 
                                                 'dr_ip': ls_id, 
                                                 'mask': lsa_content.network_mask,
                                                 'adv_router': adv_router # DR's RouterID
                                                 })
            # Add all attached routers from Network LSA as nodes
            for attached_rid in lsa_content.attached_routers:
                if attached_rid not in g:
                    g.add_node(attached_rid, data={'type': 'router', 'is_abr': False, 'is_asbr': False})

    # Pass 2: Add edges based on LSAs
    for lsa_key, lsa_content in lsdb.items():
        lsa_type, ls_id, adv_router = lsa_key

        if isinstance(lsa_content, RouterLSA):
            # adv_router is the source of these links
            for link in lsa_content.links:
                if link.link_type == RouterLSALinkType.POINT_TO_POINT:
                    # Link ID is Neighbor Router ID
                    neighbor_router_id = link.link_id
                    # For P2P links, link_id is RouterID (a str).
                    # Rely on type hints and OSPF spec rather than isinstance with NewType.
                    # Ensure neighbor_router_id is treated as the string ID it is.
                    if g.has_node(str(neighbor_router_id)) and g.get_node_data(str(neighbor_router_id)).get('type') == 'router':
                        g.add_edge(adv_router, str(neighbor_router_id), weight=link.metric)
                
                elif link.link_type == RouterLSALinkType.TRANSIT_NETWORK:
                    # Link ID is the IP address of the DR (which is the LSID of the Network LSA)
                    # This corresponds to the pseudo_node_id
                    dr_ip_on_segment = link.link_id 
                    pseudo_node_id = f"transit_{dr_ip_on_segment}"
                    
                    if g.has_node(pseudo_node_id):
                        # Router connects to pseudo-node with its interface cost (link.metric)
                        g.add_edge(adv_router, pseudo_node_id, weight=link.metric)
                    # else: pseudo-node should have been created in Pass 1 from a Network LSA.
                    # If not, there's an inconsistency or missing Network LSA.

                # STUB_NETWORK links from Router LSA are for calculating routes to networks,
                # but don't form edges to other *routers* in the SPF graph directly.
                # They represent leaf networks. These are handled by Dijkstra when calculating
                # paths if pseudo-nodes are not used for them or if they are destinations.
                # For now, graph primarily connects routers and pseudo-nodes representing multi-access segments.

        elif isinstance(lsa_content, NetworkLSA):
            # LSID is DR's IP, adv_router is DR's RouterID
            pseudo_node_id = f"transit_{ls_id}" # ls_id is DR's IP
            
            if not g.has_node(pseudo_node_id):
                # This should ideally not happen if Pass 1 was complete
                # print(f"Warning: Pseudo-node {pseudo_node_id} not found for Network LSA from {adv_router}")
                continue

            # Connect all attached routers to this pseudo-node
            # Cost from pseudo-node to an attached router is 0.
            # (The cost from router to pseudo-node is handled by Router LSA's transit link)
            for attached_rid in lsa_content.attached_routers:
                if g.has_node(attached_rid) and g.get_node_data(attached_rid).get('type') == 'router':
                    # Ensure edge is from pseudo-node to router with weight 0
                    # The reverse (router to pseudo-node) is added by the Router LSA's transit link with actual cost
                    if not g.has_edge(pseudo_node_id, attached_rid): # Avoid duplicates if any
                         g.add_edge(pseudo_node_id, attached_rid, weight=0)
    return g


@dataclass
class OSPFArea:
    area_id: AreaID
    # Routers that have at least one interface in this area.
    # This might be populated by a higher-level OSPF domain manager.
    routers_in_area: List[OSPFRouter] = field(default_factory=list) 
    # Link State Database for this area. Maps (LSAType, LSID, AdvRouter) -> LSA
    lsdb: Dict[Tuple[LSAType, Union[IPAddress, RouterID], RouterID], Union[LSAHeader, RouterLSA, NetworkLSA]] = field(default_factory=dict)
    # Intra-area topology graph for this area.
    topology_graph: Optional[Graph] = field(default=None, init=False) # Initialized by build method
    # Routing table for this area, calculated by SPF
    # Maps: SourceRouterID -> DestinationNodeID (RouterID or PseudoNodeID) -> SPFResult
    routing_table: Dict[RouterID, Dict[NodeID, SPFResult]] = field(default_factory=lambda: defaultdict(dict))


    def build_area_topology_from_lsdb(self) -> None:
        """
        Builds or rebuilds the intra-area topology graph from the area's LSDB.
        """
        self.topology_graph = build_ospf_graph_from_lsdb(self.lsdb, self.area_id)
        # print(f"Area {self.area_id}: Topology graph built/rebuilt from LSDB.")
        self.recalculate_spf() # Recalculate SPF after topology changes


    def add_lsa_to_lsdb(self, lsa: Union[RouterLSA, NetworkLSA, LSAHeader], source_router: Optional[OSPFRouter] = None) -> bool:
        """
        Adds or updates an LSA in the area's LSDB.
        Performs basic validation (e.g., sequence number, age, checksum).
        Returns True if LSA was added/updated and SPF needs recalculation, False otherwise.
        """
        lsa_key = (lsa.ls_type, lsa.link_state_id, lsa.advertising_router)
        current_lsa = self.lsdb.get(lsa_key)
        
        changed = False
        if current_lsa is None:
            self.lsdb[lsa_key] = lsa
            changed = True
        else:
            # OSPF LSDB Update Rules (simplified):
            # 1. Higher Sequence Number is preferred.
            # 2. Same Sequence Number: Lower LS Age is preferred (unless MaxAge).
            # 3. Same Sequence Number & Age: Higher Checksum is preferred. (Indicates different content)
            # 4. MaxAge (3600s) LSAs: Handled for flushing. If new LSA is MaxAge, accept if current isn't or if seqnum is higher.
            #    If current is MaxAge, new non-MaxAge LSA with same or higher seqnum can replace it.

            if lsa.ls_sequence_number > current_lsa.ls_sequence_number:
                changed = True
            elif lsa.ls_sequence_number == current_lsa.ls_sequence_number:
                if lsa.ls_checksum != current_lsa.ls_checksum: # Different content
                    if lsa.ls_age < current_lsa.ls_age : # Prefer newer if checksum differs
                         changed = True
                    # If ages are same but checksums differ, it's unusual but implies an update.
                    # RFC 2328 implies checksum is checked before seq num for identical instances.
                    # Let's assume for identical (Seq, Age, Type, LSID, AdvRtr), checksum implies content change.
                    # But standard is: if Seq, Age, Checksum are identical, it's a duplicate.
                    # If Seq is same, prefer one with smaller age OR if one is MaxAge and other isn't.
                
                # If sequence and checksum are same, compare age.
                # An LSA with MaxAge (3600) means it should be flushed.
                # A new LSA (even with same seq num) that isn't MaxAge can replace a MaxAge LSA.
                # A new LSA with smaller age (and not MaxAge) is preferred.
                if current_lsa.ls_age == 3600 and lsa.ls_age < 3600:
                    changed = True
                elif lsa.ls_age < current_lsa.ls_age and lsa.ls_age != 3600 : # Prefer fresher, non-MaxAge
                    changed = True
                # If new LSA is MaxAge and current is not, and seq num is same/higher
                elif lsa.ls_age == 3600 and current_lsa.ls_age != 3600:
                    changed = True


            if changed:
                self.lsdb[lsa_key] = lsa
        
        if changed:
            # print(f"Area {self.area_id}: LSA {lsa_key} updated in LSDB. Triggering topology rebuild and SPF.")
            self.build_area_topology_from_lsdb() # Rebuild graph and run SPF
        return changed

    def recalculate_spf(self) -> None:
        """
        Recalculates SPF for the area using Dijkstra on the current topology_graph.
        Updates self.routing_table.
        """
        if not self.topology_graph or not self.topology_graph.get_all_nodes():
            self.routing_table.clear()
            # print(f"Area {self.area_id}: SPF not run. Graph empty or not built.")
            return

        new_routing_table: Dict[RouterID, Dict[NodeID, SPFResult]] = {}
        
        # We only run SPF from actual router nodes, not pseudo-nodes.
        router_nodes_in_graph = [
            node_id for node_id in self.topology_graph.get_all_nodes() 
            if self.topology_graph.get_node_data(node_id) and \
               self.topology_graph.get_node_data(node_id).get('type') == 'router'
        ]

        for source_router_id_anytype in router_nodes_in_graph:
            source_router_id = RouterID(str(source_router_id_anytype)) # Ensure it's RouterID type

            if source_router_id not in self.topology_graph: continue # Should be in graph

            # distances: node -> cost, predecessors: node -> prev_node_on_path_from_source
            distances, predecessors = dijkstra(self.topology_graph, start_node=source_router_id)
            
            new_routing_table[source_router_id] = {}

            for dest_node_id_anytype, cost in distances.items():
                if cost == float('inf'): # Unreachable
                    continue
                
                # Ensure dest_node_id is consistently typed (str for pseudo, RouterID for router)
                dest_node_id: Union[RouterID, str]
                dest_node_data = self.topology_graph.get_node_data(dest_node_id_anytype)
                if dest_node_data and dest_node_data.get('type') == 'router':
                    dest_node_id = RouterID(str(dest_node_id_anytype))
                else: # Assumed pseudo-node (string ID like "transit_...") or other non-router node
                    dest_node_id = str(dest_node_id_anytype)


                if dest_node_id == source_router_id: # Path to self
                    next_hop = None 
                else:
                    # Reconstruct path to find the first hop from source_router_id
                    curr = dest_node_id
                    # Trace back until `prev` is source_router_id, then `curr` is the next hop
                    prev = predecessors.get(curr) 
                    if prev == source_router_id: # Direct neighbor is the first hop
                        next_hop = curr
                    else: # Need to trace back further
                        while prev is not None and predecessors.get(prev) != source_router_id:
                            curr = prev
                            prev = predecessors.get(curr)
                        # After loop, if prev is not None (i.e., path exists beyond direct connection to source),
                        # then 'curr' is the first hop from the source.
                        # If prev is None here, it means curr was source, handled above.
                        # If predecessors.get(prev) is source_router_id, then prev is the next hop.
                        if prev is not None : # prev is the next hop if loop terminated due to predecessors.get(prev) == source_router_id
                             next_hop = prev if predecessors.get(prev) == source_router_id else curr
                        else: # Should be covered by direct neighbor or self-path
                             next_hop = curr if curr != source_router_id else None


                # Store route: Destination can be another router or a pseudo-node (network)
                new_routing_table[source_router_id][dest_node_id] = SPFResult(cost=cost, next_hop_router_id=next_hop)
        
        self.routing_table = new_routing_table
        # print(f"Area {self.area_id}: SPF calculation complete. Routing table entries: {sum(len(rt) for rt in self.routing_table.values())}")


# Utility function to calculate network address
def get_network_address(ip: IPAddress, mask: IPAddress) -> IPAddress:
    try:
        # Ensure ip and mask are strings for ipaddress module
        ip_str = str(ip)
        mask_str = str(mask)
        network = ipaddress.IPv4Network(f'{ip_str}/{mask_str}', strict=False)
        return IPAddress(str(network.network_address))
    except ValueError:
        # Fallback if ip/mask format is not valid for IPv4Network (e.g. RouterID used as IP)
        # In a real OSPF, Link State IDs can be RouterIDs or IP Addresses depending on LSA type/link type
        # This function is primarily for stub network calculation where IP/Mask are expected.
        return ip # Return original IP as a last resort. Could log an error.

# Example Usage (Conceptual - would be part of a larger OSPF simulation)
# router1 = OSPFRouter(router_id=RouterID("1.1.1.1"))
# router1.add_interface(OSPFInterface(ip_address=IPAddress("10.0.1.1"), network_mask=IPAddress("255.255.255.0"), area_id=AreaID("0.0.0.0"), network_type=OSPFInterfaceState.POINT_TO_POINT, cost=10, neighbor_router_id=RouterID("2.2.2.2")))
# router2 = OSPFRouter(router_id=RouterID("2.2.2.2"))
# router2.add_interface(OSPFInterface(ip_address=IPAddress("10.0.1.2"), network_mask=IPAddress("255.255.255.0"), area_id=AreaID("0.0.0.0"), network_type=OSPFInterfaceState.POINT_TO_POINT, cost=10, neighbor_router_id=RouterID("1.1.1.1")))
# router3 = OSPFRouter(router_id=RouterID("3.3.3.3"))
# # Interface on a broadcast network where R3 is DR
# if_dr = OSPFInterface(ip_address=IPAddress("10.0.2.1"), network_mask=IPAddress("255.255.255.0"), area_id=AreaID("0.0.0.0"), network_type=OSPFInterfaceState.BROADCAST, cost=5, current_ospf_state=OSPFInterfaceState.DR, designated_router_ip_on_segment=IPAddress("10.0.2.1"), designated_router_id=RouterID("3.3.3.3"))
# router3.add_interface(if_dr)
# # R1 connects to this broadcast network, R3 is DR
# r1_if_broadcast = OSPFInterface(
#     ip_address=IPAddress("10.0.2.2"), 
#     network_mask=IPAddress("255.255.255.0"), 
#     area_id=AreaID("0.0.0.0"), 
#     network_type=OSPFInterfaceState.BROADCAST, 
#     cost=10, 
#     current_ospf_state=OSPFInterfaceState.DR_OTHER, 
#     designated_router_ip_on_segment=IPAddress("10.0.2.1"), # R1 knows DR's IP
#     designated_router_id=RouterID("3.3.3.3") # R1 knows DR's RID
# )
# router1.add_interface(r1_if_broadcast)

# # Simulate LSAs being generated and added to LSDB
# area0 = OSPFArea(area_id=AreaID("0.0.0.0"))

# # Routers generate their LSAs
# r1_lsa = router1.originate_router_lsa(area_id=AreaID("0.0.0.0"))
# r2_lsa = router2.originate_router_lsa(area_id=AreaID("0.0.0.0"))
# r3_lsa = router3.originate_router_lsa(area_id=AreaID("0.0.0.0"))

# if r1_lsa: area0.add_lsa_to_lsdb(r1_lsa)
# if r2_lsa: area0.add_lsa_to_lsdb(r2_lsa)
# if r3_lsa: area0.add_lsa_to_lsdb(r3_lsa)

# # R3 (DR on 10.0.2.0/24) originates Network LSA for that segment
# # Attached routers on that segment are R1 and R3 itself.
# net_lsa_r3 = router3.originate_network_lsa(dr_interface=if_dr, attached_router_ids=[RouterID("1.1.1.1")])
# if net_lsa_r3: area0.add_lsa_to_lsdb(net_lsa_r3)

# # At this point, area0.build_area_topology_from_lsdb() and area0.recalculate_spf() 
# # would have been called internally by add_lsa_to_lsdb.

# if area0.topology_graph:
#     print("\nArea 0 Topology Graph:")
#     print("Nodes:", area0.topology_graph.get_all_nodes(include_data=True))
#     print("Edges:", area0.topology_graph.get_all_edges(include_weights=True))

# print("\nArea 0 Routing Table (Contents):")
# for src_rid, routes in area0.routing_table.items():
#     print(f"  Routes from {src_rid}:")
#     for dest_id, (cost, nexthop) in routes.items():
#         print(f"    To {dest_id}: Cost={cost}, NextHop={nexthop}") 
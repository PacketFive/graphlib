#!/usr/bin/python3
"""
Mininet Importer for graph_lib

This script demonstrates how to:
1. Create a custom Mininet topology with routers and hosts.
2. Configure router interfaces and enable IP forwarding.
3. Extract network information from the Mininet topology.
4. Convert this information into OSPF data structures (Routers, Interfaces, LSAs) using `graph_lib.ospf`.
5. Simulate OSPF operations:
    - Perform a simplified Designated Router (DR) election on broadcast segments.
    - Originate Router LSAs (Type 1) and Network LSAs (Type 2).
    - Populate an OSPF Link State Database (LSDB) for an area.
    - Build an intra-area topology graph from the LSDB.
    - Run the Shortest Path First (SPF) algorithm (Dijkstra) to calculate routing tables.
6. Display the resulting OSPF routing tables for each router.
7. Optionally, convert the Mininet topology into a generic `graph_lib.Graph` object.
8. Control Mininet CLI interaction via an environment variable (`INTERACTIVE_MININET_CLI`).

Requirements:
- Mininet must be installed.
- Python virtual environment (e.g., at `/opt/pyvenv/`) with necessary packages.

Execution (from the project root directory, e.g., `packetfive/graphlib`):
Assuming your virtual environment is at `/opt/pyvenv/`:
  `sudo /opt/pyvenv/bin/python -m graph_lib.mininet_importer`

If your virtual environment is activated in the current shell:
  `sudo python -m graph_lib.mininet_importer`
"""

from mininet.net import Mininet
from mininet.node import Host, OVSKernelSwitch, Controller
from mininet.cli import CLI
from mininet.link import TCLink
from mininet.log import setLogLevel, info

from typing import List, Dict, Optional, Tuple
import ipaddress
import os

# Assuming graph_lib is in the parent directory or PYTHONPATH
from .ospf import (
    OSPFRouter, OSPFInterface, OSPFArea, AreaID, IPAddress, RouterID,
    LSAType, RouterLSALinkType, OSPFInterfaceState, get_network_address,
    RouterLSA, NetworkLSA
)
from .graph import Graph

# --- Mininet Topology Definition ---

DEFAULT_OSPF_AREA = AreaID("0.0.0.0")
DEFAULT_OSPF_COST = 10

def enable_ip_forwarding(host):
    """Enables IP forwarding on a Mininet host."""
    info(f"Enabling IP forwarding on {host.name}\n")
    host.cmd("sysctl -w net.ipv4.ip_forward=1")

def create_custom_topology():
    """
    Creates a Mininet network with 5 routers, 1 switch, and 2 hosts.
    - r1, r2, r3 are connected to a switch sw0 (broadcast segment).
    - r1 has a P2P link to r4.
    - r2 has a P2P link to r5.
    - h1 is connected to r4.
    - h2 is connected to r5.
    """
    net = Mininet(controller=None, switch=OVSKernelSwitch, link=TCLink, host=Host)

    info("Creating nodes...\n")
    # Routers (will be Mininet Hosts with IP forwarding enabled)
    r1 = net.addHost('r1', ip=None) # IPs will be set on interfaces
    r2 = net.addHost('r2', ip=None)
    r3 = net.addHost('r3', ip=None)
    r4 = net.addHost('r4', ip=None)
    r5 = net.addHost('r5', ip=None)
    routers = [r1, r2, r3, r4, r5]

    # Hosts
    h1 = net.addHost('h1', ip='192.168.4.100/24', defaultRoute='via 192.168.4.1')
    h2 = net.addHost('h2', ip='192.168.5.100/24', defaultRoute='via 192.168.5.1')

    # Switch for broadcast segment
    sw0 = net.addSwitch('sw0')

    info("Creating links and configuring interfaces...\\n")

    # Router Loopback IPs for RIDs (configured manually after start for OSPFRouter)
    # We'll use these as OSPF RouterIDs. Mininet hosts don't have native loopbacks easily set pre-start.
    # Instead, we will assign these conceptually and use them for RouterID.
    router_rids = {
        'r1': RouterID("1.1.1.1"), 'r2': RouterID("2.2.2.2"), 'r3': RouterID("3.3.3.3"),
        'r4': RouterID("4.4.4.4"), 'r5': RouterID("5.5.5.5")
    }

    # Connections to switch sw0 (broadcast segment 10.0.1.0/24)
    net.addLink(r1, sw0, intfName1='r1-eth0', params1={'ip': '10.0.1.1/24'})
    net.addLink(r2, sw0, intfName1='r2-eth0', params1={'ip': '10.0.1.2/24'})
    net.addLink(r3, sw0, intfName1='r3-eth0', params1={'ip': '10.0.1.3/24'})

    # P2P link r1 -- r4 (segment 10.1.4.0/24)
    net.addLink(r1, r4, intfName1='r1-eth1', params1={'ip': '10.1.4.1/24'},
                intfName2='r4-eth0', params2={'ip': '10.1.4.4/24'})

    # P2P link r2 -- r5 (segment 10.2.5.0/24)
    net.addLink(r2, r5, intfName1='r2-eth1', params1={'ip': '10.2.5.2/24'},
                intfName2='r5-eth0', params2={'ip': '10.2.5.5/24'})

    # Connections to hosts
    net.addLink(r4, h1, intfName1='r4-eth1', params1={'ip': '192.168.4.1/24'})
    net.addLink(r5, h2, intfName1='r5-eth1', params1={'ip': '192.168.5.1/24'})
    
    return net, router_rids, routers

# --- Mininet to graph_lib Conversion ---

def extract_topology_for_ospf(net: Mininet, conceptual_rids: Dict[str, RouterID], area_id_str: str = "0.0.0.0") -> OSPFArea:
    """
    Extracts topology from Mininet and converts it into OSPFArea and OSPFRouter objects.
    """
    ospf_area = OSPFArea(area_id=AreaID(area_id_str))
    ospf_routers_map: Dict[str, OSPFRouter] = {}

    mininet_routers = [h for h in net.hosts if h.name in conceptual_rids]

    # 1. Create OSPFRouter objects
    for r_node in mininet_routers:
        rid = conceptual_rids[r_node.name]
        ospf_router = OSPFRouter(router_id=rid)
        ospf_routers_map[r_node.name] = ospf_router
        ospf_area.routers_in_area.append(ospf_router)

    # 2. Identify broadcast segments and designate DRs
    # A broadcast segment is formed by interfaces connected to the same switch.
    broadcast_segments: Dict[str, Dict[str, any]] = {} # switch_name -> {dr_ip: IPAddress, dr_rid: RouterID, members: List[Tuple[Host, Intf]]}

    for sw_node in net.switches:
        segment_members = []
        highest_ip_on_segment = IPAddress("0.0.0.0")
        designated_router_node: Optional[Host] = None
        designated_router_if_ip: Optional[IPAddress] = None

        for intf in sw_node.intfList(): # Iterate switch interfaces
            if intf.link:
                node1, node2 = intf.link.intf1.node, intf.link.intf2.node
                router_node: Optional[Host] = None
                router_intf_on_link: Optional[Any] = None

                if node1 == sw_node and node2 in mininet_routers:
                    router_node = node2
                    router_intf_on_link = intf.link.intf2
                elif node2 == sw_node and node1 in mininet_routers:
                    router_node = node1
                    router_intf_on_link = intf.link.intf1
                
                if router_node and router_intf_on_link and router_intf_on_link.ip:
                    segment_members.append((router_node, router_intf_on_link))
                    # Simple DR election: highest IP on segment. Ensure IPs are comparable.
                    current_intf_ip_str = router_intf_on_link.ip
                    if IPAddress(current_intf_ip_str) > highest_ip_on_segment: 
                        highest_ip_on_segment = IPAddress(current_intf_ip_str)
                        designated_router_node = router_node
                        designated_router_if_ip = IPAddress(current_intf_ip_str)
        
        if designated_router_node and designated_router_if_ip:
            broadcast_segments[sw_node.name] = {
                'dr_node_name': designated_router_node.name,
                'dr_ip': designated_router_if_ip,
                'dr_rid': conceptual_rids[designated_router_node.name],
                'members': segment_members
            }

    # 3. Create OSPFInterface objects for each router
    for r_node in mininet_routers:
        ospf_router = ospf_routers_map[r_node.name]
        for intf in r_node.intfList():
            if not intf.link or not intf.ip:
                continue

            # WORKAROUND for missing otherIntf method on TCLink object
            current_intf_link = intf.link
            peer_intf_obj = current_intf_link.intf2 if current_intf_link.intf1 == intf else current_intf_link.intf1
            peer_node = peer_intf_obj.node
            
            if peer_node.name.startswith('h'): 
                continue

            current_ospf_dr_state = OSPFInterfaceState.DR_OTHER # Default state
            ospf_intf_state = OSPFInterfaceState.POINT_TO_POINT # Default
            neighbor_rid: Optional[RouterID] = None
            neighbor_ip: Optional[IPAddress] = None
            dr_ip_on_segment: Optional[IPAddress] = None
            dr_rid_on_segment: Optional[RouterID] = None
            
            intf_ip = IPAddress(intf.ip)
            prefix_len = intf.prefixLen if intf.prefixLen is not None else 24
            
            try:
                network_obj = ipaddress.ip_network(f'0.0.0.0/{prefix_len}', strict=False)
                intf_mask = IPAddress(str(network_obj.netmask))
            except ValueError:
                info(f"Warning: Invalid prefix length {prefix_len} for intf {intf.name} ({intf.ip}). Defaulting to 255.255.255.0")
                intf_mask = IPAddress("255.255.255.0")

            if isinstance(peer_node, OVSKernelSwitch):
                if peer_node.name in broadcast_segments:
                    segment_info = broadcast_segments[peer_node.name]
                    ospf_intf_state = OSPFInterfaceState.BROADCAST
                    dr_ip_on_segment = segment_info['dr_ip']
                    dr_rid_on_segment = segment_info['dr_rid']
                    if r_node.name == segment_info['dr_node_name']:
                        current_ospf_dr_state = OSPFInterfaceState.DR
                    else:
                        current_ospf_dr_state = OSPFInterfaceState.DR_OTHER
                else:
                    continue
            
            elif peer_node.name in conceptual_rids: # P2P link to another router
                ospf_intf_state = OSPFInterfaceState.POINT_TO_POINT
                current_ospf_dr_state = OSPFInterfaceState.POINT_TO_POINT
                neighbor_rid = conceptual_rids.get(peer_node.name)
                current_intf_link_p2p = intf.link
                peer_intf = current_intf_link_p2p.intf2 if current_intf_link_p2p.intf1 == intf else current_intf_link_p2p.intf1
                neighbor_ip = IPAddress(peer_intf.ip) if peer_intf.ip else None
            else:
                continue

            ospf_iface = OSPFInterface(
                ip_address=intf_ip,
                network_mask=intf_mask,
                area_id=AreaID(area_id_str),
                network_type=ospf_intf_state,
                cost=DEFAULT_OSPF_COST,
                current_ospf_state=current_ospf_dr_state,
                neighbor_router_id=neighbor_rid,
                neighbor_interface_ip=neighbor_ip,
                designated_router_ip_on_segment=dr_ip_on_segment,
                designated_router_id=dr_rid_on_segment
            )
            ospf_router.add_interface(ospf_iface)

    # 4. Originate LSAs and populate LSDB
    info("\\nOrigination LSAs...\\n")
    all_lsas: List[Union[RouterLSA, NetworkLSA]] = []
    for r_name, ospf_router in ospf_routers_map.items():
        r_lsa = ospf_router.originate_router_lsa(area_id=ospf_area.area_id)
        if r_lsa:
            all_lsas.append(r_lsa)
            info(f"  {r_name} generated Router LSA: {r_lsa.link_state_id}, links: {len(r_lsa.links)}\\n")
        
        for iface in ospf_router.interfaces:
            if iface.current_ospf_state == OSPFInterfaceState.DR and \
               iface.network_type == OSPFInterfaceState.BROADCAST:
                attached_rids_on_segment = []
                sw_name_for_dr_segment: Optional[str] = None
                
                # Find the Mininet router node and its interface corresponding to this DR OSPFInterface
                mininet_dr_node = None
                for mn_node in mininet_routers:
                    if conceptual_rids[mn_node.name] == ospf_router.router_id:
                        mininet_dr_node = mn_node
                        break
                if not mininet_dr_node: continue

                for mn_intf in mininet_dr_node.intfList():
                    if mn_intf.ip and IPAddress(mn_intf.ip) == iface.ip_address:
                        if mn_intf.link: # Check if Mininet interface is connected
                            current_mn_intf_link = mn_intf.link
                            peer_mn_intf_obj = current_mn_intf_link.intf2 if current_mn_intf_link.intf1 == mn_intf else current_mn_intf_link.intf1
                            peer_node_of_dr_intf = peer_mn_intf_obj.node
                            if isinstance(peer_node_of_dr_intf, OVSKernelSwitch):
                                sw_name_for_dr_segment = peer_node_of_dr_intf.name
                                break
                
                if sw_name_for_dr_segment and sw_name_for_dr_segment in broadcast_segments:
                    seg_info = broadcast_segments[sw_name_for_dr_segment]
                    for member_node, _ in seg_info['members']:
                         if member_node.name in conceptual_rids: # Ensure member is a router
                            attached_rids_on_segment.append(conceptual_rids[member_node.name])
                
                net_lsa = ospf_router.originate_network_lsa(
                    dr_interface=iface,
                    attached_router_ids=list(set(attached_rids_on_segment))
                )
                if net_lsa:
                    all_lsas.append(net_lsa)
                    info(f"  {r_name} (DR for {iface.ip_address}) generated Network LSA: {net_lsa.link_state_id}, attached: {len(net_lsa.attached_routers)}\\n")
    
    # Add LSAs to LSDB (triggers SPF)
    info("\\nAdding LSAs to Area LSDB...\\n")
    for lsa in all_lsas:
        ospf_area.add_lsa_to_lsdb(lsa)
        info(f"  Added LSA: type={lsa.ls_type.name}, id={lsa.link_state_id}, adv_rtr={lsa.advertising_router}\\n")

    return ospf_area


def mininet_to_generic_graph(net: Mininet, conceptual_rids: Dict[str, RouterID]) -> Graph:
    """Converts Mininet topology to a generic graph_lib.Graph."""
    g = Graph()
    mininet_routers_nodes = [h for h in net.hosts if h.name in conceptual_rids]

    for r_node in mininet_routers_nodes:
        g.add_node(conceptual_rids[r_node.name]) # Use OSPF RouterID as node ID for consistency

    for link in net.links:
        node1 = link.intf1.node
        node2 = link.intf2.node

        if node1.name in conceptual_rids and node2.name in conceptual_rids:
            rid1 = conceptual_rids[node1.name]
            rid2 = conceptual_rids[node2.name]
            if not g.has_edge(rid1, rid2):
                 g.add_edge(rid1, rid2, weight=DEFAULT_OSPF_COST)
            if not g.has_edge(rid2, rid1): 
                 g.add_edge(rid2, rid1, weight=DEFAULT_OSPF_COST)
    return g

# --- Main Execution ---

if __name__ == '__main__':
    setLogLevel('info')
    info("Mininet Importer Script Initialized.\\n")

    info("Starting Mininet topology creation...\\n")
    net, router_rids_map, mininet_router_nodes_list = create_custom_topology()

    info("\\nStarting network...\\n")
    net.start()

    # Enable IP forwarding on all designated routers
    for r_node in mininet_router_nodes_list:
        enable_ip_forwarding(r_node)
    
    info("\\nConfiguring conceptual loopbacks for OSPF RIDs (already mapped)...\\n")
    # In a real scenario, you might configure actual loopback interfaces on hosts.
    # Here, router_rids_map serves this purpose for OSPFRouter objects.

    info("\\n--- Running OSPF Simulation --- \\n")
    try:
        ospf_area_instance = extract_topology_for_ospf(net, router_rids_map, DEFAULT_OSPF_AREA)
        
        info("\n--- OSPF Intra-Area Routing Tables ---\n ")
        if not ospf_area_instance.routing_table:
            info("  No routing tables calculated or area has no routers.\n")
        
        for router_rid_key in ospf_area_instance.routing_table: # Corrected to singular
            router_name_display = "Unknown Router"
            for rname, rid_val in router_rids_map.items():
                if rid_val == router_rid_key:
                    router_name_display = rname
                    break
            info(f"Router {router_name_display} ({router_rid_key})'s routing table:\n")
            
            routes = ospf_area_instance.routing_table[router_rid_key] # Corrected to singular
            if not routes:
                info("  No routes calculated for this router.\\n")
            for dest_id, route_info in routes.items():
                # dest_id here is NodeID which is Union[RouterID, NetworkID, PseudoNodeID]
                # All are NewTypes of str, so dest_id is str at runtime.
                # Check if it represents a network or a router for display purposes.
                # We'll assume if it contains '/' it's a network, otherwise a router for this print.
                # A more robust way would be to check against actual NetworkID/RouterID types if they were classes.
                if "/" in str(dest_id): # Heuristic for NetworkID (e.g., "10.0.1.0/24")
                    info(f"    To Network {dest_id}: Next Hop {route_info.next_hop_router_id}, Cost {route_info.cost}\n")
                # isinstance(dest_id, RouterID) is problematic with NewType
                # elif isinstance(dest_id, str): # Check if it's a string (RouterID would be)
                # A better check might be if it doesn't contain "/" and is a valid IP format without prefix
                else: # Assume it's a RouterID if not a network format
                    info(f"    To Router {dest_id}: Next Hop {route_info.next_hop_router_id}, Cost {route_info.cost}\n")
        info("\n")
    except Exception as e:
        info(f"Error during OSPF simulation: {e}\\n")
        import traceback
        traceback.print_exc()

    info("\n--- Converting to Generic Graph (Optional) --- \n")
    try:
        generic_graph = mininet_to_generic_graph(net, router_rids_map)
        # Use get_nodes_count() and get_edges_count() instead of len() on iterators
        nodes_count = generic_graph.get_nodes_count()
        edges_count = generic_graph.get_edges_count()
        info(f"Generic graph created with {nodes_count} nodes and {edges_count} edges.\n")
        info(f"Nodes: {list(generic_graph.get_all_nodes())}\n") # Convert iterator to list for printing
        info(f"Edges: {list(generic_graph.get_all_edges(include_weights=True))}\n") # Convert iterator to list for printing
    except Exception as e:
        info(f'Error during generic graph conversion: {e}\n')

    # Only start CLI if an environment variable is set
    if os.environ.get('INTERACTIVE_MININET_CLI') == '1':
        info("\nMininet CLI is available. Type 'exit' to quit.\n")
        CLI(net)
    else:
        info("\nSkipping Mininet CLI. Set INTERACTIVE_MININET_CLI=1 to enable.\n")

    info("\nStopping network...\n")
    net.stop()

    info("\\nScript finished.\\n") 
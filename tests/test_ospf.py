import pytest
from graph_lib.ospf import (
    LSAType, LSAHeader, 
    RouterLSA, RouterLSALink, RouterLSALinkType,
    NetworkLSA, IPAddress, RouterID,
    OSPFInterface, OSPFInterfaceState, AreaID,
    OSPFRouter, OSPFArea
)
from graph_lib.graph import Graph # For type hinting if needed, or direct use
from graph_lib.ospf import build_ospf_graph_from_routers # The function to test

class TestLSAStructures:
    def test_lsa_header_defaults(self):
        header = LSAHeader()
        assert header.ls_age == 0
        assert header.options == 0
        assert header.ls_type == LSAType.ROUTER_LSA # Default, but overridden by specific types
        assert header.link_state_id == ""
        assert header.advertising_router == ""
        assert header.ls_sequence_number == 0
        assert header.ls_checksum == 0
        assert header.length == 20 # Default for a bare header

    def test_lsa_header_custom_values(self):
        header = LSAHeader(
            ls_age=100,
            options=2,
            ls_type=LSAType.AS_EXTERNAL_LSA,
            link_state_id=IPAddress("10.0.0.1"),
            advertising_router=RouterID("1.1.1.1"),
            ls_sequence_number=0x80000001,
            ls_checksum=0x1234,
            length=48 # Custom length
        )
        assert header.ls_type == LSAType.AS_EXTERNAL_LSA
        assert header.link_state_id == "10.0.0.1"
        assert header.advertising_router == "1.1.1.1"
        assert header.length == 48

    def test_lsa_header_invalid_type(self):
        with pytest.raises(TypeError, match="ls_type must be an instance of LSAType Enum"):
            LSAHeader(ls_type=1) # Not an LSAType enum

    def test_router_lsa_defaults_and_initialization(self):
        adv_router = RouterID("1.1.1.1")
        rlsa = RouterLSA(advertising_router=adv_router)
        assert rlsa.ls_type == LSAType.ROUTER_LSA
        assert rlsa.advertising_router == adv_router
        # Link State ID for Router LSA should be the advertising router ID
        assert rlsa.link_state_id == adv_router 
        assert not rlsa.is_abr
        assert not rlsa.is_asbr
        assert not rlsa.is_virtual_link_endpoint
        assert len(rlsa.links) == 0
        # Base LSA header (20) + Router LSA body (4 bytes for flags/num_links)
        assert rlsa.length == 20 + 4 

    def test_router_lsa_add_link(self):
        rlsa = RouterLSA(advertising_router=RouterID("1.1.1.1"))
        initial_length = rlsa.length

        link1 = RouterLSALink(
            link_id=RouterID("2.2.2.2"), 
            link_data=IPAddress("192.168.1.1"), 
            link_type=RouterLSALinkType.POINT_TO_POINT, 
            metric=10
        )
        rlsa.add_link(link1)
        assert len(rlsa.links) == 1
        # Each link adds 12 bytes
        assert rlsa.length == initial_length + 12

        link2 = RouterLSALink(
            link_id=IPAddress("10.0.0.0"), # Network IP
            link_data=IPAddress("255.255.255.0"), # Mask, though typically Link Data for stub is network IP, simplified here.
            link_type=RouterLSALinkType.STUB_NETWORK, 
            metric=1
        )
        rlsa.add_link(link2)
        assert len(rlsa.links) == 2
        assert rlsa.length == initial_length + 12 + 12
        assert rlsa.links[1].link_type == RouterLSALinkType.STUB_NETWORK

    def test_network_lsa_defaults_and_initialization(self):
        adv_router = RouterID("1.1.1.1") # DR
        ls_id = IPAddress("192.168.1.1") # DR's interface IP on this network
        nlsa = NetworkLSA(advertising_router=adv_router, link_state_id=ls_id, network_mask=IPAddress("255.255.255.0"))
        
        assert nlsa.ls_type == LSAType.NETWORK_LSA
        assert nlsa.advertising_router == adv_router
        assert nlsa.link_state_id == ls_id
        assert nlsa.network_mask == "255.255.255.0"
        assert len(nlsa.attached_routers) == 0
        # Base LSA header (20) + Network LSA body (4 for mask + 0 for attached routers)
        assert nlsa.length == 20 + 4

    def test_network_lsa_add_attached_router(self):
        nlsa = NetworkLSA(advertising_router=RouterID("1.1.1.1"), link_state_id=IPAddress("192.168.1.1"))
        initial_length = nlsa.length # Should be 20 (header) + 4 (mask, even if empty initially)
        assert initial_length == 20 + 4 # Default mask is empty string, but we assume 4 bytes for it in calc
        
        nlsa.add_attached_router(RouterID("2.2.2.2"))
        assert len(nlsa.attached_routers) == 1
        # Each attached router adds 4 bytes
        assert nlsa.length == initial_length + 4

        nlsa.add_attached_router(RouterID("3.3.3.3"))
        assert len(nlsa.attached_routers) == 2
        assert nlsa.length == initial_length + 4 + 4
        
        # Adding same router should not change anything
        nlsa.add_attached_router(RouterID("3.3.3.3"))
        assert len(nlsa.attached_routers) == 2
        assert nlsa.length == initial_length + 4 + 4

class TestOSPFRouterConfig:
    def test_ospf_interface_creation(self):
        iface = OSPFInterface(
            ip_address=IPAddress("10.0.0.1"),
            network_mask=IPAddress("255.255.255.0"),
            area_id=AreaID("0.0.0.0"),
            cost=5,
            current_ospf_state=OSPFInterfaceState.POINT_TO_POINT,
            priority=100
        )
        assert iface.ip_address == "10.0.0.1"
        assert iface.area_id == "0.0.0.0"
        assert iface.cost == 5
        assert iface.current_ospf_state == OSPFInterfaceState.POINT_TO_POINT
        assert iface.hello_interval == 10 # Default
        assert iface.priority == 100

    def test_ospf_router_creation(self):
        router = OSPFRouter(router_id=RouterID("1.1.1.1"))
        assert router.router_id == "1.1.1.1"
        assert len(router.interfaces) == 0
        # assert router.lsdb == {} # If lsdb is added

    def test_ospf_router_add_interface(self):
        router = OSPFRouter(router_id=RouterID("1.1.1.1"))
        iface1_ip = IPAddress("10.0.1.1")
        iface1 = OSPFInterface(
            ip_address=iface1_ip,
            network_mask=IPAddress("255.255.255.0"),
            area_id=AreaID("0.0.0.0")
        )
        router.add_interface(iface1)
        assert len(router.interfaces) == 1
        assert router.interfaces[0].ip_address == iface1_ip

        iface2_ip = IPAddress("10.0.2.1")
        iface2 = OSPFInterface(
            ip_address=iface2_ip,
            network_mask=IPAddress("255.255.255.0"),
            area_id=AreaID("0.0.0.1")
        )
        router.add_interface(iface2)
        assert len(router.interfaces) == 2
        assert router.interfaces[1].ip_address == iface2_ip

    def test_conceptual_lsa_origination_placeholders(self):
        """Test that the LSA origination methods exist and return None as per placeholder."""
        router = OSPFRouter(router_id=RouterID("1.1.1.1"))
        # Add a dummy interface for the network LSA case
        dr_iface = OSPFInterface(
            ip_address=IPAddress("192.168.1.1"), 
            network_mask=IPAddress("255.255.255.0"),
            area_id=AreaID("0.0.0.0"),
            current_ospf_state=OSPFInterfaceState.DR
        )
        router.add_interface(dr_iface)

        assert router.originate_router_lsa(area_id=AreaID("0.0.0.0")) is None
        assert router.originate_network_lsa(interface_ip=IPAddress("192.168.1.1")) is None
        # Test non-DR case for network LSA
        router.interfaces[0].current_ospf_state = OSPFInterfaceState.DR_OTHER
        assert router.originate_network_lsa(interface_ip=IPAddress("192.168.1.1")) is None

class TestOSPTopologyBuilding:
    def test_build_graph_no_routers(self):
        g = build_ospf_graph_from_routers([], AreaID("0.0.0.0"))
        assert len(g) == 0
        assert g.get_edges_count() == 0

    def test_build_graph_single_router_no_links(self):
        r1 = OSPFRouter(router_id=RouterID("1.1.1.1"))
        r1.add_interface(OSPFInterface(IPAddress("10.0.0.1"), IPAddress("255.255.255.0"), area_id=AreaID("0.0.0.0")))
        g = build_ospf_graph_from_routers([r1], AreaID("0.0.0.0"))
        assert len(g) == 1
        assert RouterID("1.1.1.1") in g
        assert g.get_node_data(RouterID("1.1.1.1")) == r1
        assert g.get_edges_count() == 0

    def test_build_graph_p2p_link_one_way_defined(self):
        r1 = OSPFRouter(router_id=RouterID("1.1.1.1"))
        r1.add_interface(OSPFInterface(
            ip_address=IPAddress("10.0.0.1"), network_mask=IPAddress("255.255.255.252"), 
            area_id=AreaID("0"), cost=10, network_type=OSPFInterfaceState.POINT_TO_POINT,
            neighbor_router_id=RouterID("2.2.2.2")
        ))
        # R2 does not exist in the input list yet
        g = build_ospf_graph_from_routers([r1], AreaID("0"))
        assert RouterID("1.1.1.1") in g
        assert RouterID("2.2.2.2") not in g # R2 was not provided
        assert g.get_edges_count() == 0 # No edge to non-existent R2

    def test_build_graph_p2p_link_bidirectional(self):
        r1 = OSPFRouter(router_id=RouterID("1.1.1.1"))
        r1.add_interface(OSPFInterface(
            ip_address=IPAddress("10.0.0.1"), network_mask=IPAddress("255.255.255.252"), 
            area_id=AreaID("0"), cost=10, network_type=OSPFInterfaceState.POINT_TO_POINT,
            neighbor_router_id=RouterID("2.2.2.2")
        ))
        r2 = OSPFRouter(router_id=RouterID("2.2.2.2"))
        r2.add_interface(OSPFInterface(
            ip_address=IPAddress("10.0.0.2"), network_mask=IPAddress("255.255.255.252"), 
            area_id=AreaID("0"), cost=15, network_type=OSPFInterfaceState.POINT_TO_POINT,
            neighbor_router_id=RouterID("1.1.1.1")
        ))
        
        routers = [r1, r2]
        g = build_ospf_graph_from_routers(routers, AreaID("0"))

        assert len(g) == 2
        assert RouterID("1.1.1.1") in g
        assert RouterID("2.2.2.2") in g
        assert g.get_node_data(RouterID("1.1.1.1")) == r1
        assert g.get_node_data(RouterID("2.2.2.2")) == r2

        assert g.get_edges_count() == 2
        assert g.get_edge_weight(RouterID("1.1.1.1"), RouterID("2.2.2.2")) == 10
        assert g.get_edge_weight(RouterID("2.2.2.2"), RouterID("1.1.1.1")) == 15

    def test_build_graph_multiple_areas_p2p_links(self):
        r1 = OSPFRouter(router_id=RouterID("R1"))
        r1.add_interface(OSPFInterface(ip_address=IPAddress("10.0.1.1"), network_mask=IPAddress("255.255.255.0"), area_id=AreaID("0"), cost=10, network_type=OSPFInterfaceState.POINT_TO_POINT, neighbor_router_id=RouterID("R2")))
        r1.add_interface(OSPFInterface(ip_address=IPAddress("10.0.3.1"), network_mask=IPAddress("255.255.255.0"), area_id=AreaID("1"), cost=5, network_type=OSPFInterfaceState.POINT_TO_POINT, neighbor_router_id=RouterID("R3")))

        r2 = OSPFRouter(router_id=RouterID("R2"))
        r2.add_interface(OSPFInterface(ip_address=IPAddress("10.0.1.2"), network_mask=IPAddress("255.255.255.0"), area_id=AreaID("0"), cost=10, network_type=OSPFInterfaceState.POINT_TO_POINT, neighbor_router_id=RouterID("R1")))
        r2.add_interface(OSPFInterface(ip_address=IPAddress("10.0.2.1"), network_mask=IPAddress("255.255.255.0"), area_id=AreaID("0"), cost=20, network_type=OSPFInterfaceState.POINT_TO_POINT, neighbor_router_id=RouterID("R4")))

        r3 = OSPFRouter(router_id=RouterID("R3")) # In Area 1
        r3.add_interface(OSPFInterface(ip_address=IPAddress("10.0.3.2"), network_mask=IPAddress("255.255.255.0"), area_id=AreaID("1"), cost=5, network_type=OSPFInterfaceState.POINT_TO_POINT, neighbor_router_id=RouterID("R1")))

        r4 = OSPFRouter(router_id=RouterID("R4")) # In Area 0 with R2
        r4.add_interface(OSPFInterface(ip_address=IPAddress("10.0.2.2"), network_mask=IPAddress("255.255.255.0"), area_id=AreaID("0"), cost=20, network_type=OSPFInterfaceState.POINT_TO_POINT, neighbor_router_id=RouterID("R2")))

        routers = [r1, r2, r3, r4]

        # Test for Area 0
        g_area0 = build_ospf_graph_from_routers(routers, AreaID("0"))
        assert RouterID("R1") in g_area0
        assert RouterID("R2") in g_area0
        assert RouterID("R4") in g_area0
        assert RouterID("R3") not in g_area0 # R3 has no interfaces in Area 0
        assert len(g_area0) == 3

        assert g_area0.get_edge_weight(RouterID("R1"), RouterID("R2")) == 10
        assert g_area0.get_edge_weight(RouterID("R2"), RouterID("R1")) == 10
        assert g_area0.get_edge_weight(RouterID("R2"), RouterID("R4")) == 20
        assert g_area0.get_edge_weight(RouterID("R4"), RouterID("R2")) == 20
        assert g_area0.get_edges_count() == 4

        # Test for Area 1
        g_area1 = build_ospf_graph_from_routers(routers, AreaID("1"))
        assert RouterID("R1") in g_area1
        assert RouterID("R3") in g_area1
        assert RouterID("R2") not in g_area1
        assert RouterID("R4") not in g_area1
        assert len(g_area1) == 2

        assert g_area1.get_edge_weight(RouterID("R1"), RouterID("R3")) == 5
        assert g_area1.get_edge_weight(RouterID("R3"), RouterID("R1")) == 5
        assert g_area1.get_edges_count() == 2

    def test_build_graph_router_in_multiple_areas_but_no_links_in_target_area(self):
        r1 = OSPFRouter(router_id=RouterID("R1"))
        # Interface in area 1, but we will query for area 0
        r1.add_interface(OSPFInterface(ip_address=IPAddress("10.0.3.1"), network_mask=IPAddress("255.255.255.0"), area_id=AreaID("1"), cost=5, network_type=OSPFInterfaceState.POINT_TO_POINT, neighbor_router_id=RouterID("R3")))
        
        g_area0 = build_ospf_graph_from_routers([r1], AreaID("0"))
        assert RouterID("R1") not in g_area0 # R1 has no interfaces in Area 0
        assert len(g_area0) == 0
        assert g_area0.get_edges_count() == 0

class TestOSPFArea:
    def test_ospf_area_creation(self):
        area0 = OSPFArea(area_id=AreaID("0.0.0.0"))
        assert area0.area_id == "0.0.0.0"
        assert len(area0.routers_in_area) == 0
        assert area0.topology_graph is None
        assert len(area0.lsdb) == 0

    def test_ospf_area_build_topology_no_routers(self):
        area0 = OSPFArea(area_id=AreaID("0"))
        area0.build_intra_area_topology(all_domain_routers=[])
        assert area0.topology_graph is not None
        assert len(area0.topology_graph) == 0
        assert len(area0.routers_in_area) == 0

    def test_ospf_area_build_topology_with_routers(self):
        area_id_0 = AreaID("0")
        r1 = OSPFRouter(router_id=RouterID("R1"))
        r1.add_interface(OSPFInterface(IPAddress("10.0.1.1"), IPAddress("255.255.255.0"), area_id_0, cost=10, network_type=OSPFInterfaceState.POINT_TO_POINT, neighbor_router_id=RouterID("R2")))
        
        r2 = OSPFRouter(router_id=RouterID("R2"))
        r2.add_interface(OSPFInterface(IPAddress("10.0.1.2"), IPAddress("255.255.255.0"), area_id_0, cost=10, network_type=OSPFInterfaceState.POINT_TO_POINT, neighbor_router_id=RouterID("R1")))

        # Router in a different area
        r3 = OSPFRouter(router_id=RouterID("R3"))
        r3.add_interface(OSPFInterface(IPAddress("10.0.2.1"), IPAddress("255.255.255.0"), AreaID("1"), cost=5))

        all_routers = [r1, r2, r3]
        area0 = OSPFArea(area_id=area_id_0)
        area0.build_intra_area_topology(all_domain_routers=all_routers)

        assert len(area0.routers_in_area) == 2 # R1 and R2 are in area 0
        assert r1 in area0.routers_in_area
        assert r2 in area0.routers_in_area
        assert r3 not in area0.routers_in_area

        assert area0.topology_graph is not None
        assert len(area0.topology_graph) == 2
        assert RouterID("R1") in area0.topology_graph
        assert RouterID("R2") in area0.topology_graph
        assert area0.topology_graph.get_edge_weight(RouterID("R1"), RouterID("R2")) == 10

    def test_ospf_area_add_lsa_to_lsdb(self):
        area0 = OSPFArea(area_id=AreaID("0"))
        rlsa1 = RouterLSA(
            advertising_router=RouterID("1.1.1.1"), 
            link_state_id=RouterID("1.1.1.1"), 
            ls_sequence_number=100, 
            ls_age=50
        )
        area0.add_lsa_to_lsdb(rlsa1)
        key1 = (LSAType.ROUTER_LSA, RouterID("1.1.1.1"), RouterID("1.1.1.1"))
        assert key1 in area0.lsdb
        assert area0.lsdb[key1] == rlsa1

        # Add newer LSA
        rlsa2 = RouterLSA(
            advertising_router=RouterID("1.1.1.1"), 
            link_state_id=RouterID("1.1.1.1"), 
            ls_sequence_number=101, 
            ls_age=20
        )
        area0.add_lsa_to_lsdb(rlsa2)
        assert area0.lsdb[key1] == rlsa2 # Should be updated

        # Add older LSA (should not update)
        rlsa_old = RouterLSA(
            advertising_router=RouterID("1.1.1.1"), 
            link_state_id=RouterID("1.1.1.1"), 
            ls_sequence_number=100, 
            ls_age=200
        )
        area0.add_lsa_to_lsdb(rlsa_old)
        assert area0.lsdb[key1] == rlsa2 # Should still be rlsa2

        # Add LSA with same sequence but younger age (should update)
        rlsa_younger = RouterLSA(
            advertising_router=RouterID("1.1.1.1"), 
            link_state_id=RouterID("1.1.1.1"), 
            ls_sequence_number=101, 
            ls_age=10 # Younger than rlsa2's age 20
        )
        area0.add_lsa_to_lsdb(rlsa_younger)
        assert area0.lsdb[key1] == rlsa_younger

        # Add MaxAge LSA (should be accepted)
        rlsa_maxage = RouterLSA(
            advertising_router=RouterID("1.1.1.1"), 
            link_state_id=RouterID("1.1.1.1"), 
            ls_sequence_number=101, # Can be same or newer
            ls_age=3600 
        )
        area0.add_lsa_to_lsdb(rlsa_maxage)
        assert area0.lsdb[key1] == rlsa_maxage 
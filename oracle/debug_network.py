import oci

config = {
    "user": "ocid1.user.oc1..aaaaaaaabs7fgezeif7aoxflpjxl34dle2vc6u5qdppfoctuo6x4mqtankva",
    "fingerprint": "67:96:db:1f:f0:94:b7:ff:f8:1a:91:ed:de:5b:f1:cf",
    "tenancy": "ocid1.tenancy.oc1..aaaaaaaa77xucbzcg6sufcsp7oct5nwxlqqf66g4q3ejkh2lucopepcg4a6a",
    "region": "ap-hyderabad-1",
    "key_file": "C:/Users/veera/.ssh/id_rsa_oracle",
}

network_client = oci.core.VirtualNetworkClient(config)
root_compartment = "ocid1.tenancy.oc1..aaaaaaaa77xucbzcg6sufcsp7oct5nwxlqqf66g4q3ejkh2lucopepcg4a6a"

vcns = network_client.list_vcns(compartment_id=root_compartment).data
for vcn in vcns:
    print(f"\nVCN: {vcn.display_name}")
    
    rts = network_client.list_route_tables(compartment_id=root_compartment, vcn_id=vcn.id).data
    print(f"  Route tables: {len(rts)}")
    for rt in rts:
        print(f"    - {rt.display_name} ({rt.id})")
        print(f"      Routes: {len(rt.route_rules)}")
        for rule in rt.route_rules:
            print(f"        {rule.destination} -> {rule.network_entity_id}")
    
    igws = network_client.list_internet_gateways(compartment_id=root_compartment, vcn_id=vcn.id).data
    print(f"  IGWs: {len(igws)}")
    for igw in igws:
        print(f"    - {igw.display_name} ({igw.id})")

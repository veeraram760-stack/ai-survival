import oci

config = {
    "user": "ocid1.user.oc1..aaaaaaaabs7fgezeif7aoxflpjxl34dle2vc6u5qdppfoctuo6x4mqtankva",
    "fingerprint": "67:96:db:1f:f0:94:b7:ff:f8:1a:91:ed:de:5b:f1:cf",
    "tenancy": "ocid1.tenancy.oc1..aaaaaaaa77xucbzcg6sufcsp7oct5nwxlqqf66g4q3ejkh2lucopepcg4a6a",
    "region": "ap-hyderabad-1",
    "key_file": "C:/Users/veera/.ssh/id_rsa_oracle",
}

compute_client = oci.core.ComputeClient(config)
network_client = oci.core.VirtualNetworkClient(config)
compartment_id = "ocid1.compartment.oc1..aaaaaaaappuxkojmokxox4v2aanula5sec4wtbxpopbd46kmw6535e7notvq"

# Terminate test instance
instances = compute_client.list_instances(compartment_id=compartment_id).data
for inst in instances:
    if "test" in inst.display_name.lower():
        print(f"Terminating {inst.display_name}...")
        compute_client.terminate_instance(inst.id)

# Delete test VCN
vcns = network_client.list_vcns(compartment_id=compartment_id).data
for vcn in vcns:
    if "test" in vcn.display_name.lower():
        print(f"Deleting VCN {vcn.display_name}...")
        subnets = network_client.list_subnets(compartment_id=compartment_id, vcn_id=vcn.id).data
        for subnet in subnets:
            network_client.delete_subnet(subnet.id)
        
        igws = network_client.list_internet_gateways(compartment_id=compartment_id, vcn_id=vcn.id).data
        for igw in igws:
            network_client.delete_internet_gateway(igw.id)
        
        rts = network_client.list_route_tables(compartment_id=compartment_id, vcn_id=vcn.id).data
        for rt in rts:
            if not rt.display_name.startswith("Default"):
                network_client.delete_route_table(rt.id)
        
        sls = network_client.list_security_lists(compartment_id=compartment_id, vcn_id=vcn.id).data
        for sl in sls:
            if not sl.display_name.startswith("Default"):
                network_client.delete_security_list(sl.id)
        
        network_client.delete_vcn(vcn.id)

print("Cleanup complete")

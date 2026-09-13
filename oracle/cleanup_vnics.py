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

# Find and detach VNICs from terminated instances
instances = compute_client.list_instances(compartment_id=compartment_id).data
for inst in instances:
    if inst.lifecycle_state == "TERMINATED":
        print(f"Checking VNICs for terminated instance: {inst.display_name}")
        vnic_attachments = compute_client.list_vnic_attachments(compartment_id=compartment_id, instance_id=inst.id).data
        for vnic_att in vnic_attachments:
            print(f"  Found VNIC: {vnic_att.vnic_id}")
            try:
                # Try to detach VNIC
                compute_client.detach_vnic(vnic_att.vnic_id)
                print(f"    Detached VNIC")
            except Exception as e:
                print(f"    Could not detach: {e}")

# Now try to delete test VCN again
vcns = network_client.list_vcns(compartment_id=compartment_id).data
for vcn in vcns:
    if "test" in vcn.display_name.lower():
        print(f"\nDeleting test VCN: {vcn.display_name}")
        subnets = network_client.list_subnets(compartment_id=compartment_id, vcn_id=vcn.id).data
        for subnet in subnets:
            try:
                network_client.delete_subnet(subnet.id)
                print(f"  Deleted subnet: {subnet.display_name}")
            except Exception as e:
                print(f"  Failed to delete subnet: {e}")
        
        try:
            network_client.delete_vcn(vcn.id)
            print(f"  Deleted VCN: {vcn.display_name}")
        except Exception as e:
            print(f"  Failed to delete VCN: {e}")

print("\nDone!")

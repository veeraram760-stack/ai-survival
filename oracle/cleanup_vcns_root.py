import oci
import time

config = {
    "user": "ocid1.user.oc1..aaaaaaaabs7fgezeif7aoxflpjxl34dle2vc6u5qdppfoctuo6x4mqtankva",
    "fingerprint": "67:96:db:1f:f0:94:b7:ff:f8:1a:91:ed:de:5b:f1:cf",
    "tenancy": "ocid1.tenancy.oc1..aaaaaaaa77xucbzcg6sufcsp7oct5nwxlqqf66g4q3ejkh2lucopepcg4a6a",
    "region": "ap-hyderabad-1",
    "key_file": "C:/Users/veera/.ssh/id_rsa_oracle",
}

network_client = oci.core.VirtualNetworkClient(config)
root_compartment = "ocid1.tenancy.oc1..aaaaaaaa77xucbzcg6sufcsp7oct5nwxlqqf66g4q3ejkh2lucopepcg4a6a"

# List all VCNs in root compartment
vcns = network_client.list_vcns(compartment_id=root_compartment).data
print(f"Found {len(vcns)} VCN(s) in root compartment")

for vcn in vcns:
    print(f"\nProcessing VCN: {vcn.display_name} ({vcn.id})")
    
    # 1. Delete subnets
    print("  Deleting subnets...")
    subnets = network_client.list_subnets(compartment_id=root_compartment, vcn_id=vcn.id).data
    for subnet in subnets:
        try:
            network_client.delete_subnet(subnet.id)
            print(f"    Deleted subnet: {subnet.display_name}")
            time.sleep(2)
        except Exception as e:
            print(f"    Failed to delete subnet {subnet.display_name}: {e}")
    
    # 2. Delete internet gateways
    print("  Deleting internet gateways...")
    igws = network_client.list_internet_gateways(compartment_id=root_compartment, vcn_id=vcn.id).data
    for igw in igws:
        try:
            network_client.delete_internet_gateway(igw.id)
            print(f"    Deleted IGW: {igw.display_name}")
            time.sleep(2)
        except Exception as e:
            print(f"    Failed to delete IGW {igw.display_name}: {e}")
    
    # 3. Delete route tables (except default)
    print("  Deleting route tables...")
    rts = network_client.list_route_tables(compartment_id=root_compartment, vcn_id=vcn.id).data
    for rt in rts:
        if not rt.display_name.startswith("Default"):
            try:
                network_client.delete_route_table(rt.id)
                print(f"    Deleted route table: {rt.display_name}")
                time.sleep(2)
            except Exception as e:
                print(f"    Failed to delete route table {rt.display_name}: {e}")
    
    # 4. Delete security lists (except default)
    print("  Deleting security lists...")
    sls = network_client.list_security_lists(compartment_id=root_compartment, vcn_id=vcn.id).data
    for sl in sls:
        if not sl.display_name.startswith("Default"):
            try:
                network_client.delete_security_list(sl.id)
                print(f"    Deleted security list: {sl.display_name}")
                time.sleep(2)
            except Exception as e:
                print(f"    Failed to delete security list {sl.display_name}: {e}")
    
    # 5. Delete DHCP options (except default)
    print("  Deleting DHCP options...")
    dhcps = network_client.list_dhcp_options(compartment_id=root_compartment, vcn_id=vcn.id).data
    for dhcp in dhcps:
        if not dhcp.display_name.startswith("Default"):
            try:
                network_client.delete_dhcp_options(dhcp.id)
                print(f"    Deleted DHCP options: {dhcp.display_name}")
                time.sleep(2)
            except Exception as e:
                print(f"    Failed to delete DHCP options {dhcp.display_name}: {e}")
    
    # 6. Now delete the VCN
    print("  Deleting VCN...")
    try:
        network_client.delete_vcn(vcn.id)
        print(f"    Deleted VCN: {vcn.display_name}")
    except Exception as e:
        print(f"    Failed to delete VCN: {e}")

print("\nCleanup complete!")

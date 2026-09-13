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

# First, update the default route table for vcn-20260729-1504 to remove the IGW route
print("Fixing default route table for vcn-20260729-1504...")
rt_id = "ocid1.routetable.oc1.ap-hyderabad-1.aaaaaaaatwav4szpswmbhw3du6h65q2eytzryefcifjulyvrkm7dfgkjyttq"
try:
    update_details = oci.core.models.UpdateRouteTableDetails(
        route_rules=[]
    )
    network_client.update_route_table(rt_id, update_details)
    print("  Route table updated successfully")
    time.sleep(3)
except Exception as e:
    print(f"  Failed to update route table: {e}")

# Now delete IGWs
vcns = network_client.list_vcns(compartment_id=root_compartment).data
for vcn in vcns:
    print(f"\nProcessing VCN: {vcn.display_name}")
    
    igws = network_client.list_internet_gateways(compartment_id=root_compartment, vcn_id=vcn.id).data
    for igw in igws:
        try:
            network_client.delete_internet_gateway(igw.id)
            print(f"  Deleted IGW: {igw.display_name}")
            time.sleep(2)
        except Exception as e:
            print(f"  Failed to delete IGW {igw.display_name}: {e}")
    
    # Try deleting VCN
    try:
        network_client.delete_vcn(vcn.id)
        print(f"  Deleted VCN: {vcn.display_name}")
    except Exception as e:
        print(f"  Failed to delete VCN: {e}")

print("\nDone!")

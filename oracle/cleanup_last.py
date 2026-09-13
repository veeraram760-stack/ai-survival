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

# The problematic route table
rt_id = "ocid1.routetable.oc1.ap-hyderabad-1.aaaaaaaaxmnfyeupd2wldtn3hg7bnid7qvyihyxwrnjpbauu7ufuzgmtstea"
igw_id = "ocid1.internetgateway.oc1.ap-hyderabad-1.aaaaaaaawbga3xstgkwzomgfkwj2exudqofoafuoxzo2puuolclcp4mrky5q"
vcn_id = "ocid1.vcn.oc1.ap-hyderabad-1.amaaaaaakroosiqaazsiambobkhpfbp3l7xl54pkkpg4xf7m7eh4anvklj6q"

# Try to delete the route table directly
print(f"Deleting route table {rt_id}...")
try:
    network_client.delete_route_table(rt_id)
    print("  Deleted route table")
    time.sleep(3)
except Exception as e:
    print(f"  Failed: {e}")

# Try to delete the IGW
print(f"Deleting IGW {igw_id}...")
try:
    network_client.delete_internet_gateway(igw_id)
    print("  Deleted IGW")
    time.sleep(3)
except Exception as e:
    print(f"  Failed: {e}")

# Try to delete the VCN
print(f"Deleting VCN {vcn_id}...")
try:
    network_client.delete_vcn(vcn_id)
    print("  Deleted VCN")
except Exception as e:
    print(f"  Failed: {e}")

print("\nDone!")

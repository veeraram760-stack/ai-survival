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

# The problematic route table for vcn-20260729-1939
rt_id = "ocid1.routetable.oc1.ap-hyderabad-1.aaaaaaaaxmnfyeupd2wldtn3hg7bnid7qvyihyxwrnjpbauu7ufuzgmtstea"

# Get current route table details
print("Getting route table details...")
rt_details = network_client.get_route_table(rt_id).data
print(f"  Route table: {rt_details.display_name}")
print(f"  Routes: {len(rt_details.route_rules)}")
for rule in rt_details.route_rules:
    print(f"    {rule.destination} -> {rule.network_entity_id}")

# Update to remove all routes
print("\nUpdating route table to remove all routes...")
update_details = oci.core.models.UpdateRouteTableDetails(
    route_rules=[]
)
network_client.update_route_table(rt_id, update_details)
print("  Update sent")

# Wait a moment
time.sleep(5)

# Verify the update
print("\nVerifying update...")
rt_details = network_client.get_route_table(rt_id).data
print(f"  Routes after update: {len(rt_details.route_rules)}")
for rule in rt_details.route_rules:
    print(f"    {rule.destination} -> {rule.network_entity_id}")

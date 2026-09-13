import oci

config = {
    "user": "ocid1.user.oc1..aaaaaaaabs7fgezeif7aoxflpjxl34dle2vc6u5qdppfoctuo6x4mqtankva",
    "fingerprint": "67:96:db:1f:f0:94:b7:ff:f8:1a:91:ed:de:5b:f1:cf",
    "tenancy": "ocid1.tenancy.oc1..aaaaaaaa77xucbzcg6sufcsp7oct5nwxlqqf66g4q3ejkh2lucopepcg4a6a",
    "region": "ap-hyderabad-1",
    "key_file": "C:/Users/veera/.ssh/id_rsa_oracle",
}

network_client = oci.core.VirtualNetworkClient(config)
compartment_id = "ocid1.compartment.oc1..aaaaaaaappuxkojmokxox4v2aanula5sec4wtbxpopbd46kmw6535e7notvq"

# List existing VCNs
vcns = network_client.list_vcns(compartment_id=compartment_id).data
print(f"Existing VCNs: {len(vcns)}")
for vcn in vcns:
    print(f"  - {vcn.display_name} ({vcn.id}) - {vcn.lifecycle_state} - CIDR: {vcn.cidr_block}")

# List subnets
subnets = network_client.list_subnets(compartment_id=compartment_id).data
print(f"\nExisting Subnets: {len(subnets)}")
for subnet in subnets:
    print(f"  - {subnet.display_name} ({subnet.id}) - {subnet.lifecycle_state} - CIDR: {subnet.cidr_block}")

# List internet gateways
igws = network_client.list_internet_gateways(compartment_id=compartment_id).data
print(f"\nExisting Internet Gateways: {len(igws)}")
for igw in igws:
    print(f"  - {igw.display_name} ({igw.id}) - {igw.lifecycle_state}")

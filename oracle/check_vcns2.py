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
user_compartment = "ocid1.compartment.oc1..aaaaaaaappuxkojmokxox4v2aanula5sec4wtbxpopbd46kmw6535e7notvq"

# Check root compartment
vcns_root = network_client.list_vcns(compartment_id=root_compartment).data
print(f"Root compartment VCNs: {len(vcns_root)}")
for vcn in vcns_root:
    print(f"  - {vcn.display_name} ({vcn.id}) - {vcn.lifecycle_state}")

# Check user compartment
vcns_user = network_client.list_vcns(compartment_id=user_compartment).data
print(f"\nUser compartment VCNs: {len(vcns_user)}")
for vcn in vcns_user:
    print(f"  - {vcn.display_name} ({vcn.id}) - {vcn.lifecycle_state}")

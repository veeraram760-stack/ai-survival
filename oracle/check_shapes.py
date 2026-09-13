import oci

config = {
    "user": "ocid1.user.oc1..aaaaaaaabs7fgezeif7aoxflpjxl34dle2vc6u5qdppfoctuo6x4mqtankva",
    "fingerprint": "67:96:db:1f:f0:94:b7:ff:f8:1a:91:ed:de:5b:f1:cf",
    "tenancy": "ocid1.tenancy.oc1..aaaaaaaa77xucbzcg6sufcsp7oct5nwxlqqf66g4q3ejkh2lucopepcg4a6a",
    "region": "ap-hyderabad-1",
    "key_file": "C:/Users/veera/.ssh/id_rsa_oracle",
}

compute_client = oci.core.ComputeClient(config)
identity_client = oci.identity.IdentityClient(config)

compartment_id = "ocid1.compartment.oc1..aaaaaaaappuxkojmokxox4v2aanula5sec4wtbxpopbd46kmw6535e7notvq"

# List availability domains
print("Availability Domains:")
ads = identity_client.list_availability_domains(compartment_id=compartment_id).data
for ad in ads:
    print(f"  - {ad.name}")

# List shapes available for A1.Flex
print("\nShapes for A1.Flex:")
shapes = compute_client.list_shapes(
    compartment_id=compartment_id,
    shape="VM.Standard.A1.Flex"
).data
for shape in shapes:
    print(f"  - {shape.shape}")

# List shapes available in the region
print("\nAll shapes:")
all_shapes = compute_client.list_shapes(compartment_id=compartment_id).data
for shape in all_shapes[:20]:
    print(f"  - {shape.shape}")

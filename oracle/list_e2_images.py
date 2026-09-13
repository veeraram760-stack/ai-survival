import oci

config = {
    "user": "ocid1.user.oc1..aaaaaaaabs7fgezeif7aoxflpjxl34dle2vc6u5qdppfoctuo6x4mqtankva",
    "fingerprint": "67:96:db:1f:f0:94:b7:ff:f8:1a:91:ed:de:5b:f1:cf",
    "tenancy": "ocid1.tenancy.oc1..aaaaaaaa77xucbzcg6sufcsp7oct5nwxlqqf66g4q3ejkh2lucopepcg4a6a",
    "region": "ap-hyderabad-1",
    "key_file": "C:/Users/veera/.ssh/id_rsa_oracle",
}

compute_client = oci.core.ComputeClient(config)
compartment_id = "ocid1.compartment.oc1..aaaaaaaappuxkojmokxox4v2aanula5sec4wtbxpopbd46kmw6535e7notvq"

# List images compatible with E2.1.Micro
images = compute_client.list_images(
    compartment_id=compartment_id,
    operating_system="Oracle Linux",
    shape="VM.Standard.E2.1.Micro",
    lifecycle_state="AVAILABLE",
).data

print(f"Found {len(images)} Oracle Linux images for E2.1.Micro:")
for img in images[:10]:
    print(f"  - {img.display_name} ({img.id})")

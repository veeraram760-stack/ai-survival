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
ad = "Uocm:AP-HYDERABAD-AD-1"
image_id = "ocid1.image.oc1.ap-hyderabad-1.aaaaaaaacmnvmptgyentlnimqs2fm7dw3mkktpbujbg33my7m4eek4qp4oua"

# Get a subnet
subnets = network_client.list_subnets(compartment_id=compartment_id).data
if subnets:
    subnet_id = subnets[0].id
    print(f"Using subnet: {subnet_id}")
else:
    print("No subnets found")
    exit(1)

# Try to launch a simple instance
try:
    result = compute_client.launch_instance(
        launch_instance_details=oci.core.models.LaunchInstanceDetails(
            compartment_id=compartment_id,
            display_name="test-instance",
            availability_domain=ad,
            shape="VM.Standard.A1.Flex",
            shape_config=oci.core.models.LaunchInstanceShapeConfigDetails(
                ocpus=1,
                memory_in_gbs=6,
            ),
            source_details=oci.core.models.InstanceSourceViaImageDetails(
                source_type="image",
                image_id=image_id,
            ),
            create_vnic_details=oci.core.models.CreateVnicDetails(
                subnet_id=subnet_id,
                assign_public_ip=True,
            ),
            metadata={
                "ssh_authorized_keys": "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCc+uICDzcjhDUhFcA3B0Fjh3w5al0jqS7UCOSBy/UBC7R5gZO8Mbz+ZjkOK6Ua75yt/Fd4Uvla3oJwf7U3LBxFfNrgZ83TeXjREiwi1fgO//oCRd7zvmSWJOLldoiG5wQRqKgTZQkNg7m/J6AoRGE4L9JXNUcoZa8uQuNgty2Y/dr8pXizM9rSQz3TFos50v50bIXQMFBXtceAAtdYl0RNn8434a54YZVNNhbQg2ngvRyEiibU3d+3TGwGWlfJPhi2RR0qJqG2H0fjVNe/BqesGIuYfNJPW/kX3k5k2qY2LbVxPlGHAuDjqlz50eeYcAzLVhUDxTyD8RIanbSxlynR oracle-ai-survival"
            },
        )
    )
    print("Instance launched:", result.data.id)
except Exception as e:
    print("Error:", e)

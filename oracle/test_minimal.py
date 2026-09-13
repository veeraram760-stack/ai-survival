#!/usr/bin/env python3
"""Minimal test instance creation without complex user-data"""

import oci
from pathlib import Path

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
ad = "NGKk:AP-HYDERABAD-1-AD-1"

# Create minimal VCN
print("Creating minimal VCN...")
vcn = network_client.create_vcn(
    create_vcn_details=oci.core.models.CreateVcnDetails(
        compartment_id=compartment_id,
        display_name="test-vcn",
        cidr_block="10.0.0.0/16",
    )
).data
oci.wait_until(network_client, network_client.get_vcn(vcn.id), "lifecycle_state", "AVAILABLE", max_wait_seconds=120)

# Create IGW
igw = network_client.create_internet_gateway(
    create_internet_gateway_details=oci.core.models.CreateInternetGatewayDetails(
        compartment_id=compartment_id,
        display_name="test-igw",
        vcn_id=vcn.id,
        is_enabled=True,
    )
).data

# Create route table
rt = network_client.create_route_table(
    create_route_table_details=oci.core.models.CreateRouteTableDetails(
        compartment_id=compartment_id,
        display_name="test-rt",
        vcn_id=vcn.id,
        route_rules=[
            oci.core.models.RouteRule(
                destination="0.0.0.0/0",
                destination_type="CIDR_BLOCK",
                network_entity_id=igw.id,
            )
        ],
    )
).data

# Create security list
sl = network_client.create_security_list(
    create_security_list_details=oci.core.models.CreateSecurityListDetails(
        compartment_id=compartment_id,
        display_name="test-sl",
        vcn_id=vcn.id,
        egress_security_rules=[oci.core.models.EgressSecurityRule(protocol="all", destination="0.0.0.0/0")],
        ingress_security_rules=[
            oci.core.models.IngressSecurityRule(
                protocol="6", source="0.0.0.0/0", is_stateless=False,
                tcp_options=oci.core.models.TcpOptions(destination_port_range=oci.core.models.PortRange(min=22, max=22)),
            ),
        ],
    )
).data

# Create subnet
subnet = network_client.create_subnet(
    create_subnet_details=oci.core.models.CreateSubnetDetails(
        compartment_id=compartment_id,
        display_name="test-subnet",
        vcn_id=vcn.id,
        cidr_block="10.0.1.0/24",
        route_table_id=rt.id,
        security_list_ids=[sl.id],
        dhcp_options_id=vcn.default_dhcp_options_id,
    )
).data

# Get image
image_id = compute_client.list_images(
    compartment_id=compartment_id,
    operating_system="Oracle Linux",
    shape="VM.Standard.E2.1.Micro",
    lifecycle_state="AVAILABLE",
).data[0].id

# Read SSH key
with open(r"C:\Users\veera\.ssh\id_rsa_oracle.pub", "r") as f:
    ssh_key = f.read().strip()

# Create instance with minimal user-data
print("Creating test instance...")
instance = compute_client.launch_instance(
    launch_instance_details=oci.core.models.LaunchInstanceDetails(
        compartment_id=compartment_id,
        display_name="test-instance",
        availability_domain=ad,
        shape="VM.Standard.E2.1.Micro",
        shape_config=oci.core.models.LaunchInstanceShapeConfigDetails(ocpus=1, memory_in_gbs=1),
        source_details=oci.core.models.InstanceSourceViaImageDetails(source_type="image", image_id=image_id),
        create_vnic_details=oci.core.models.CreateVnicDetails(subnet_id=subnet.id, assign_public_ip=True),
        metadata={"ssh_authorized_keys": ssh_key},
    )
).data
print(f"Instance created: {instance.id}")

print("Waiting for RUNNING...")
try:
    oci.wait_until(compute_client, compute_client.get_instance(instance.id), "lifecycle_state", "RUNNING", max_wait_seconds=600)
    instance = compute_client.get_instance(instance.id).data
    print(f"Instance is RUNNING: {instance.lifecycle_state}")
    
    vnic = compute_client.list_vnic_attachments(compartment_id=compartment_id, instance_id=instance.id).data[0]
    vnic_info = compute_client.get_vnic(vnic.vnic_id).data
    print(f"Public IP: {vnic_info.public_ip}")
except Exception as e:
    print(f"Wait failed: {e}")
    instance = compute_client.get_instance(instance.id).data
    print(f"Current state: {instance.lifecycle_state}")

#!/usr/bin/env python3
"""Test if user-data causes instance termination"""

import oci
import base64
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
vcn = network_client.create_vcn(
    create_vcn_details=oci.core.models.CreateVcnDetails(
        compartment_id=compartment_id, display_name="ud-test-vcn", cidr_block="10.0.0.0/16"
    )
).data
oci.wait_until(network_client, network_client.get_vcn(vcn.id), "lifecycle_state", "AVAILABLE", max_wait_seconds=120)

igw = network_client.create_internet_gateway(
    create_internet_gateway_details=oci.core.models.CreateInternetGatewayDetails(
        compartment_id=compartment_id, display_name="ud-test-igw", vcn_id=vcn.id, is_enabled=True
    )
).data

rt = network_client.create_route_table(
    create_route_table_details=oci.core.models.CreateRouteTableDetails(
        compartment_id=compartment_id, display_name="ud-test-rt", vcn_id=vcn.id,
        route_rules=[oci.core.models.RouteRule(destination="0.0.0.0/0", destination_type="CIDR_BLOCK", network_entity_id=igw.id)]
    )
).data

sl = network_client.create_security_list(
    create_security_list_details=oci.core.models.CreateSecurityListDetails(
        compartment_id=compartment_id, display_name="ud-test-sl", vcn_id=vcn.id,
        egress_security_rules=[oci.core.models.EgressSecurityRule(protocol="all", destination="0.0.0.0/0")],
        ingress_security_rules=[
            oci.core.models.IngressSecurityRule(
                protocol="6", source="0.0.0.0/0", is_stateless=False,
                tcp_options=oci.core.models.TcpOptions(destination_port_range=oci.core.models.PortRange(min=22, max=22)),
            ),
        ],
    )
).data

subnet = network_client.create_subnet(
    create_subnet_details=oci.core.models.CreateSubnetDetails(
        compartment_id=compartment_id, display_name="ud-test-subnet", vcn_id=vcn.id,
        cidr_block="10.0.1.0/24", route_table_id=rt.id, security_list_ids=[sl.id],
        dhcp_options_id=vcn.default_dhcp_options_id,
    )
).data

image_id = compute_client.list_images(
    compartment_id=compartment_id, operating_system="Oracle Linux",
    shape="VM.Standard.E2.1.Micro", lifecycle_state="AVAILABLE"
).data[0].id

with open(r"C:\Users\veera\.ssh\id_rsa_oracle.pub", "r") as f:
    ssh_key = f.read().strip()

# Minimal user-data that just echoes
user_data = base64.b64encode(b"#!/bin/bash\necho 'User-data executed'\n").decode()

print("Creating test instance with minimal user-data...")
instance = compute_client.launch_instance(
    launch_instance_details=oci.core.models.LaunchInstanceDetails(
        compartment_id=compartment_id, display_name="ud-test",
        availability_domain=ad, shape="VM.Standard.E2.1.Micro",
        shape_config=oci.core.models.LaunchInstanceShapeConfigDetails(ocpus=1, memory_in_gbs=1),
        source_details=oci.core.models.InstanceSourceViaImageDetails(source_type="image", image_id=image_id),
        create_vnic_details=oci.core.models.CreateVnicDetails(subnet_id=subnet.id, assign_public_ip=True),
        metadata={"ssh_authorized_keys": ssh_key, "user_data": user_data},
    )
).data
print(f"Instance created: {instance.id}")

import time
for i in range(12):
    time.sleep(10)
    inst = compute_client.get_instance(instance.id).data
    print(f"  [{i*10}s] State: {inst.lifecycle_state}")
    if inst.lifecycle_state == "RUNNING":
        print("Instance is RUNNING!")
        break
    elif inst.lifecycle_state == "TERMINATED":
        print("Instance was TERMINATED!")
        break

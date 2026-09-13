#!/usr/bin/env python3
"""
OCI Python SDK Single-Instance Deployment Script for AI Survival System
Deploys all services on one E2.1.Micro instance to stay within Free Tier limits
"""

import base64
import os
import sys
import time
from pathlib import Path

try:
    import oci
except ImportError:
    print("Error: OCI SDK not installed. Run: pip install oci")
    sys.exit(1)

ORACLE_DIR = Path(__file__).parent
TFVARS_PATH = ORACLE_DIR / "terraform.tfvars"
SSH_KEY_PATH = Path(r"C:\Users\veera\.ssh\id_rsa_oracle")
SSH_PUB_KEY_PATH = Path(r"C:\Users\veera\.ssh\id_rsa_oracle.pub")

AD = "NGKk:AP-HYDERABAD-1-AD-1"
VCN_CIDR = "10.0.0.0/16"
PUBLIC_SUBNET_CIDR = "10.0.1.0/24"


def parse_tfvars(path):
    config = {
        "region": "ap-hyderabad-1",
        "tenancy_ocid": "ocid1.tenancy.oc1..aaaaaaaa77xucbzcg6sufcsp7oct5nwxlqqf66g4q3ejkh2lucopepcg4a6a",
        "user_ocid": "ocid1.user.oc1..aaaaaaaabs7fgezeif7aoxflpjxl34dle2vc6u5qdppfoctuo6x4mqtankva",
        "fingerprint": "67:96:db:1f:f0:94:b7:ff:f8:1a:91:ed:de:5b:f1:cf",
        "private_key_path": r"C:\Users\veera\.ssh\id_rsa_oracle",
        "compartment_id": "ocid1.compartment.oc1..aaaaaaaappuxkojmokxox4v2aanula5sec4wtbxpopbd46kmw6535e7notvq",
        "ssh_public_key_path": r"C:\Users\veera\.ssh\id_rsa_oracle.pub",
    }
    if not path.exists():
        return config
    
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip('"')
                if key in config:
                    config[key] = value
    return config


def read_ssh_key(path):
    with open(path, "r") as f:
        return f.read().strip()


def read_user_data(path):
    with open(path, "r") as f:
        return base64.b64encode(f.read().encode()).decode()


def main():
    print("=" * 60)
    print("AI Survival System - Oracle Cloud Single-Instance Deployment")
    print("=" * 60)
    
    config = parse_tfvars(TFVARS_PATH)
    print(f"Region: {config['region']}")
    print(f"Compartment: {config['compartment_id']}")
    print()
    
    print("Reading SSH keys...")
    ssh_key = read_ssh_key(SSH_PUB_KEY_PATH)
    print(f"  SSH key loaded from {SSH_PUB_KEY_PATH}")
    
    print("Initializing OCI clients...")
    config_file_path = str(Path.home() / ".oci" / "config")
    try:
        oci_config = oci.config.from_file(config_file_path, "ai-survival")
        print(f"  Loaded OCI config from {config_file_path}")
    except Exception as e:
        print(f"Error loading OCI config: {e}")
        sys.exit(1)
    
    identity_client = oci.identity.IdentityClient(oci_config)
    network_client = oci.core.VirtualNetworkClient(oci_config)
    compute_client = oci.core.ComputeClient(oci_config)
    
    try:
        tenancy = identity_client.get_tenancy(config["tenancy_ocid"]).data
        print(f"  Connected to tenancy: {tenancy.name}")
    except Exception as e:
        print(f"Authentication failed: {e}")
        sys.exit(1)
    
    print()
    print("=" * 60)
    print("STEP 1: Creating Network Infrastructure")
    print("=" * 60)
    
    print("Creating VCN...")
    vcn = network_client.create_vcn(
        create_vcn_details=oci.core.models.CreateVcnDetails(
            compartment_id=config["compartment_id"],
            display_name="ai-survival-vcn",
            cidr_block=VCN_CIDR,
        )
    ).data
    print(f"  VCN created: {vcn.display_name} ({vcn.id})")
    
    oci.wait_until(network_client, network_client.get_vcn(vcn.id), "lifecycle_state", "AVAILABLE", max_wait_seconds=120)
    
    print("Creating Internet Gateway...")
    igw = network_client.create_internet_gateway(
        create_internet_gateway_details=oci.core.models.CreateInternetGatewayDetails(
            compartment_id=config["compartment_id"],
            display_name="ai-survival-igw",
            vcn_id=vcn.id,
            is_enabled=True,
        )
    ).data
    print(f"  IGW created: {igw.display_name} ({igw.id})")
    
    print("Creating Route Table...")
    public_rt = network_client.create_route_table(
        create_route_table_details=oci.core.models.CreateRouteTableDetails(
            compartment_id=config["compartment_id"],
            display_name="Public Route Table",
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
    print(f"  Route table created: {public_rt.display_name} ({public_rt.id})")
    
    print("Creating Security List...")
    public_sl = network_client.create_security_list(
        create_security_list_details=oci.core.models.CreateSecurityListDetails(
            compartment_id=config["compartment_id"],
            display_name="Public Security List",
            vcn_id=vcn.id,
            egress_security_rules=[
                oci.core.models.EgressSecurityRule(protocol="all", destination="0.0.0.0/0")
            ],
            ingress_security_rules=[
                oci.core.models.IngressSecurityRule(
                    protocol="6", source="0.0.0.0/0", is_stateless=False,
                    tcp_options=oci.core.models.TcpOptions(destination_port_range=oci.core.models.PortRange(min=22, max=22)),
                ),
                oci.core.models.IngressSecurityRule(
                    protocol="6", source="0.0.0.0/0", is_stateless=False,
                    tcp_options=oci.core.models.TcpOptions(destination_port_range=oci.core.models.PortRange(min=80, max=80)),
                ),
                oci.core.models.IngressSecurityRule(
                    protocol="6", source="0.0.0.0/0", is_stateless=False,
                    tcp_options=oci.core.models.TcpOptions(destination_port_range=oci.core.models.PortRange(min=443, max=443)),
                ),
                oci.core.models.IngressSecurityRule(
                    protocol="6", source="0.0.0.0/0", is_stateless=False,
                    tcp_options=oci.core.models.TcpOptions(destination_port_range=oci.core.models.PortRange(min=3000, max=3000)),
                ),
                oci.core.models.IngressSecurityRule(
                    protocol="6", source="0.0.0.0/0", is_stateless=False,
                    tcp_options=oci.core.models.TcpOptions(destination_port_range=oci.core.models.PortRange(min=8000, max=8000)),
                ),
            ],
        )
    ).data
    print(f"  Security list created: {public_sl.display_name} ({public_sl.id})")
    
    print()
    print("=" * 60)
    print("STEP 2: Creating Subnet")
    print("=" * 60)
    
    vcn_info = network_client.get_vcn(vcn.id).data
    public_subnet = network_client.create_subnet(
        create_subnet_details=oci.core.models.CreateSubnetDetails(
            compartment_id=config["compartment_id"],
            display_name="Public Subnet",
            vcn_id=vcn.id,
            cidr_block=PUBLIC_SUBNET_CIDR,
            route_table_id=public_rt.id,
            security_list_ids=[public_sl.id],
            dhcp_options_id=vcn_info.default_dhcp_options_id,
        )
    ).data
    print(f"  Subnet created: {public_subnet.display_name} ({public_subnet.id})")
    
    print()
    print("=" * 60)
    print("STEP 3: Creating Instance")
    print("=" * 60)
    
    image_id = compute_client.list_images(
        compartment_id=config["compartment_id"],
        operating_system="Oracle Linux",
        shape="VM.Standard.E2.1.Micro",
        lifecycle_state="AVAILABLE",
    ).data[0].id
    print(f"  Using image: {image_id}")
    
    user_data_path = ORACLE_DIR / "user-data-simple.sh"
    if not user_data_path.exists():
        print(f"ERROR: {user_data_path} not found!")
        sys.exit(1)
    
    with open(user_data_path, "r") as f:
        user_data = base64.b64encode(f.read().encode()).decode()
    
    print("Creating instance: ai-survival-all-in-one...")
    instance = compute_client.launch_instance(
        launch_instance_details=oci.core.models.LaunchInstanceDetails(
            compartment_id=config["compartment_id"],
            display_name="ai-survival-all-in-one",
            availability_domain=AD,
            shape="VM.Standard.E2.1.Micro",
            shape_config=oci.core.models.LaunchInstanceShapeConfigDetails(
                ocpus=1,
                memory_in_gbs=1,
            ),
            source_details=oci.core.models.InstanceSourceViaImageDetails(
                source_type="image",
                image_id=image_id,
            ),
            create_vnic_details=oci.core.models.CreateVnicDetails(
                subnet_id=public_subnet.id,
                assign_public_ip=True,
            ),
            metadata={
                "ssh_authorized_keys": ssh_key,
                "user_data": user_data,
            },
        )
    ).data
    print(f"  Instance created: {instance.display_name} ({instance.id})")
    print("  Waiting for instance to become RUNNING...")
    
    oci.wait_until(compute_client, compute_client.get_instance(instance.id), "lifecycle_state", "RUNNING", max_wait_seconds=600)
    
    instance = compute_client.get_instance(instance.id).data
    vnic = compute_client.list_vnic_attachments(compartment_id=config["compartment_id"], instance_id=instance.id).data[0]
    vnic_info = network_client.get_vnic(vnic.vnic_id).data
    public_ip = vnic_info.public_ip
    
    print()
    print("=" * 60)
    print("DEPLOYMENT COMPLETE!")
    print("=" * 60)
    print()
    print(f"Public IP: {public_ip}")
    print(f"SSH: ssh -i {SSH_KEY_PATH} opc@{public_ip}")
    print()
    print("Services (may take 5-10 minutes to start):")
    print(f"  Backend API:  http://{public_ip}:8000")
    print(f"  Dashboard:    http://{public_ip}:3000")
    print()
    print("To check status:")
    print(f"  ssh -i {SSH_KEY_PATH} opc@{public_ip} 'docker ps'")


if __name__ == "__main__":
    main()

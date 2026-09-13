#!/usr/bin/env python3
"""
OCI Python SDK Deployment Script for AI Survival System
Deploys to Oracle Cloud Free Tier (ARM instances)
"""

import base64
import os
import sys
from pathlib import Path

try:
    import oci
except ImportError:
    print("Error: OCI SDK not installed. Run: pip install oci")
    sys.exit(1)

# Configuration
ORACLE_DIR = Path(__file__).parent
TFVARS_PATH = ORACLE_DIR / "terraform.tfvars"
SSH_KEY_PATH = Path(r"C:\Users\veera\.ssh\id_rsa_oracle")
SSH_PUB_KEY_PATH = Path(r"C:\Users\veera\.ssh\id_rsa_oracle.pub")

# Default values from terraform.tfvars
DEFAULTS = {
    "region": "ap-hyderabad-1",
    "tenancy_ocid": "ocid1.tenancy.oc1..aaaaaaaa77xucbzcg6sufcsp7oct5nwxlqqf66g4q3ejkh2lucopepcg4a6a",
    "user_ocid": "ocid1.user.oc1..aaaaaaaabs7fgezeif7aoxflpjxl34dle2vc6u5qdppfoctuo6x4mqtankva",
    "fingerprint": "3a:62:9f:f6:9b:40:40:3e:ba:a1:64:99:a2:6b:b9:a5",
    "private_key_path": r"C:\Users\veera\.ssh\id_rsa_new",
    "compartment_id": "ocid1.compartment.oc1..aaaaaaaappuxkojmokxox4v2aanula5sec4wtbxpopbd46kmw6535e7notvq",
    "ssh_public_key_path": r"C:\Users\veera\.ssh\id_rsa_new.pub",
}

AD = "NGKk:AP-HYDERABAD-1-AD-1"
VCN_CIDR = "10.0.0.0/16"
PUBLIC_SUBNET_CIDR = "10.0.1.0/24"
PRIVATE_SUBNET_CIDR = "10.0.2.0/24"


def parse_tfvars(path):
    """Parse terraform.tfvars file"""
    config = DEFAULTS.copy()
    if not path.exists():
        print(f"Warning: {path} not found, using defaults")
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
    """Read SSH public key content"""
    with open(path, "r") as f:
        return f.read().strip()


def read_user_data(path):
    """Read and base64 encode user data script"""
    with open(path, "r") as f:
        return base64.b64encode(f.read().encode()).decode()


def get_oracle_linux_image(compute_client, compartment_id, shape="VM.Standard.A1.Flex"):
    """Find latest Oracle Linux image compatible with the given shape"""
    print(f"Finding Oracle Linux image for {shape}...")
    images = compute_client.list_images(
        compartment_id=compartment_id,
        operating_system="Oracle Linux",
        shape=shape,
        lifecycle_state="AVAILABLE",
    ).data
    
    # Filter for Oracle Linux images
    ol_images = [img for img in images if "oracle-linux" in img.display_name.lower()]
    
    if not ol_images:
        # Fallback: get any Oracle Linux image
        ol_images = list(images)
    
    # Sort by time created, get latest
    ol_images.sort(key=lambda x: x.time_created, reverse=True)
    
    if not ol_images:
        raise RuntimeError("No Oracle Linux image found!")
    
    image = ol_images[0]
    print(f"  Using image: {image.display_name} ({image.id})")
    return image.id


def create_vcn(network_client, compartment_id):
    """Create VCN"""
    print("Creating VCN...")
    try:
        result = network_client.create_vcn(
            create_vcn_details=oci.core.models.CreateVcnDetails(
                compartment_id=compartment_id,
                display_name="ai-survival-vcn",
                cidr_block=VCN_CIDR,
            )
        )
        vcn = result.data
        print(f"  VCN created: {vcn.display_name} ({vcn.id})")
        
        # Wait for VCN to become available
        print("  Waiting for VCN to become available...")
        oci.wait_until(
            network_client,
            network_client.get_vcn(vcn.id),
            "lifecycle_state",
            "AVAILABLE",
            max_wait_seconds=120,
        )
        return vcn
    except oci.exceptions.ServiceError as e:
        if e.status == 400 and "LimitExceeded" in str(e):
            print("\n" + "="*60)
            print("ERROR: VCN quota limit reached!")
            print("="*60)
            print("\nOracle Cloud Free Tier has a limit on the number of VCNs.")
            print("You need to free up space before deployment can continue.")
            print("\nOptions:")
            print("1. Delete an existing VCN in this compartment or region")
            print("2. Request a quota increase at: https://cloud.oracle.com/quotas")
            print("3. Use a different compartment (if available)")
            print("\nTo check existing VCNs:")
            print("  - Go to Oracle Cloud Console -> Networking -> Virtual Cloud Networks")
            print("  - Look for VCNs in the 'ap-hyderabad-1' region")
            sys.exit(1)
        else:
            raise


def create_internet_gateway(network_client, compartment_id, vcn_id):
    """Create Internet Gateway"""
    print("Creating Internet Gateway...")
    result = network_client.create_internet_gateway(
        create_internet_gateway_details=oci.core.models.CreateInternetGatewayDetails(
            compartment_id=compartment_id,
            display_name="ai-survival-igw",
            vcn_id=vcn_id,
            is_enabled=True,
        )
    )
    igw = result.data
    print(f"  IGW created: {igw.display_name} ({igw.id})")
    return igw


def create_route_table(network_client, compartment_id, vcn_id, igw_id, is_public=True):
    """Create Route Table"""
    name = "Public Route Table" if is_public else "Private Route Table"
    print(f"Creating {name}...")
    
    route_rules = []
    if is_public:
        route_rules.append(
            oci.core.models.RouteRule(
                destination="0.0.0.0/0",
                destination_type="CIDR_BLOCK",
                network_entity_id=igw_id,
            )
        )
    
    result = network_client.create_route_table(
        create_route_table_details=oci.core.models.CreateRouteTableDetails(
            compartment_id=compartment_id,
            display_name=name,
            vcn_id=vcn_id,
            route_rules=route_rules,
        )
    )
    rt = result.data
    print(f"  Route table created: {rt.display_name} ({rt.id})")
    return rt


def create_security_list(network_client, compartment_id, vcn_id, is_public=True):
    """Create Security List"""
    name = "Public Security List" if is_public else "Private Security List"
    print(f"Creating {name}...")
    
    if is_public:
        ingress_rules = [
            oci.core.models.IngressSecurityRule(
                protocol="6",
                source="0.0.0.0/0",
                is_stateless=False,
                tcp_options=oci.core.models.TcpOptions(
                    destination_port_range=oci.core.models.PortRange(min=22, max=22)
                ),
            ),
            oci.core.models.IngressSecurityRule(
                protocol="6",
                source="0.0.0.0/0",
                is_stateless=False,
                tcp_options=oci.core.models.TcpOptions(
                    destination_port_range=oci.core.models.PortRange(min=80, max=80)
                ),
            ),
            oci.core.models.IngressSecurityRule(
                protocol="6",
                source="0.0.0.0/0",
                is_stateless=False,
                tcp_options=oci.core.models.TcpOptions(
                    destination_port_range=oci.core.models.PortRange(min=443, max=443)
                ),
            ),
            oci.core.models.IngressSecurityRule(
                protocol="6",
                source="0.0.0.0/0",
                is_stateless=False,
                tcp_options=oci.core.models.TcpOptions(
                    destination_port_range=oci.core.models.PortRange(min=3000, max=3000)
                ),
            ),
        ]
    else:
        ingress_rules = [
            oci.core.models.IngressSecurityRule(
                protocol="6",
                source="10.0.1.0/24",
                is_stateless=False,
                tcp_options=oci.core.models.TcpOptions(
                    destination_port_range=oci.core.models.PortRange(min=6379, max=6379)
                ),
            ),
            oci.core.models.IngressSecurityRule(
                protocol="6",
                source="10.0.1.0/24",
                is_stateless=False,
                tcp_options=oci.core.models.TcpOptions(
                    destination_port_range=oci.core.models.PortRange(min=22, max=22)
                ),
            ),
        ]
    
    result = network_client.create_security_list(
        create_security_list_details=oci.core.models.CreateSecurityListDetails(
            compartment_id=compartment_id,
            display_name=name,
            vcn_id=vcn_id,
            egress_security_rules=[
                oci.core.models.EgressSecurityRule(
                    protocol="all",
                    destination="0.0.0.0/0",
                )
            ],
            ingress_security_rules=ingress_rules,
        )
    )
    sl = result.data
    print(f"  Security list created: {sl.display_name} ({sl.id})")
    return sl


def create_subnet(network_client, compartment_id, vcn_id, rt_id, sl_id, cidr, name, is_public=True):
    """Create Subnet"""
    print(f"Creating {name}...")
    
    # Get default DHCP options for the VCN
    vcn = network_client.get_vcn(vcn_id).data
    dhcp_options_id = vcn.default_dhcp_options_id
    
    result = network_client.create_subnet(
        create_subnet_details=oci.core.models.CreateSubnetDetails(
            compartment_id=compartment_id,
            display_name=name,
            vcn_id=vcn_id,
            cidr_block=cidr,
            route_table_id=rt_id,
            security_list_ids=[sl_id],
            dhcp_options_id=dhcp_options_id,
        )
    )
    subnet = result.data
    print(f"  Subnet created: {subnet.display_name} ({subnet.id})")
    return subnet


def create_instance(compute_client, compartment_id, ad, image_id, subnet_id, 
                   ssh_key, user_data, display_name, shape="VM.Standard.E2.1.Micro",
                   ocpus=1, memory=1, assign_public_ip=True, hostname=""):
    """Create Compute Instance"""
    print(f"Creating instance: {display_name}...")
    
    vnic_details = oci.core.models.CreateVnicDetails(
        subnet_id=subnet_id,
        assign_public_ip=assign_public_ip,
    )
    if hostname:
        vnic_details.hostname_label = hostname
    
    result = compute_client.launch_instance(
        launch_instance_details=oci.core.models.LaunchInstanceDetails(
            compartment_id=compartment_id,
            display_name=display_name,
            availability_domain=ad,
            shape=shape,
            shape_config=oci.core.models.LaunchInstanceShapeConfigDetails(
                ocpus=ocpus,
                memory_in_gbs=memory,
            ),
            source_details=oci.core.models.InstanceSourceViaImageDetails(
                source_type="image",
                image_id=image_id,
            ),
            create_vnic_details=vnic_details,
            metadata={
                "ssh_authorized_keys": ssh_key,
                "user_data": user_data,
            },
        )
    )
    instance = result.data
    print(f"  Instance created: {instance.display_name} ({instance.id})")
    print(f"  Waiting for instance to become RUNNING...")
    
    oci.wait_until(
        compute_client,
        compute_client.get_instance(instance.id),
        "lifecycle_state",
        "RUNNING",
        max_wait_seconds=600,
    )
    
    # Get updated instance info for public IP
    instance = compute_client.get_instance(instance.id).data
    print(f"  Instance RUNNING: {instance.display_name}")
    if assign_public_ip:
        vnic = compute_client.list_vnic_attachments(
            compartment_id=compartment_id,
            instance_id=instance.id,
        ).data[0]
        vnic_info = compute_client.get_vnic(vnic.vnic_id).data
        print(f"  Public IP: {vnic_info.public_ip}")
        return instance, vnic_info.public_ip
    else:
        print(f"  Private IP: (check console)")
        return instance, None


def main():
    print("=" * 60)
    print("AI Survival System - Oracle Cloud Deployment")
    print("=" * 60)
    
    # Load config
    config = parse_tfvars(TFVARS_PATH)
    print(f"Region: {config['region']}")
    print(f"Compartment: {config['compartment_id']}")
    print()
    
    # Read SSH keys
    print("Reading SSH keys...")
    ssh_key = read_ssh_key(SSH_PUB_KEY_PATH)
    print(f"  SSH key loaded from {SSH_PUB_KEY_PATH}")
    
    # Read user data scripts
    print("Reading user data scripts...")
    backend_user_data = read_user_data(ORACLE_DIR / "user-data-backend.sh")
    dashboard_user_data = read_user_data(ORACLE_DIR / "user-data-dashboard.sh")
    redis_user_data = read_user_data(ORACLE_DIR / "user-data-redis.sh")
    
    # Initialize OCI clients
    print("Initializing OCI clients...")
    config_file_path = str(Path.home() / ".oci" / "config")
    try:
        oci_config = oci.config.from_file(config_file_path, "ai-survival")
        print(f"  Loaded OCI config from {config_file_path}")
        print(f"  Config keys: {list(oci_config.keys())}")
        print(f"  Fingerprint: {oci_config.get('fingerprint')}")
        print(f"  Key file: {oci_config.get('key_file')}")
    except Exception as e:
        print(f"Error loading OCI config file: {e}")
        print("\nTrying manual config...")
        oci_config = {
            "region": config["region"],
            "tenancy": config["tenancy_ocid"],
            "user": config["user_ocid"],
            "fingerprint": config["fingerprint"],
            "key_file": str(Path(config["private_key_path"])),
        }
    
    # Enable logging for debugging
    import logging
    logging.basicConfig(level=logging.DEBUG)
    
    # Enable HTTP debugging
    import http.client
    http.client.HTTPConnection.debuglevel = 1
    
    try:
        identity_client = oci.identity.IdentityClient(oci_config)
        network_client = oci.core.VirtualNetworkClient(oci_config)
        compute_client = oci.core.ComputeClient(oci_config)
    except Exception as e:
        print(f"Error creating OCI clients: {e}")
        print("\nPossible issues:")
        print("1. Private key file not found or invalid format")
        print("2. Fingerprint doesn't match the public key in Oracle Cloud")
        print("3. User OCID or tenancy OCID is incorrect")
        sys.exit(1)
    
    # Verify tenancy
    try:
        tenancy = identity_client.get_tenancy(config["tenancy_ocid"]).data
        print(f"  Connected to tenancy: {tenancy.name}")
    except Exception as e:
        print(f"Authentication failed: {e}")
        print("\nVerify:")
        print("1. The public key is uploaded to Oracle Cloud for this user")
        print("2. The private key matches the uploaded public key")
        print("3. User has correct permissions")
        sys.exit(1)
    
    # Get Oracle Linux image for E2.1.Micro
    image_id = get_oracle_linux_image(compute_client, config["compartment_id"], shape="VM.Standard.E2.1.Micro")
    
    print()
    print("=" * 60)
    print("STEP 1: Creating Network Infrastructure")
    print("=" * 60)
    
    # Create VCN
    vcn = create_vcn(network_client, config["compartment_id"])
    
    # Create Internet Gateway
    igw = create_internet_gateway(network_client, config["compartment_id"], vcn.id)
    
    # Create Route Tables
    public_rt = create_route_table(network_client, config["compartment_id"], vcn.id, igw.id, is_public=True)
    private_rt = create_route_table(network_client, config["compartment_id"], vcn.id, igw.id, is_public=False)
    
    # Create Security Lists
    public_sl = create_security_list(network_client, config["compartment_id"], vcn.id, is_public=True)
    private_sl = create_security_list(network_client, config["compartment_id"], vcn.id, is_public=False)
    
    print()
    print("=" * 60)
    print("STEP 2: Creating Subnets")
    print("=" * 60)
    
    # Get default DHCP options
    dhcp_options = network_client.get_vcn(vcn.id).data.default_dhcp_options_id
    
    public_subnet = create_subnet(
        network_client, config["compartment_id"], vcn.id,
        public_rt.id, public_sl.id,
        PUBLIC_SUBNET_CIDR, "Public Subnet", is_public=True
    )
    
    private_subnet = create_subnet(
        network_client, config["compartment_id"], vcn.id,
        private_rt.id, private_sl.id,
        PRIVATE_SUBNET_CIDR, "Private Subnet", is_public=False
    )
    
    print()
    print("=" * 60)
    print("STEP 3: Creating Instances")
    print("=" * 60)
    
    # Create Redis instance (private subnet) - E2.1.Micro
    redis_instance, redis_private_ip = create_instance(
        compute_client, config["compartment_id"], AD, image_id,
        private_subnet.id, ssh_key, redis_user_data,
        "ai-survival-redis", shape="VM.Standard.E2.1.Micro", ocpus=1, memory=1, assign_public_ip=False, hostname="redis"
    )
    
    # Create Backend instance (public subnet) - E2.1.Micro
    backend_instance, backend_ip = create_instance(
        compute_client, config["compartment_id"], AD, image_id,
        public_subnet.id, ssh_key, backend_user_data,
        "ai-survival-backend", shape="VM.Standard.E2.1.Micro", ocpus=1, memory=1, assign_public_ip=True, hostname="backend"
    )
    
    # Create Dashboard instance (public subnet) - E2.1.Micro
    dashboard_instance, dashboard_ip = create_instance(
        compute_client, config["compartment_id"], AD, image_id,
        public_subnet.id, ssh_key, dashboard_user_data,
        "ai-survival-dashboard", shape="VM.Standard.E2.1.Micro", ocpus=1, memory=1, assign_public_ip=True, hostname="dashboard"
    )
    
    print()
    print("=" * 60)
    print("DEPLOYMENT COMPLETE!")
    print("=" * 60)
    print()
    print("Connection Information:")
    print(f"  Backend Public IP:  {backend_ip}")
    print(f"  Dashboard Public IP: {dashboard_ip}")
    print(f"  Redis Private IP:    {redis_private_ip}")
    print()
    print("SSH Commands:")
    print(f"  Backend:  ssh -i {SSH_KEY_PATH} opc@{backend_ip}")
    print(f"  Dashboard: ssh -i {SSH_KEY_PATH} opc@{dashboard_ip}")
    print()
    print("Services:")
    print(f"  Backend API:  http://{backend_ip}:8000")
    print(f"  Dashboard:    http://{dashboard_ip}:3000")
    print()
    print("Note: It may take 5-10 minutes for Docker containers to build and start.")
    print("Check status with: ssh -i ... opc@<ip> 'sudo systemctl status ai-survival-backend'")


if __name__ == "__main__":
    main()

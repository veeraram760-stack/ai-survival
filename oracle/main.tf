resource "oci_core_instance" "backend" {
  availability_domain = local.availability_domain
  compartment_id      = var.compartment_id
  display_name        = "ai-survival-backend"
  shape               = "VM.Standard.A1.Flex"
  shape_config {
    ocpus         = 4
    memory_in_gbs = 24
  }

  source_details {
    source_type = "image"
    source_id   = local.oracle_linux_image
  }

  create_vnic_details {
    subnet_id        = oci_core_subnet.public.id
    assign_public_ip = true
    hostname_label   = "backend"
  }

  metadata = {
    ssh_authorized_keys = file(var.ssh_public_key_path)
    user_data = base64encode(file("${path.module}/user-data-backend.sh"))
  }

  timeouts {
    create = "15m"
  }
}

resource "oci_core_instance" "dashboard" {
  availability_domain = local.availability_domain
  compartment_id      = var.compartment_id
  display_name        = "ai-survival-dashboard"
  shape               = "VM.Standard.A1.Flex"
  shape_config {
    ocpus         = 4
    memory_in_gbs = 24
  }

  source_details {
    source_type = "image"
    source_id   = local.oracle_linux_image
  }

  create_vnic_details {
    subnet_id        = oci_core_subnet.public.id
    assign_public_ip = true
    hostname_label   = "dashboard"
  }

  metadata = {
    ssh_authorized_keys = file(var.ssh_public_key_path)
    user_data = base64encode(file("${path.module}/user-data-dashboard.sh"))
  }

  timeouts {
    create = "15m"
  }
}

resource "oci_core_instance" "redis" {
  availability_domain = local.availability_domain
  compartment_id      = var.compartment_id
  display_name        = "ai-survival-redis"
  shape               = "VM.Standard.A1.Flex"
  shape_config {
    ocpus         = 4
    memory_in_gbs = 24
  }

  source_details {
    source_type = "image"
    source_id   = local.oracle_linux_image
  }

  create_vnic_details {
    subnet_id        = oci_core_subnet.private.id
    assign_public_ip = false
    hostname_label   = "redis"
  }

  metadata = {
    ssh_authorized_keys = file(var.ssh_public_key_path)
    user_data = base64encode(file("${path.module}/user-data-redis.sh"))
  }

  timeouts {
    create = "15m"
  }
}

resource "oci_core_subnet" "public" {
  compartment_id      = var.compartment_id
  vcn_id              = oci_core_vcn.ai_survival_vcn.id
  display_name        = "Public Subnet"
  cidr_block          = "10.0.1.0/24"
  route_table_id      = oci_core_route_table.public.id
  security_list_ids   = [oci_core_security_list.public.id]
  dhcp_options_id     = oci_core_vcn.ai_survival_vcn.default_dhcp_options_id
}

resource "oci_core_subnet" "private" {
  compartment_id      = var.compartment_id
  vcn_id              = oci_core_vcn.ai_survival_vcn.id
  display_name        = "Private Subnet"
  cidr_block          = "10.0.2.0/24"
  route_table_id      = oci_core_route_table.private.id
  security_list_ids   = [oci_core_security_list.private.id]
  dhcp_options_id     = oci_core_vcn.ai_survival_vcn.default_dhcp_options_id
}

resource "oci_core_vcn" "ai_survival_vcn" {
  compartment_id = var.compartment_id
  display_name   = "ai-survival-vcn"
  cidr_block     = "10.0.0.0/16"
}

resource "oci_core_internet_gateway" "igw" {
  compartment_id = var.compartment_id
  display_name   = "ai-survival-igw"
  vcn_id         = oci_core_vcn.ai_survival_vcn.id
}

resource "oci_core_route_table" "public" {
  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.ai_survival_vcn.id
  display_name   = "Public Route Table"

  route_rules {
    destination       = "0.0.0.0/0"
    destination_type  = "CIDR_BLOCK"
    network_entity_id = oci_core_internet_gateway.igw.id
  }
}

resource "oci_core_route_table" "private" {
  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.ai_survival_vcn.id
  display_name   = "Private Route Table"
}

resource "oci_core_security_list" "public" {
  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.ai_survival_vcn.id
  display_name   = "Public Security List"

  egress_security_rules {
    protocol    = "all"
    destination = "0.0.0.0/0"
  }

  ingress_security_rules {
    protocol = "6"
    source   = "0.0.0.0/0"
    stateless = false
    tcp_options {
      min = 22
      max = 22
    }
  }

  ingress_security_rules {
    protocol = "6"
    source   = "0.0.0.0/0"
    stateless = false
    tcp_options {
      min = 80
      max = 80
    }
  }

  ingress_security_rules {
    protocol = "6"
    source   = "0.0.0.0/0"
    stateless = false
    tcp_options {
      min = 443
      max = 443
    }
  }

  ingress_security_rules {
    protocol = "6"
    source   = "0.0.0.0/0"
    stateless = false
    tcp_options {
      min = 3000
      max = 3000
    }
  }
}

resource "oci_core_security_list" "private" {
  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.ai_survival_vcn.id
  display_name   = "Private Security List"

  egress_security_rules {
    protocol    = "all"
    destination = "0.0.0.0/0"
  }

  ingress_security_rules {
    protocol = "6"
    source   = "10.0.1.0/24"
    stateless = false
    tcp_options {
      min = 6379
      max = 6379
    }
  }

  ingress_security_rules {
    protocol = "6"
    source   = "10.0.1.0/24"
    stateless = false
    tcp_options {
      min = 22
      max = 22
    }
  }
}

resource "oci_core_public_ip" "backend_ip" {
  compartment_id = var.compartment_id
  lifetime       = "RESERVED"
}

resource "oci_core_public_ip" "dashboard_ip" {
  compartment_id = var.compartment_id
  lifetime       = "RESERVED"
}

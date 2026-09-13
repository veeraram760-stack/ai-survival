terraform {
  required_providers {
    oci = {
      source  = "oracle/oci"
      version = "~> 6.0"
    }
  }
  required_version = ">= 1.5"
}

provider "oci" {
  region           = var.region
  tenancy_ocid     = var.tenancy_ocid
  user_ocid        = var.user_ocid
  fingerprint      = var.fingerprint
  private_key_path = var.private_key_path
}

locals {
  availability_domain = "Uocm:AP-HYDERABAD-AD-1"
  oracle_linux_image  = "ocid1.image.oc1..aaaaaaaabz5etuqnyrn7a4cbzmgdgf7xmjqkmvmpf3q5n2v3s5b64m2cwjoa"
}

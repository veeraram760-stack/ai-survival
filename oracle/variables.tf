variable "region" {
  type        = string
  default     = "us-ashburn-1"
  description = "Oracle Cloud region"
}

variable "tenancy_ocid" {
  type        = string
  description = "Oracle Cloud tenancy OCID"
}

variable "user_ocid" {
  type        = string
  description = "Oracle Cloud user OCID"
}

variable "fingerprint" {
  type        = string
  description = "API key fingerprint"
}

variable "private_key_path" {
  type        = string
  default     = "~/.oci/oci_api_key.pem"
  description = "Path to private key"
}

variable "compartment_id" {
  type        = string
  description = "Root compartment OCID"
}

variable "ssh_public_key_path" {
  type        = string
  default     = "~/.ssh/id_rsa.pub"
  description = "Path to SSH public key"
}

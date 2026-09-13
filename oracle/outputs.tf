output "backend_public_ip" {
  value = oci_core_instance.backend.public_ip
}

output "dashboard_public_ip" {
  value = oci_core_instance.dashboard.public_ip
}

output "redis_private_ip" {
  value = oci_core_instance.redis.private_ip
}

output "backend_ssh" {
  value = "ssh -i ~/.ssh/id_rsa opc@${oci_core_instance.backend.public_ip}"
}

output "dashboard_ssh" {
  value = "ssh -i ~/.ssh/id_rsa opc@${oci_core_instance.dashboard.public_ip}"
}

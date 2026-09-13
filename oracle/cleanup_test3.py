import oci

config = {
    "user": "ocid1.user.oc1..aaaaaaaabs7fgezeif7aoxflpjxl34dle2vc6u5qdppfoctuo6x4mqtankva",
    "fingerprint": "67:96:db:1f:f0:94:b7:ff:f8:1a:91:ed:de:5b:f1:cf",
    "tenancy": "ocid1.tenancy.oc1..aaaaaaaa77xucbzcg6sufcsp7oct5nwxlqqf66g4q3ejkh2lucopepcg4a6a",
    "region": "ap-hyderabad-1",
    "key_file": "C:/Users/veera/.ssh/id_rsa_oracle",
}

network_client = oci.core.VirtualNetworkClient(config)

# Delete test security list
sl_id = "ocid1.securitylist.oc1.ap-hyderabad-1.aaaaaaaakvt2siyj77j3jogvn65i6bpixyxzilqm7vym23gr24jixgddxqpq"
try:
    network_client.delete_security_list(sl_id)
    print("Deleted security list")
except Exception as e:
    print(f"Failed to delete security list: {e}")

# Delete test VCN
vcn_id = "ocid1.vcn.oc1.ap-hyderabad-1.amaaaaaakroosiqaak6nsg6zdw3fgkm33tnuvmv37bpl2svjg44xre7ckmlq"
try:
    network_client.delete_vcn(vcn_id)
    print("Deleted VCN")
except Exception as e:
    print(f"Failed to delete VCN: {e}")

print("Done!")

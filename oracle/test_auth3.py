import oci
import logging

logging.basicConfig(level=logging.DEBUG)

# Try with traditional OpenSSL format
config = {
    "user": "ocid1.user.oc1..aaaaaaaabs7fgezeif7aoxflpjxl34dle2vc6u5qdppfoctuo6x4mqtankva",
    "fingerprint": "ca:68:ae:74:d7:2f:a2:4b:50:b3:36:e5:d5:ae:89:85",
    "tenancy": "ocid1.tenancy.oc1..aaaaaaaa77xucbzcg6sufcsp7oct5nwxlqqf66g4q3ejkh2lucopepcg4a6a",
    "region": "ap-hyderabad-1",
    "key_file": "C:/Users/veera/.ssh/id_rsa_new_traditional.pem",
}

client = oci.identity.IdentityClient(config)

try:
    result = client.get_tenancy(config['tenancy'])
    print("Success:", result.data.name)
except Exception as e:
    print("Error:", e)

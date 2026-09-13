import oci
import logging

logging.basicConfig(level=logging.DEBUG)

# Test with config file
config = oci.config.from_file('C:\\Users\\veera\\.oci\\config', 'ai-survival')
print("Config:", config)
print("Key file exists:", __import__('os').path.exists(config['key_file']))

# Try to create client and make a simple call
client = oci.identity.IdentityClient(config)

try:
    # This will trigger the actual signing
    result = client.get_tenancy(config['tenancy'])
    print("Success:", result.data.name)
except Exception as e:
    print("Error:", e)
    
    # Try to get more details about what the SDK is doing
    import http.client
    http.client.HTTPConnection.debuglevel = 1

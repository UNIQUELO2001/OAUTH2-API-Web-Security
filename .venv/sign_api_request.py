import requests
import json
import base64
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.serialization import load_pem_private_key

# ✅ Load Private Key
with open("private_key.pem", "rb") as key_file:
    private_key = load_pem_private_key(key_file.read(), password=None)


def sign_request(data):
    """
    Signs API request payload with RSA private key.
    """
    data_bytes = json.dumps(data, sort_keys=True).encode()

    signature = private_key.sign(
        data_bytes,
        padding.PKCS1v15(),
        hashes.SHA256()
    )

    return base64.b64encode(signature).decode()


def make_signed_api_request(access_token, api_url, payload):
    """
    Makes an API request with OAuth 2.0 and digital signature.
    """
    if not access_token:
        raise ValueError("❌ ERROR: Access Token is missing! Please log in and get a valid token.")

    signature = sign_request(payload)

    headers = {
        "Authorization": f"Bearer {access_token}",  # ✅ OAuth Token
        "Content-Type": "application/json",
        "X-Signature": signature  # ✅ Custom header for digital signature
    }

    print("\n🔑 Generated X-Signature:", signature)  # ✅ Print the signature
    print("\n📡 Sending API Request with Headers:", headers)

    response = requests.post(api_url, headers=headers, json=payload)

    return response.json(), signature


# ✅ Example Usage
if __name__ == "__main__":
    '''Add your current access token here'''
    access_token = "ya29.a0AeXRPp5aTdkwNi2h7m17VDxzg7I0w3kzvOr38-CeTnHxzkKqnvtSL_3ltzOPnxz9BUqeN0EBf0gXbU5HXMIeCpDtMGXmfyAlr71Jru13XbcBJ8D32r97trfF86Slds7_nFHblqFWNcDVPpcTTB8JanHgvUWZShfWsvE_nRSpaCgYKAd8SARMSFQHGX2Mi2bGKWIARCzbg_rqawD3ywg0175"
    api_url = "https://www.googleapis.com/drive/v3/files"
    payload = {"query": "mimeType='application/pdf'"}

    response, generated_signature = make_signed_api_request(access_token, api_url, payload)

    print("\n🔍 API Response:", response)
    print("\n🔑 Use this X-Signature for verification:", generated_signature)

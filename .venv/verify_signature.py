import json
import base64
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.serialization import load_pem_public_key

# ✅ Load Public Key
with open("public_key.pem", "rb") as key_file:
    public_key = load_pem_public_key(key_file.read())

def verify_signature(data, signature):
    """
    Verifies the API request signature using the public key.
    """
    data_bytes = json.dumps(data, sort_keys=True).encode()
    signature_bytes = base64.b64decode(signature)

    try:
        public_key.verify(
            signature_bytes,
            data_bytes,
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        print("\n✅ Signature verification successful!")
        return True
    except Exception as e:
        print("\n❌ Signature verification failed!", str(e))
        return False

# ✅ Example Usage
if __name__ == "__main__":
    test_data = {"query": "mimeType='application/pdf'"}
    test_signature = "cwJfga6wttswArCSkxHy7g0BR+skgXirCN/4PGBupGbnzhbOwOw++nqJmQy9+3RVR+7WbaChJYy85RpE8/kL5P9YgufkCU0YRBKh8wTAfw1Nsb0Cyq3HAWDVB5x+fYsptpN7kyKlUE6ONtrgiQZXw6ZbNzPa079ruw7Rb8ynF9l6OPxRTHtBhc9qWvH/t2hjcUCH3DWZ0dkDTs4uHzOF+a3Uq6v/HL8XGRt6S+8cjaLRaSiGHXMfIC9wptMba4peXgO+K3OU0K9yn02z4noGDT/JEs3MaDUs+gvMcx587DyoREEZGlxV6a1/LxAasgLtFEvMvUxSG1LajLHRevxVAA=="
    verify_signature(test_data, test_signature)

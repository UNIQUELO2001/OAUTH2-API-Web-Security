import requests
import json
import base64
import time
import pandas as pd
import matplotlib.pyplot as plt
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.serialization import load_pem_private_key

# OAuth 2.0 Credentials
GOOGLE_CLIENT_ID = "450584471734-cl1idqj9d8fc9qaoe706l776j8ebgtps.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET = "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"
REDIRECT_URI = "http://localhost:5000/callback"
TOKEN_URL = "https://oauth2.googleapis.com/token"

# ✅ Load Private Key for Signing API Requests
with open("private_key.pem", "rb") as key_file:
    private_key = load_pem_private_key(key_file.read(), password=None)

# ✅ Track API Performance
log_data = []


def get_access_token(auth_code):
    """
    Exchanges an authorization code for an access token and logs response time.
    """
    start_time = time.time()

    payload = {
        "code": auth_code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code"
    }

    response = requests.post(TOKEN_URL, data=payload)
    token_data = response.json()

    response_time = time.time() - start_time
    log_data.append({"API": "Token Request", "Time (s)": response_time,
                     "Status": "Success" if "access_token" in token_data else "Failed"})

    if "access_token" not in token_data:
        raise Exception(f"Failed to get access token: {token_data}")

    return token_data["access_token"]


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
    Measures response time and logs success/failure.
    """
    signature = sign_request(payload)

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Signature": signature  # ✅ Custom header for digital signature
    }

    start_time = time.time()
    response = requests.post(api_url, headers=headers, json=payload)
    response_time = time.time() - start_time

    log_data.append(
        {"API": api_url, "Time (s)": response_time, "Status": "Success" if response.status_code == 200 else "Failed"})

    return response.json()


def analyze_efficiency():
    """
    Analyzes OAuth 2.0 efficiency using response times and success rates.
    """
    df = pd.DataFrame(log_data)

    # ✅ Print Efficiency Log
    print("\n🔍 OAuth 2.0 Efficiency Log")
    print(df)

    # ✅ Plot Response Time Analysis
    plt.figure(figsize=(8, 5))
    plt.bar(df["API"], df["Time (s)"], color=["green" if status == "Success" else "red" for status in df["Status"]])
    plt.xlabel("API Calls")
    plt.ylabel("Time Taken (s)")
    plt.title("OAuth 2.0 API Response Time")
    plt.xticks(rotation=45)
    plt.show()


# ✅ Example Usage
if __name__ == "__main__":
    auth_code = input("Enter your Google OAuth Code: ").strip()

    try:
        access_token = get_access_token(auth_code)

        # ✅ Test API Calls
        api_url = "https://www.googleapis.com/drive/v3/files"
        payload = {"query": "mimeType='application/pdf'"}

        response = make_signed_api_request(access_token, api_url, payload)

        # ✅ Analyze OAuth Efficiency
        analyze_efficiency()

    except Exception as e:
        print("❌ Error:", e)

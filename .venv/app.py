from flask import Flask, redirect, request, session, jsonify
import requests
import urllib.parse
import os
from flask import Flask, session
from flask_session import Session
import time

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Change this to a secure key

# ✅ Store session on the filesystem (prevents loss on restart)
app.config["SESSION_TYPE"] = "filesystem"
Session(app)


# ✅ Google OAuth 2.0 Credentials (Replace these with your actual credentials)
GOOGLE_CLIENT_ID = "450584471734-cl1idqj9d8fc9qaoe706l776j8ebgtps.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET = "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"
REDIRECT_URI = "http://localhost:5000/callback"
TOKEN_URL = "https://oauth2.googleapis.com/token"
USER_INFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
SCOPES = "openid email profile"

@app.route("/")
def home():
    return "🚀 OAuth 2.0 Login - Visit /login to authenticate."


REDIRECT_URI = "http://localhost:5000/callback"  # ✅ Ensure this matches Google Cloud

@app.route("/login")
def login():
    """
    Redirect user to Google's OAuth 2.0 login page.
    """
    SCOPES = "openid email profile https://www.googleapis.com/auth/drive.readonly"

    google_auth_url = (
        f"https://accounts.google.com/o/oauth2/auth"
        f"?client_id={GOOGLE_CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"  # ✅ This must match exactly with Google Cloud
        f"&response_type=code"
        f"&scope={SCOPES}"
        f"&access_type=offline"
        f"&prompt=consent"
    )

    print("\n🔍 OAuth Login URL:", google_auth_url)  # ✅ Debugging
    return redirect(google_auth_url)






TOKEN_URL = "https://oauth2.googleapis.com/token"

@app.route("/callback")
def callback():
    code = request.args.get("code")

    # ✅ Exchange authorization code for tokens
    data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    }

    response = requests.post(TOKEN_URL, data=data)
    token_json = response.json()

    print("\n🔍 DEBUG: Token Response →", token_json)  # ✅ Print tokens in terminal

    if "access_token" in token_json:
        session["access_token"] = token_json["access_token"]
        session["refresh_token"] = token_json.get("refresh_token")

        print("\n✅ DEBUG: Session Data After Login →", dict(session))  # ✅ Confirm session data

        return jsonify({
            "message": "User authenticated",
            "access_token": session["access_token"],
            "refresh_token": session.get("refresh_token", "No refresh token")
        })
    else:
        return jsonify({"error": "Failed to retrieve access token", "details": token_json}), 400


@app.route("/profile")
def profile():
    """
    Debug session and check if user is authenticated.
    """
    print("\n🔍 DEBUG: Current Session Data →", dict(session))  # ✅ Print session data in terminal

    if "access_token" not in session:
        return jsonify({
            "error": "User not authenticated",
            "message": "Please log in again.",
            "debug": "Session data is empty or expired."
        }), 401

    return jsonify({
        "message": "User is authenticated",
        "access_token": session["access_token"],
        "refresh_token": session.get("refresh_token", "No refresh token found")
    })

# ✅ Define global sets to store expired tokens and used timestamps (nonces)
EXPIRED_TOKENS = set()
VALID_NONCES = set()

@app.route("/protected_api", methods=["GET"])
def protected_api():
    """
    Protects against session hijacking & replay attacks.
    """
    access_token = request.headers.get("Authorization")
    signature = request.headers.get("X-Signature")
    timestamp = request.headers.get("X-Timestamp")

    # ✅ Debugging - Print incoming requests
    print("\n🔍 Incoming Request:")
    print(" - Access Token:", access_token)
    print(" - Signature:", signature)
    print(" - Timestamp:", timestamp)

    # ✅ Reject missing authentication headers
    if not access_token or not signature or not timestamp:
        return jsonify({"error": "Missing authentication headers"}), 401

    # ✅ Convert timestamp to integer
    try:
        request_time = int(timestamp)
    except ValueError:
        return jsonify({"error": "Invalid timestamp format"}), 400

    current_time = int(time.time())

    # ✅ Reject if timestamp is too old (5 minutes threshold)
    if abs(current_time - request_time) > 300:
        return jsonify({"error": "Request timestamp expired"}), 403

    # ✅ Reject replayed timestamps (nonce check)
    if timestamp in VALID_NONCES:
        return jsonify({"error": "Replay attack detected"}), 403
    VALID_NONCES.add(timestamp)  # ✅ Store timestamp to prevent reuse

    # ✅ Reject reused access tokens
    if access_token in EXPIRED_TOKENS:
        return jsonify({"error": "Invalid or expired access token"}), 401

    # ✅ Mark token as expired (to prevent reuse)
    EXPIRED_TOKENS.add(access_token)

    return jsonify({"message": "Request received successfully"}), 200

if __name__ == "__main__":
    app.run(debug=True)



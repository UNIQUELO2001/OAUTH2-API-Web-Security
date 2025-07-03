import time
import hmac
import hashlib
import requests
import json
import random

# ─────────────────────────────────────────────────────
# CONFIGURATION
SECRET_KEY = b"super_secret_key"
HIJACKED_ACCESS_TOKEN = "ya29.a0AS3H6NzHhiPpbB5Z5SbUzR1DjDJgzMZENHv_0TDUiXotSGQp2DlwPFxjMEiVapw-Zr08tCxV9Fs3cVLSAVev2ydzaNSBb7doS8MGi6G8R-EkJ8i10ilZLxoqDqryocGy5RPIZIy7DwRi1p9DqWAdCnKjO6Otx93gwzi32xSqaCgYKAaYSARcSFQHGX2MinV5wQxj2ewoafRn4CxlIQQ0175"  # Replace with actual access token
API_URL = "http://localhost:5000/protected_api"

TOTAL_DURATION_SECONDS = 4 * 60 * 60
INTERVAL_SECONDS = 2
TOTAL_ITERATIONS = TOTAL_DURATION_SECONDS // INTERVAL_SECONDS
# ─────────────────────────────────────────────────────

def generate_signature(token, timestamp):
    message = f"{token}:{timestamp}"
    start = time.perf_counter()
    signature = hmac.new(SECRET_KEY, message.encode(), hashlib.sha256).hexdigest()
    end = time.perf_counter()
    signing_time_ms = round((end - start) * 1000, 4)
    return signature, signing_time_ms

def generate_random_attacker_id():
    return f"attacker_{random.randint(1000, 9999)}"

def send_attack(attempt):
    # Alternating logic
    if attempt % 2 == 1:
        attack_type = "Replay Attack"
        timestamp = str(int(time.time()) - 600)  # 10 mins old
    else:
        attack_type = "Session Hijacking"
        timestamp = str(int(time.time()))  # current time

    attacker_id = generate_random_attacker_id()
    signature, signing_time_ms = generate_signature(HIJACKED_ACCESS_TOKEN, timestamp)

    headers = {
        "Authorization": f"Bearer {HIJACKED_ACCESS_TOKEN}",
        "X-Timestamp": timestamp,
        "X-Signature": signature,
        "Content-Type": "application/json"
    }

    start_req = time.perf_counter()
    response = requests.get(API_URL, headers=headers)
    end_req = time.perf_counter()
    response_time_sec = round(end_req - start_req, 4)

    log = {
        "attempt": attempt,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "attacker_id": attacker_id,
        "attack_type": attack_type,
        "access_token_preview": HIJACKED_ACCESS_TOKEN[:40] + "...",
        "signature": signature,
        "signature_size_bytes": len(signature.encode()),
        "signing_time_ms": signing_time_ms,
        "request_timestamp": timestamp,
        "response_time_sec": response_time_sec,
        "status_code": response.status_code,
        "response_text": response.text.strip()
    }

    print(f"🚨 Attempt #{attempt} | {attacker_id} | {attack_type} | Status: {response.status_code} | Signing: {signing_time_ms} ms | Resp: {response_time_sec}s")

    with open("oauth2_attack_log.json", "a") as f:
        f.write(json.dumps(log) + "\n")

if __name__ == "__main__":
    print(f"🚀 Starting OAuth 2.0 Alternating Attack Test ({TOTAL_ITERATIONS} attempts)...\n")
    for i in range(1, TOTAL_ITERATIONS + 1):
        send_attack(i)
        time.sleep(INTERVAL_SECONDS)

    print("\n✅ Test complete! Logs saved to 'oauth2_attack_log.json'")

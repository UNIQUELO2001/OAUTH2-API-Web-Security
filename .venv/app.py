from flask import Flask, redirect, request, session, jsonify, render_template_string
from flask_session import Session
import requests
import random
import time
import webbrowser

app = Flask(__name__)
app.secret_key = "e3d5c9c59f2179a63fcfe7d2b8e9aab445c49a43a39bc913d377b9b34c5d80d0"

# Store session on the filesystem
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# === Google OAuth 2.0 Credentials ===
GOOGLE_CLIENT_ID = "450584471734-cl1idqj9d8fc9qaoe706l776j8ebgtps.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET = "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"
REDIRECT_URI = "http://localhost:5000/callback"
TOKEN_URL = "https://oauth2.googleapis.com/token"
USER_INFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
SCOPES = "openid email profile https://www.googleapis.com/auth/drive.readonly"

# Simulate a known token the attacker has (for token injection tests)
VALID_ACCESS_TOKEN = "abc123-token"

# ------------------------
# Slick Dashboard UI (inline)
# ------------------------
DASHBOARD_HTML = r"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>OAuth 2.0 Test Console</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-950 text-slate-100">
  <div class="max-w-5xl mx-auto p-6">
    <header class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-bold">OAuth 2.0 Test Console</h1>
      <div class="flex gap-2">
        <a href="/login"
           class="px-4 py-2 rounded-2xl bg-indigo-600 hover:bg-indigo-500 transition">
          Login with Google
        </a>
      </div>
    </header>

    <section class="grid md:grid-cols-3 gap-4 mb-6">
      <div class="rounded-2xl bg-slate-900 border border-slate-800 p-4">
        <h2 class="font-semibold mb-2">Session</h2>
        <div id="sessionStatus" class="text-sm text-slate-300">Not checked yet.</div>
        <button id="btnCheckProfile"
                class="mt-3 w-full px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 transition">
          Check Profile / Session
        </button>
      </div>

      <div class="rounded-2xl bg-slate-900 border border-slate-800 p-4">
        <h2 class="font-semibold mb-2">Known Token (for Injection)</h2>
        <input id="knownToken" type="text" value="abc123-token"
               class="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-600" />
        <p class="text-xs text-slate-400 mt-2">
          Mirrors <code>VALID_ACCESS_TOKEN</code> on the server.
        </p>
      </div>

      <div class="rounded-2xl bg-slate-900 border border-slate-800 p-4">
        <h2 class="font-semibold mb-2">Server Behavior</h2>
        <p class="text-sm text-slate-300">
          For a valid token, the server randomly returns <span class="text-emerald-400">200</span> or <span class="text-rose-400">401</span> (no signature checks).
        </p>
        <p class="text-xs text-slate-400 mt-2">
          Configure in <code>/protected_api</code>.
        </p>
      </div>
    </section>

    <section class="rounded-2xl bg-slate-900 border border-slate-800 p-4 mb-6">
      <div class="flex items-center justify-between mb-3">
        <h2 class="font-semibold">Protected API Tester</h2>
        <div class="text-xs text-slate-400">GET /protected_api</div>
      </div>

      <div class="grid md:grid-cols-4 gap-3 mb-3">
        <div class="md:col-span-3">
          <label class="block text-sm mb-1">Authorization Header (token only)</label>
          <input id="attackToken" type="text" placeholder="e.g., abc123-token"
                 class="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-600" />
        </div>
        <div class="md:col-span-1 flex items-end">
          <button id="btnCallProtected"
                  class="w-full px-4 py-2 rounded-2xl bg-indigo-600 hover:bg-indigo-500 transition">
            Call Protected API
          </button>
        </div>
      </div>

      <div class="grid md:grid-cols-3 gap-3">
        <div class="rounded-xl bg-slate-800/60 p-3">
          <div class="text-xs text-slate-400 mb-1">Status</div>
          <div id="protectedStatus" class="text-lg">—</div>
        </div>
        <div class="rounded-xl bg-slate-800/60 p-3">
          <div class="text-xs text-slate-400 mb-1">Response Time (ms)</div>
          <div id="protectedLatency" class="text-lg">—</div>
        </div>
        <div class="rounded-xl bg-slate-800/60 p-3">
          <div class="text-xs text-slate-400 mb-1">Result</div>
          <div id="protectedResult" class="text-lg">—</div>
        </div>
      </div>

      <div class="mt-4">
        <div class="text-xs text-slate-400 mb-1">Response Body</div>
        <pre id="protectedBody" class="text-sm p-3 rounded-xl bg-slate-950 border border-slate-800 overflow-auto max-h-64">—</pre>
      </div>
    </section>

    <section class="rounded-2xl bg-slate-900 border border-slate-800 p-4">
      <div class="flex items-center justify-between mb-3">
        <h2 class="font-semibold">Request Log</h2>
        <button id="btnClearLog"
                class="px-3 py-2 rounded-2xl bg-slate-800 hover:bg-slate-700 transition">
          Clear Log
        </button>
      </div>
      <div class="overflow-auto">
        <table class="w-full text-left text-sm">
          <thead class="text-slate-300 border-b border-slate-800">
            <tr>
              <th class="py-2 pr-4">Time</th>
              <th class="py-2 pr-4">Endpoint</th>
              <th class="py-2 pr-4">Status</th>
              <th class="py-2 pr-4">Latency (ms)</th>
              <th class="py-2 pr-4">Notes</th>
            </tr>
          </thead>
          <tbody id="logTable"></tbody>
        </table>
      </div>
    </section>
  </div>

  <script>
    const $ = (id) => document.getElementById(id);

    // Prefill from known token
    const syncKnownToAttack = () => {
      $("attackToken").value = $("knownToken").value.trim();
    };
    syncKnownToAttack();
    $("knownToken").addEventListener("input", syncKnownToAttack);

    function logRow({ time, endpoint, status, latency, notes }) {
      const tr = document.createElement("tr");
      tr.className = "border-b border-slate-800/70";
      tr.innerHTML = `
        <td class="py-2 pr-4 whitespace-nowrap">${time}</td>
        <td class="py-2 pr-4">${endpoint}</td>
        <td class="py-2 pr-4">${status ?? "—"}</td>
        <td class="py-2 pr-4">${latency ?? "—"}</td>
        <td class="py-2 pr-4 text-slate-300">${notes || ""}</td>
      `;
      $("logTable").prepend(tr);
    }

    $("btnCheckProfile").addEventListener("click", async () => {
      const t0 = performance.now();
      try {
        const res = await fetch("/profile");
        const t1 = performance.now();
        const latency = (t1 - t0).toFixed(2);
        const data = await res.json();
        $("sessionStatus").textContent = res.ok
          ? "Authenticated. Access token present in session."
          : (data?.message || data?.error || "Not authenticated.");

        logRow({
          time: new Date().toLocaleString(),
          endpoint: "/profile",
          status: res.status,
          latency,
          notes: res.ok ? "Session OK" : "No session"
        });
      } catch (e) {
        $("sessionStatus").textContent = "Error checking session.";
        logRow({
          time: new Date().toLocaleString(),
          endpoint: "/profile",
          status: "ERR",
          latency: "—",
          notes: "Failed to fetch profile."
        });
      }
    });

    $("btnCallProtected").addEventListener("click", async () => {
      const token = $("attackToken").value.trim();
      if (!token) {
        alert("Enter a token first.");
        return;
      }
      const t0 = performance.now();
      try {
        const res = await fetch("/protected_api", {
          method: "GET",
          headers: { "Authorization": token }
        });
        const t1 = performance.now();
        const latency = (t1 - t0).toFixed(2);
        const bodyText = await res.text();

        $("protectedStatus").textContent = res.status;
        $("protectedLatency").textContent = latency;
        $("protectedResult").textContent = res.ok ? "SUCCESS" : "FAIL";
        $("protectedBody").textContent = bodyText;

        logRow({
          time: new Date().toLocaleString(),
          endpoint: "/protected_api",
          status: res.status,
          latency,
          notes: res.ok ? "Random success" : "Random failure / unauthorized"
        });
      } catch (e) {
        $("protectedStatus").textContent = "ERR";
        $("protectedLatency").textContent = "—";
        $("protectedResult").textContent = "FAIL";
        $("protectedBody").textContent = "Network error.";
        logRow({
          time: new Date().toLocaleString(),
          endpoint: "/protected_api",
          status: "ERR",
          latency: "—",
          notes: "Network error"
        });
      }
    });

    $("btnClearLog").addEventListener("click", () => {
      $("logTable").innerHTML = "";
    });
  </script>
</body>
</html>
"""

# ------------------------
# Routes
# ------------------------

@app.route("/")
def home():
    return "🚀 OAuth 2.0 Login - Visit /dashboard for the UI or /login to authenticate."

@app.route("/dashboard")
def dashboard():
    return render_template_string(DASHBOARD_HTML)

@app.route("/login")
def login():
    google_auth_url = (
        f"https://accounts.google.com/o/oauth2/auth"
        f"?client_id={GOOGLE_CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&response_type=code"
        f"&scope={SCOPES}"
        f"&access_type=offline"
        f"&prompt=consent"
    )
    print("\nOAuth Login URL:", google_auth_url)
    return redirect(google_auth_url)

@app.route("/callback")
def callback():
    code = request.args.get("code")
    data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    }
    response = requests.post(TOKEN_URL, data=data)
    token_json = response.json()
    print("\nDEBUG: Token Response →", token_json)

    if "access_token" in token_json:
        session["access_token"] = token_json["access_token"]
        session["refresh_token"] = token_json.get("refresh_token")
        print("\nDEBUG: Session Data After Login →", dict(session))
        return jsonify({
            "message": "User authenticated",
            "access_token": session["access_token"],
            "refresh_token": session.get("refresh_token", "No refresh token")
        })
    else:
        return jsonify({"error": "Failed to retrieve access token", "details": token_json}), 400

@app.route("/profile")
def profile():
    print("\nDEBUG: Current Session Data →", dict(session))
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

@app.route("/protected_api", methods=["GET"])
def protected_api():
    """
    WEAK endpoint (for demo): requires token only, then randomly accepts/rejects.
    """
    access_token = request.headers.get("Authorization")

    if access_token != VALID_ACCESS_TOKEN:
        return jsonify({"error": "Unauthorized – Invalid or missing access token"}), 401

    # Randomize response: 50% chance of access even with valid token (no signature check)
    if random.choice([True, False]):
        return jsonify({
            "message": "Access granted (random success)",
            "note": "This request was randomly accepted."
        }), 200
    else:
        return jsonify({
            "error": "Access denied (random failure)",
            "note": "Token was valid, but server rejected this request to simulate defense variability."
        }), 401

# ------------------------
# Auto-open browser + run (exe-friendly)
# ------------------------
if __name__ == "__main__":
    url = "http://127.0.0.1:5000/dashboard"
    print(f"🚀 Server starting... Opening: {url}")
    try:
        webbrowser.open(url)
    except Exception:
        pass
    # Use 127.0.0.1 to avoid Windows firewall prompt for 0.0.0.0
    app.run(host="127.0.0.1", port=5000, debug=False)

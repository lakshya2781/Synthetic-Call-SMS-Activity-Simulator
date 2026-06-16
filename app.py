from flask import Flask, jsonify
import threading, time, random, datetime
from datetime import timezone, timedelta

app = Flask(__name__)

IST = timezone(timedelta(hours=5, minutes=30))
def now_ist():
    return datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")

# Per-minute stats
minute_stats = []  # list of {time, calls, sms}
totals = {"total_calls": 0, "total_sms": 0}

def generate_minute_stats():
    while True:
        time.sleep(60)  # every 1 minute

        calls_this_min = random.randint(5, 50)
        sms_this_min = random.randint(20, 200)

        totals["total_calls"] += calls_this_min
        totals["total_sms"] += sms_this_min

        minute_stats.append({
            "time": now_ist(),
            "calls": calls_this_min,
            "sms": sms_this_min
        })
        if len(minute_stats) > 30:
            minute_stats.pop(0)

        print(f"[{now_ist()}] Calls: {calls_this_min} | SMS: {sms_this_min}", flush=True)

@app.route("/")
def home():
    rows = "".join(
        f"<tr><td>{m['time']}</td><td>{m['calls']}</td><td>{m['sms']}</td></tr>"
        for m in reversed(minute_stats[-15:])
    )

    last = minute_stats[-1] if minute_stats else {"calls": 0, "sms": 0}

    return f"""
    <html>
    <head><title>CPaaS Usage Monitor</title><meta http-equiv="refresh" content="20"></head>
    <body style="font-family:monospace; background:#111; color:#0f0; padding:30px">
        <h2>📡 CPaaS Usage Monitor (Simulated)</h2>
        <p style="color:#aaa">⚠️ Simulated data — no real CPaaS account connected yet</p>

        <div style="display:flex; gap:40px; margin:20px 0">
            <div>
                <p>📞 Calls (last minute)</p>
                <h1 style="color:lime">{last['calls']}</h1>
            </div>
            <div>
                <p>💬 SMS (last minute)</p>
                <h1 style="color:cyan">{last['sms']}</h1>
            </div>
            <div>
                <p>📊 Total Calls (since start)</p>
                <h1 style="color:yellow">{totals['total_calls']}</h1>
            </div>
            <div>
                <p>📊 Total SMS (since start)</p>
                <h1 style="color:orange">{totals['total_sms']}</h1>
            </div>
        </div>

        <h3>📋 Per-Minute Log</h3>
        <table style="border-collapse:collapse; width:100%; color:#0f0">
            <tr><th>Time (IST)</th><th>Calls</th><th>SMS</th></tr>
            {rows}
        </table>

        <br>
        <a href="/api" style="color:cyan">📡 JSON API</a>
    </body></html>"""

@app.route("/api")
def api():
    return jsonify({
        "totals": totals,
        "per_minute": minute_stats
    })

if __name__ == "__main__":
    threading.Thread(target=generate_minute_stats, daemon=True).start()
    app.run(host="0.0.0.0", port=10000, threaded=True)

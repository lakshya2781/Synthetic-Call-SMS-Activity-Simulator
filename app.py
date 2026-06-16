from flask import Flask, jsonify
import threading, time, random, datetime
from datetime import timezone, timedelta

app = Flask(__name__)

IST = timezone(timedelta(hours=5, minutes=30))
def now_ist():
    return datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")

call_logs = []
sms_logs = []

def fake_number():
    return f"+91-9{random.randint(100000000, 999999999)}"

def generate_activity():
    while True:
        time.sleep(60)  # every 1 minute, generate a fake event

        # Fake call record
        call_logs.append({
            "time": now_ist(),
            "from": fake_number(),
            "to": fake_number(),
            "duration_sec": random.randint(5, 600),
            "status": random.choice(["Completed", "Missed", "Rejected"])
        })
        if len(call_logs) > 30:
            call_logs.pop(0)

        # Fake SMS record
        sms_logs.append({
            "time": now_ist(),
            "from": fake_number(),
            "to": fake_number(),
            "length_chars": random.randint(5, 160),
            "status": random.choice(["Delivered", "Failed", "Pending"])
        })
        if len(sms_logs) > 30:
            sms_logs.pop(0)

        print(f"[{now_ist()}] Generated 1 fake call + 1 fake SMS", flush=True)

@app.route("/")
def home():
    call_rows = "".join(
        f"<tr><td>{c['time']}</td><td>{c['from']}</td><td>{c['to']}</td><td>{c['duration_sec']}s</td><td>{c['status']}</td></tr>"
        for c in reversed(call_logs[-10:])
    )
    sms_rows = "".join(
        f"<tr><td>{s['time']}</td><td>{s['from']}</td><td>{s['to']}</td><td>{s['length_chars']} chars</td><td>{s['status']}</td></tr>"
        for s in reversed(sms_logs[-10:])
    )

    return f"""
    <html>
    <head><title>Call & SMS Simulator</title><meta http-equiv="refresh" content="15"></head>
    <body style="font-family:monospace; background:#111; color:#0f0; padding:30px">
        <h2>📞 Synthetic Call & SMS Activity Simulator</h2>
        <p style="color:#aaa">⚠️ All data below is randomly generated / fake — not real telecom data</p>

        <h3>📱 Recent Fake Calls</h3>
        <table style="border-collapse:collapse; width:100%; color:#0f0">
            <tr><th>Time</th><th>From</th><th>To</th><th>Duration</th><th>Status</th></tr>
            {call_rows}
        </table>

        <h3>💬 Recent Fake SMS</h3>
        <table style="border-collapse:collapse; width:100%; color:#0ff">
            <tr><th>Time</th><th>From</th><th>To</th><th>Length</th><th>Status</th></tr>
            {sms_rows}
        </table>

        <br>
        <a href="/api/calls" style="color:cyan">📡 Calls JSON</a> |
        <a href="/api/sms" style="color:cyan">📡 SMS JSON</a>
    </body></html>"""

@app.route("/api/calls")
def api_calls():
    return jsonify(call_logs)

@app.route("/api/sms")
def api_sms():
    return jsonify(sms_logs)

if __name__ == "__main__":
    threading.Thread(target=generate_activity, daemon=True).start()
    app.run(host="0.0.0.0", port=10000, threaded=True)
from flask import Flask, jsonify
import threading, time, random, datetime, os
from datetime import timezone, timedelta
import psycopg2

app = Flask(__name__)

IST = timezone(timedelta(hours=5, minutes=30))
def now_ist():
    return datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS cpaas_minute_stats (
            id SERIAL PRIMARY KEY,
            log_time TEXT NOT NULL,
            calls INTEGER NOT NULL,
            sms INTEGER NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS cpaas_totals (
            id INTEGER PRIMARY KEY DEFAULT 1,
            total_calls BIGINT NOT NULL DEFAULT 0,
            total_sms BIGINT NOT NULL DEFAULT 0
        )
    """)
    cur.execute("SELECT COUNT(*) FROM cpaas_totals")
    if cur.fetchone()[0] == 0:
        cur.execute("INSERT INTO cpaas_totals (id, total_calls, total_sms) VALUES (1, 0, 0)")
    conn.commit()
    cur.close()
    conn.close()

def add_minute_stat(calls, sms):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO cpaas_minute_stats (log_time, calls, sms) VALUES (%s,%s,%s)",
        (now_ist(), calls, sms)
    )
    cur.execute(
        "UPDATE cpaas_totals SET total_calls = total_calls + %s, total_sms = total_sms + %s WHERE id=1",
        (calls, sms)
    )
    conn.commit()
    cur.close()
    conn.close()

def get_state():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT log_time, calls, sms FROM cpaas_minute_stats ORDER BY id DESC LIMIT 15")
    per_minute = [{"time": t, "calls": c, "sms": s} for t, c, s in reversed(cur.fetchall())]
    cur.execute("SELECT total_calls, total_sms FROM cpaas_totals WHERE id=1")
    total_calls, total_sms = cur.fetchone()
    cur.close()
    conn.close()
    return per_minute, {"total_calls": total_calls, "total_sms": total_sms}

def generate_minute_stats():
    while True:
        time.sleep(60)
        calls = random.randint(5, 50)
        sms = random.randint(20, 200)
        add_minute_stat(calls, sms)
        print(f"[{now_ist()}] Calls: {calls} | SMS: {sms}", flush=True)

@app.route("/")
def home():
    return """
    <html>
    <head>
        <title>CPaaS Usage Monitor</title>
        <style>body{font-family:monospace;background:#111;color:#0f0;padding:30px;}
        .stats{display:flex;gap:40px;margin:20px 0;}
        table{border-collapse:collapse;width:100%;} td,th{padding:6px;text-align:left;}</style>
    </head>
    <body>
        <h2>📡 CPaaS Usage Monitor (Persistent, Simulated)</h2>
        <p style="color:#aaa">⚠️ Simulated data — no real CPaaS account connected</p>
        <div class="stats">
            <div><p>📞 Calls (last min)</p><h1 id="last_calls" style="color:lime">--</h1></div>
            <div><p>💬 SMS (last min)</p><h1 id="last_sms" style="color:cyan">--</h1></div>
            <div><p>📊 Total Calls</p><h1 id="total_calls" style="color:yellow">--</h1></div>
            <div><p>📊 Total SMS</p><h1 id="total_sms" style="color:orange">--</h1></div>
        </div>
        <h3>📋 Per-Minute Log</h3>
        <table><tr><th>Time (IST)</th><th>Calls</th><th>SMS</th></tr>
        <tbody id="rows"><tr><td colspan="3">loading...</td></tr></tbody></table>
        <script>
        async function updateData() {
            const res = await fetch('/api');
            const data = await res.json();
            const stats = data.per_minute;
            const last = stats[stats.length - 1] || {calls:0, sms:0};
            document.getElementById('last_calls').innerText = last.calls;
            document.getElementById('last_sms').innerText = last.sms;
            document.getElementById('total_calls').innerText = data.totals.total_calls;
            document.getElementById('total_sms').innerText = data.totals.total_sms;
            document.getElementById('rows').innerHTML = stats.slice().reverse().map(m =>
                `<tr><td>${m.time}</td><td>${m.calls}</td><td>${m.sms}</td></tr>`).join('');
        }
        updateData();
        setInterval(updateData, 5000);
        </script>
    </body></html>"""

@app.route("/api")
def api():
    per_minute, totals = get_state()
    return jsonify({"totals": totals, "per_minute": per_minute})

if __name__ == "__main__":
    init_db()
    threading.Thread(target=generate_minute_stats, daemon=True).start()
    app.run(host="0.0.0.0", port=10000, threaded=True)
    

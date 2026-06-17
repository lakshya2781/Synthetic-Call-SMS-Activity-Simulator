from flask import Flask, jsonify, request
import threading, time, random, datetime, os
from datetime import timezone, timedelta
import psycopg2

app = Flask(__name__)

IST = timezone(timedelta(hours=5, minutes=30))
def now_ist():
    return datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")

DATABASE_URL = os.environ.get("DATABASE_URL")
DBVIEW_PASSWORD = os.environ.get("DBVIEW_PASSWORD", "Lakshya2781")

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
        <p><a href="/dbview" style="color:cyan">🗄️ View Database</a></p>
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

@app.route("/dbview")
def dbview():
    provided_password = request.args.get("password", "")
    if provided_password != DBVIEW_PASSWORD:
        return """
        <html>
        <head><title>Locked</title></head>
        <body style="font-family:monospace; background:#111; color:#0f0; padding:60px; text-align:center;">
            <h2>🔒 Access Restricted</h2>
            <p>Add ?password=YOUR_PASSWORD to the URL to view this page.</p>
        </body></html>
        """, 401

    # --- Read filter parameters from URL ---
    search_text = request.args.get("search", "").strip()
    date_from = request.args.get("date_from", "").strip()
    date_to = request.args.get("date_to", "").strip()
    table_filter = request.args.get("table", "all")
    row_limit_raw = request.args.get("limit", "200").strip()

    # Validate row limit
    if row_limit_raw == "all":
        row_limit = None
    else:
        try:
            row_limit = int(row_limit_raw)
            if row_limit <= 0:
                row_limit = 200
        except ValueError:
            row_limit = 200

    conn = get_db()
    cur = conn.cursor()
    sections = []

    table_list = ["counter_state", "counter_logs", "population_state",
                  "population_history", "cpaas_totals", "cpaas_minute_stats",
                  "stock_state", "stock_history"]

    for table_name in table_list:
        if table_filter != "all" and table_filter != table_name:
            continue

        has_log_time = table_name in ("counter_logs", "population_history",
                                       "cpaas_minute_stats", "stock_history")

        if has_log_time:
            query = f"SELECT * FROM {table_name} WHERE 1=1"
            params = []
            if date_from:
                query += " AND log_time >= %s"
                params.append(date_from)
            if date_to:
                query += " AND log_time <= %s"
                params.append(date_to + " 23:59:59")
            if search_text:
                query += " AND log_time::text ILIKE %s"
                params.append(f"%{search_text}%")
            query += " ORDER BY id DESC"
            if row_limit is not None:
                query += " LIMIT %s"
                params.append(row_limit)
            cur.execute(query, params)
        else:
            cur.execute(f"SELECT * FROM {table_name} ORDER BY 1")

        cols = [desc[0] for desc in cur.description]
        rows = cur.fetchall()
        sections.append((table_name, cols, rows))

    cur.close()
    conn.close()

    # --- Build filter form ---
    table_options = "".join(
        f'<option value="{t}" {"selected" if table_filter==t else ""}>{t}</option>'
        for t in table_list
    )

    limit_options_list = ["20", "50", "200", "500", "1000", "all"]
    limit_options = "".join(
        f'<option value="{l}" {"selected" if row_limit_raw==l else ""}>{"All" if l=="all" else l}</option>'
        for l in limit_options_list
    )

    filter_html = f"""
    <form method="GET" style="margin-bottom:25px; background:#1a1a1a; padding:15px; border-radius:6px;">
        <input type="hidden" name="password" value="{provided_password}">
        <label>Table:
            <select name="table">
                <option value="all" {"selected" if table_filter=="all" else ""}>All Tables</option>
                {table_options}
            </select>
        </label>
        &nbsp;&nbsp;
        <label>Show:
            <select name="limit">{limit_options}</select> rows
        </label>
        &nbsp;&nbsp;
        <label>Search (timestamp text): <input type="text" name="search" value="{search_text}" placeholder="e.g. 2026-06-17"></label>
        &nbsp;&nbsp;
        <label>From: <input type="date" name="date_from" value="{date_from}"></label>
        &nbsp;&nbsp;
        <label>To: <input type="date" name="date_to" value="{date_to}"></label>
        &nbsp;&nbsp;
        <button type="submit" style="background:#0a5;color:white;border:none;padding:6px 14px;cursor:pointer;border-radius:4px;">Apply Filters</button>
        <a href="/dbview?password={provided_password}" style="color:cyan; margin-left:10px;">Clear Filters</a>
    </form>
    """

    html = f"""
    <html>
    <head>
        <title>Database Viewer</title>
        <style>
            body {{ font-family:monospace; background:#111; color:#0f0; padding:30px; }}
            h3 {{ color:cyan; margin-top:30px; }}
            table {{ border-collapse:collapse; width:100%; margin-bottom:10px; }}
            td, th {{ padding:6px 10px; text-align:left; border-bottom:1px solid #333; font-size:13px; }}
            th {{ color:yellow; }}
            input, select {{ background:#222; color:#0f0; border:1px solid #444; padding:4px; }}
            label {{ color:#aaa; }}
        </style>
    </head>
    <body>
        <h2>🗄️ Database Viewer (Read-Only)</h2>
        <p style="color:#aaa">Showing tables from shared-logs-db</p>
        {filter_html}
    """

    for table_name, cols, rows in sections:
        html += f"<h3>📋 {table_name} ({len(rows)} rows shown)</h3>"
        html += "<table><tr>" + "".join(f"<th>{c}</th>" for c in cols) + "</tr>"
        for row in rows:
            html += "<tr>" + "".join(f"<td>{val}</td>" for val in row) + "</tr>"
        html += "</table>"

    html += "</body></html>"
    return html

if __name__ == "__main__":
    init_db()
    threading.Thread(target=generate_minute_stats, daemon=True).start()
    app.run(host="0.0.0.0", port=10000, threaded=True)

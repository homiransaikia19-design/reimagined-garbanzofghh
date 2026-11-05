from fastapi import FastAPI, HTTPException, Query, Depends, Form, Response, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import Column, String
import datetime
import secrets

import models
from database import engine, SessionLocal, Base

app = FastAPI(title="Professional Phone API")

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"
DISCORD_LINK = "https://discord.gg/Qnfp2KZbW9"

# Define the PhoneRecord table
class PhoneRecord(Base):
    __tablename__ = "phone_numbers"
    mobile = Column(String(20), primary_key=True, index=True)
    name = Column(String(255))
    address = Column(String(500))
    pincode = Column(String(20))
    city = Column(String(100))

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# =====================================================================
# 1. THE PUBLIC API ENDPOINT (Includes Limits & Support Link)
# =====================================================================
@app.get("/api/infonumber")
def get_info_by_number(
    number: str = Query(...),
    api: str = Query(...),
    db: Session = Depends(get_db)
):
    key_record = db.query(models.APIKey).filter(models.APIKey.key_string == api).first()
    if not key_record:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    if not key_record.is_active:
        raise HTTPException(status_code=403, detail="API Key is disabled")
    if key_record.expires_at < datetime.datetime.utcnow():
        raise HTTPException(status_code=403, detail="API Key has expired")

    today = datetime.date.today()
    usage_record = db.query(models.APIUsageLog).filter(
        models.APIUsageLog.api_key_id == key_record.id,
        models.APIUsageLog.usage_date == today
    ).first()

    if usage_record:
        if usage_record.hit_count >= key_record.request_limit:
            raise HTTPException(status_code=429, detail=f"Daily limit reached. Upgrade or contact support: {DISCORD_LINK}")
        usage_record.hit_count += 1
    else:
        new_log = models.APIUsageLog(api_key_id=key_record.id, usage_date=today, hit_count=1)
        db.add(new_log)

    db.commit()
    
    # Calculate limit left
    current_usage = usage_record.hit_count if usage_record else 1
    limit_left = key_record.request_limit - current_usage

    record = db.query(PhoneRecord).filter(PhoneRecord.mobile == number).first()
    
    if record:
        return {
            "status": "success",
            "api_key_name": key_record.owner_name,
            "limit_left": limit_left,
            "support_discord": DISCORD_LINK,
            "data": {
                "mobile": record.mobile, 
                "name": record.name, 
                "address": record.address, 
                "pincode": record.pincode, 
                "city": record.city
            }
        }
    return {
        "status": "error", 
        "message": "Number not found",
        "api_key_name": key_record.owner_name,
        "limit_left": limit_left,
        "support_discord": DISCORD_LINK
    }


# =====================================================================
# 2. THE PROFESSIONAL ADMIN PANEL (MATCHING SCREENSHOT & FIXED LOGIN)
# =====================================================================
@app.get("/admin", response_class=HTMLResponse)
def admin_panel(admin_session: str = Cookie(None)):
    # If not logged in, show the login screen
    if admin_session != "logged_in":
        return """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <title>Admin Login</title>
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
            <style>
                body { background: #0a0a0a; color: white; font-family: 'Inter', sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
                .login-box { background: #111111; padding: 40px; border-radius: 12px; border: 1px solid #222; width: 100%; max-width: 350px; }
                h2 { text-align: center; margin-bottom: 20px; color: #00ff66; }
                input { width: 100%; padding: 12px; margin-bottom: 15px; background: #0a0a0a; border: 1px solid #222; color: white; border-radius: 6px; box-sizing: border-box; }
                button { width: 100%; padding: 12px; background: #00ff66; color: black; border: none; border-radius: 6px; font-weight: bold; cursor: pointer; font-size: 1rem; }
                button:hover { background: #00cc52; }
            </style>
        </head>
        <body>
            <div class="login-box">
                <h2>Admin Login</h2>
                <form action="/admin/login" method="post">
                    <input type="text" name="username" placeholder="Username" required>
                    <input type="password" name="password" placeholder="Password" required>
                    <button type="submit">Login</button>
                </form>
            </div>
        </body>
        </html>
        """

    # If logged in, show the dashboard
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>MARKETPLACE - Admin</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
        <style>
            :root { --bg-body: #0a0a0a; --bg-sidebar: #000000; --bg-card: #111111; --border: #222222; --text-main: #e0e0e0; --text-muted: #888888; --primary: #00ff66; --accent: #3b82f6; --danger: #ef4444; }
            * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', sans-serif; }
            body { background-color: var(--bg-body); color: var(--text-main); min-height: 100vh; display: flex; }
            
            .sidebar { width: 260px; background: var(--bg-sidebar); border-right: 1px solid var(--border); padding: 20px; display: flex; flex-direction: column; }
            .logo { display: flex; align-items: center; gap: 10px; font-size: 1rem; font-weight: 700; color: white; margin-bottom: 30px; letter-spacing: 1px; }
            .logo-icon { background: var(--primary); color: black; width: 28px; height: 28px; border-radius: 6px; display: flex; align-items: center; justify-content: center; font-weight: bold; }
            .nav-item { padding: 12px; margin-bottom: 5px; border-radius: 6px; cursor: pointer; color: var(--text-muted); display: flex; align-items: center; gap: 10px; font-size: 0.85rem; }
            .nav-item:hover { background: rgba(255,255,255,0.05); color: white; }
            .nav-item.active { color: var(--primary); font-weight: 600; }
            .nav-item.active::before { content: ''; display: inline-block; width: 4px; height: 16px; background: var(--primary); border-radius: 2px; margin-right: 5px; }
            
            .user-profile { margin-top: auto; background: #111; padding: 10px; border-radius: 8px; display: flex; align-items: center; gap: 10px; border: 1px solid var(--border); }
            .avatar { background: var(--primary); width: 30px; height: 30px; border-radius: 50%; display: flex; justify-content: center; align-items: center; color: black; font-weight: bold; }

            .main-content { flex: 1; padding: 30px; overflow-y: auto; }
            .header { margin-bottom: 30px; }
            .header h1 { font-size: 1.4rem; color: white; font-weight: 600; }
            .header p { color: var(--text-muted); font-size: 0.85rem; margin-top: 5px; }
            
            .stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 30px; }
            .stat-card { background: var(--bg-card); border: 1px solid var(--border); padding: 20px; border-radius: 8px; }
            .stat-title { font-size: 0.7rem; text-transform: uppercase; color: var(--text-muted); margin-bottom: 10px; display: flex; justify-content: space-between; letter-spacing: 0.5px; }
            .stat-value { font-size: 1.8rem; font-weight: 700; color: white; margin-bottom: 5px; }
            .stat-sub { font-size: 0.7rem; color: var(--primary); }

            .card { background: var(--bg-card); border: 1px solid var(--border); border-radius: 8px; padding: 25px; margin-bottom: 20px; }
            .card-title { font-size: 1rem; color: white; margin-bottom: 20px; display: flex; align-items: center; gap: 10px; font-weight: 600; }
            .form-group { margin-bottom: 15px; }
            .form-group label { display: block; font-size: 0.75rem; color: var(--text-muted); margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.5px;}
            input { width: 100%; padding: 12px; background: var(--bg-body); border: 1px solid var(--border); border-radius: 6px; color: white; font-size: 0.9rem; }
            input:focus { outline: none; border-color: var(--primary); }
            
            .module-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-bottom: 20px; }
            .module-btn { background: var(--bg-body); border: 1px solid var(--border); padding: 15px 10px; border-radius: 6px; text-align: center; color: var(--text-muted); font-size: 0.75rem; cursor: pointer; transition: 0.2s; }
            .module-btn.active { border-color: var(--primary); color: var(--primary); background: rgba(0, 255, 102, 0.05); }
            .module-icon { font-size: 1.2rem; display: block; margin-bottom: 5px; }

            .btn-primary { background: var(--primary); color: black; border: none; padding: 12px 20px; border-radius: 6px; cursor: pointer; font-weight: 700; font-size: 0.85rem; display: inline-flex; align-items: center; gap: 8px; }
            .btn-primary:hover { background: #00cc52; }
            
            table { width: 100%; border-collapse: collapse; }
            th, td { padding: 15px 10px; text-align: left; border-bottom: 1px solid var(--border); font-size: 0.85rem; }
            th { color: var(--text-muted); font-weight: 500; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.5px; }
            .badge { padding: 4px 8px; border-radius: 4px; font-size: 0.75rem; background: rgba(59, 130, 246, 0.1); color: var(--accent); }
            .btn-delete { background: transparent; border: 1px solid var(--danger); color: var(--danger); padding: 5px 10px; border-radius: 4px; cursor: pointer; font-size: 0.75rem; }
            .btn-delete:hover { background: var(--danger); color: white; }
        </style>
    </head>
    <body>

        <div class="sidebar">
            <div class="logo"><div class="logo-icon">M</div> MARKETPLACE</div>
            <div class="nav-item active">Dashboard</div>
            <div class="nav-item">API Keys</div>
            <div class="nav-item">Analytics</div>
            <div class="nav-item">Users</div>
            <div class="nav-item">Servers</div>
            <div class="nav-item">Activity</div>
            <div class="nav-item">Settings</div>
            
            <div class="user-profile">
                <div class="avatar">A</div>
                <div>
                    <div style="font-size: 0.8rem; color: white; font-weight: 600;">admin</div>
                    <div style="font-size: 0.65rem; color: var(--text-muted);">Administrator</div>
                </div>
                <div style="margin-left: auto; cursor:pointer;" onclick="window.location.href='/admin/logout'"><span style="color:var(--text-muted); font-size:0.8rem;">⏻</span></div>
            </div>
        </div>

        <div class="main-content">
            <div class="header">
                <h1>Good Morning, Admin</h1>
                <p>Here's what's happening today</p>
            </div>

            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-title">TOTAL KEYS <span>🔑</span></div>
                    <div class="stat-value" id="stat-total">0</div>
                    <div class="stat-sub" id="stat-active">0 active</div>
                </div>
                <div class="stat-card">
                    <div class="stat-title">ACTIVE KEYS <span>✅</span></div>
                    <div class="stat-value" id="stat-active-val">0</div>
                    <div class="stat-sub">100% utilization</div>
                </div>
                <div class="stat-card">
                    <div class="stat-title">TOTAL API CALLS <span>➔</span></div>
                    <div class="stat-value" id="stat-total-calls">0</div>
                    <div class="stat-sub">+0 today</div>
                </div>
                <div class="stat-card">
                    <div class="stat-title">TODAY'S CALLS <span>📅</span></div>
                    <div class="stat-value" id="stat-today-calls">0</div>
                    <div class="stat-sub">0% of total</div>
                </div>
            </div>

            <div class="card">
                <div class="card-title"><span>+</span> Create API Key</div>
                
                <div class="form-group">
                    <label>API KEY</label>
                    <input type="text" id="clientName" placeholder="Enter unique API key">
                </div>

                <div class="module-grid">
                    <div class="module-btn active"><span class="module-icon">📞</span>NUMBER</div>
                    <div class="module-btn"><span class="module-icon">🆔</span>AADHAAR</div>
                    <div class="module-btn"><span class="module-icon">📄</span>RATION</div>
                    <div class="module-btn"><span class="module-icon">🚗</span>VEHICLE</div>
                    <div class="module-btn"><span class="module-icon">🏢</span>TOGNUM</div>
                    <div class="module-btn"><span class="module-icon">🚙</span>VEHICLE</div>
                    <div class="module-btn"><span class="module-icon">🏦</span>IFSC</div>
                    <div class="module-btn"><span class="module-icon">📍</span>PINCODE</div>
                </div>

                <div class="form-group">
                    <label>DAILY LIMIT</label>
                    <input type="number" id="limit" value="100">
                </div>

                <div class="form-group">
                    <label>EXPIRY TYPE</label>
                    <div style="display:grid; grid-template-columns: 1fr 1fr 1fr; gap:10px;">
                        <div class="module-btn">⏱ Demo (Hours)</div>
                        <div class="module-btn">⭐ Premium (Days)</div>
                        <div class="module-btn active">📅 Custom Date</div>
                    </div>
                </div>

                <div class="form-group" style="margin-top: 10px;">
                    <label>EXPIRY (DAYS)</label>
                    <input type="number" id="validity" value="30">
                </div>

                <button class="btn-primary" onclick="createKey()">🚀 Create Key</button>
            </div>

            <div class="card">
                <div class="card-title"><span>📋</span> All API Keys</div>
                <table id="keysTable">
                    <thead>
                        <tr><th>API KEY</th><th>EXPIRES</th><th>LIMIT</th><th>USED TODAY</th><th>ACTION</th></tr>
                    </thead>
                    <tbody></tbody>
                </table>
            </div>
        </div>

        <script>
            window.onload = function() { loadData(); };

            async function loadData() {
                const res = await fetch('/admin/get_dashboard_data?admin_pass=admin123');
                const data = await res.json();
                
                if(!res.ok) return;

                document.getElementById('stat-total').innerText = data.stats.total_keys;
                document.getElementById('stat-active').innerText = data.stats.active_keys + " active";
                document.getElementById('stat-active-val').innerText = data.stats.active_keys;
                document.getElementById('stat-total-calls').innerText = data.stats.total_calls;
                document.getElementById('stat-today-calls').innerText = data.stats.today_calls;

                const tbody = document.querySelector('#keysTable tbody');
                tbody.innerHTML = "";
                data.keys.forEach(item => {
                    const expDate = new Date(item.expires_at).toLocaleDateString();
                    tbody.innerHTML += '<tr>' +
                        '<td><b>' + item.key_string + '</b></td>' +
                        '<td>' + expDate + '</td>' +
                        '<td>' + item.request_limit + '</td>' +
                        '<td><span class="badge">' + item.used_today + '</span></td>' +
                        '<td><button class="btn-delete" onclick="deleteKey(\'' + item.key_string + '\')">Delete</button></td>' +
                        '</tr>';
                });
            }

            async function createKey() {
                const name = document.getElementById('clientName').value;
                const limit = document.getElementById('limit').value;
                const days = document.getElementById('validity').value;
                
                if(!name) { alert("Enter an API Name"); return; }

                const res = await fetch('/admin/generate_key?owner_name=' + name + '&request_limit=' + limit + '&validity_days=' + days + '&admin_pass=admin123', { method: 'POST' });
                const data = await res.json();
                if(res.ok) {
                    alert("API Key Created: " + data.api_key);
                    document.getElementById('clientName').value = "";
                    loadData();
                } else { alert("Error: " + data.detail); }
            }

            async function deleteKey(keyName) {
                if(!confirm("Delete this key?")) return;
                const res = await fetch('/admin/delete_key?key_name=' + keyName + '&admin_pass=admin123', { method: 'DELETE' });
                if(res.ok) { loadData(); }
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.post("/admin/login")
def login(username: str = Form(...), password: str = Form(...)):
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        response = RedirectResponse(url="/admin", status_code=303)
        response.set_cookie(key="admin_session", value="logged_in", httponly=True)
        return response
    return RedirectResponse(url="/admin", status_code=303)

@app.get("/admin/logout")
def logout():
    response = RedirectResponse(url="/admin", status_code=303)
    response.delete_cookie("admin_session")
    return response

# =====================================================================
# 3. DASHBOARD DATA ENDPOINTS
# =====================================================================
@app.get("/admin/get_dashboard_data")
def get_dashboard_data(admin_pass: str, db: Session = Depends(get_db)):
    if admin_pass != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Wrong Password")
    
    today = datetime.date.today()
    keys = db.query(models.APIKey).all()
    
    total_keys = len(keys)
    active_keys = sum(1 for k in keys if k.is_active and k.expires_at > datetime.datetime.utcnow())
    all_logs = db.query(models.APIUsageLog).all()
    total_calls = sum(log.hit_count for log in all_logs)
    today_logs = db.query(models.APIUsageLog).filter(models.APIUsageLog.usage_date == today).all()
    today_calls = sum(log.hit_count for log in today_logs)
    
    key_list = []
    for key in keys:
        log = db.query(models.APIUsageLog).filter(
            models.APIUsageLog.api_key_id == key.id,
            models.APIUsageLog.usage_date == today
        ).first()
        used_today = log.hit_count if log else 0
        key_list.append({
       
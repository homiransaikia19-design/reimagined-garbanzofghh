from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import Column, String
import datetime
import secrets

import models
from database import engine, SessionLocal, Base

app = FastAPI(title="Professional Phone API")

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

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
# 1. THE PUBLIC API ENDPOINT
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
            raise HTTPException(status_code=429, detail="Daily API Limit Reached")
        usage_record.hit_count += 1
    else:
        new_log = models.APIUsageLog(api_key_id=key_record.id, usage_date=today, hit_count=1)
        db.add(new_log)

    db.commit()

    record = db.query(PhoneRecord).filter(PhoneRecord.mobile == number).first()
    if record:
        return {
            "status": "success", 
            "data": {
                "mobile": record.mobile, 
                "name": record.name, 
                "address": record.address, 
                "pincode": record.pincode, 
                "city": record.city
            }
        }
    return {"status": "error", "message": "Number not found"}


# =====================================================================
# 2. THE PROFESSIONAL ADMIN PANEL
# =====================================================================
@app.get("/admin", response_class=HTMLResponse)
def admin_panel():
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>MARKETPLACE - Admin</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
        <style>
            :root { --bg-body: #0d1117; --bg-sidebar: #161b22; --bg-card: #161b22; --border: #30363d; --text-main: #c9d1d9; --text-muted: #8b949e; --primary: #238636; --primary-hover: #2ea043; --accent: #58a6ff; --danger: #f85149; }
            * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', sans-serif; }
            body { background-color: var(--bg-body); color: var(--text-main); min-height: 100vh; display: flex; }
            
            .sidebar { width: 260px; background: var(--bg-sidebar); border-right: 1px solid var(--border); padding: 20px; display: flex; flex-direction: column; }
            .logo { display: flex; align-items: center; gap: 10px; font-size: 1.2rem; font-weight: 700; color: white; margin-bottom: 30px; }
            .logo-icon { background: var(--primary); width: 30px; height: 30px; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-weight: bold; }
            .nav-item { padding: 12px; margin-bottom: 5px; border-radius: 6px; cursor: pointer; color: var(--text-muted); display: flex; align-items: center; gap: 10px; font-size: 0.9rem; }
            .nav-item:hover { background: rgba(255,255,255,0.05); color: white; }
            .nav-item.active { background: rgba(35, 134, 54, 0.1); color: var(--primary); font-weight: 600; border-left: 3px solid var(--primary); }

            .main-content { flex: 1; padding: 30px; overflow-y: auto; }
            .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; }
            .header h1 { font-size: 1.5rem; color: white; }
            .header p { color: var(--text-muted); font-size: 0.9rem; }
            .btn-logout { background: transparent; border: 1px solid var(--border); color: white; padding: 8px 16px; border-radius: 6px; cursor: pointer; }
            
            .stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-bottom: 30px; }
            .stat-card { background: var(--bg-card); border: 1px solid var(--border); padding: 20px; border-radius: 8px; }
            .stat-title { font-size: 0.75rem; text-transform: uppercase; color: var(--text-muted); margin-bottom: 10px; display: flex; justify-content: space-between; }
            .stat-value { font-size: 1.8rem; font-weight: 700; color: white; margin-bottom: 5px; }
            .stat-sub { font-size: 0.75rem; color: var(--primary); }

            .card { background: var(--bg-card); border: 1px solid var(--border); border-radius: 8px; padding: 20px; margin-bottom: 20px; }
            .card-title { font-size: 1.1rem; color: white; margin-bottom: 20px; display: flex; align-items: center; gap: 10px; }
            .form-group { margin-bottom: 15px; }
            .form-group label { display: block; font-size: 0.8rem; color: var(--text-muted); margin-bottom: 5px; }
            input { width: 100%; padding: 10px; background: var(--bg-body); border: 1px solid var(--border); border-radius: 6px; color: white; font-size: 0.9rem; }
            input:focus { outline: none; border-color: var(--accent); }
            
            .module-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-bottom: 20px; }
            .module-btn { background: var(--bg-body); border: 1px solid var(--border); padding: 15px; border-radius: 6px; text-align: center; color: var(--text-muted); cursor: not-allowed; opacity: 0.5; }
            .module-btn.active { border-color: var(--primary); color: var(--primary); opacity: 1; cursor: pointer; background: rgba(35, 134, 54, 0.05); }

            .btn-primary { background: var(--primary); color: white; border: none; padding: 10px 20px; border-radius: 6px; cursor: pointer; font-weight: 600; width: 100%; }
            .btn-primary:hover { background: var(--primary-hover); }
            
            table { width: 100%; border-collapse: collapse; }
            th, td { padding: 12px; text-align: left; border-bottom: 1px solid var(--border); font-size: 0.85rem; }
            th { color: var(--text-muted); font-weight: 500; }
            .badge { padding: 4px 8px; border-radius: 4px; font-size: 0.75rem; background: rgba(88, 166, 255, 0.1); color: var(--accent); }
            .btn-delete { background: transparent; border: 1px solid var(--danger); color: var(--danger); padding: 5px 10px; border-radius: 4px; cursor: pointer; font-size: 0.75rem; }
            .btn-delete:hover { background: var(--danger); color: white; }

            .login-container { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: var(--bg-body); display: flex; align-items: center; justify-content: center; z-index: 1000; }
            .login-box { background: var(--bg-card); border: 1px solid var(--border); padding: 40px; border-radius: 12px; width: 100%; max-width: 400px; }
            .login-box h2 { color: white; margin-bottom: 20px; text-align: center; }
        </style>
    </head>
    <body>

        <!-- LOGIN SCREEN -->
        <div class="login-container" id="loginScreen">
            <div class="login-box">
                <h2>Admin Login</h2>
                <div class="form-group">
                    <label>Username</label>
                    <input type="text" id="username" value="admin">
                </div>
                <div class="form-group">
                    <label>Password</label>
                    <input type="password" id="password" placeholder="Enter password">
                </div>
                <button class="btn-primary" onclick="login()">Login</button>
            </div>
        </div>

        <!-- DASHBOARD -->
        <div id="dashboard" style="display: none; width: 100%; display: flex;">
            <div class="sidebar">
                <div class="logo"><div class="logo-icon">M</div> MARKETPLACE</div>
                <div class="nav-item active">Dashboard</div>
                <div class="nav-item">API Keys</div>
                <div class="nav-item">Analytics</div>
                <div class="nav-item">Users</div>
                <div class="nav-item">Settings</div>
                <div style="margin-top: auto;">
                    <button class="btn-logout" style="width: 100%;" onclick="logout()">Logout</button>
                </div>
            </div>

            <div class="main-content">
                <div class="header">
                    <div>
                        <h1>Good Morning, Admin</h1>
                        <p>Here's what's happening today</p>
                    </div>
                </div>

                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-title">TOTAL KEYS <span style="color:var(--primary);">🔑</span></div>
                        <div class="stat-value" id="stat-total">0</div>
                        <div class="stat-sub" id="stat-active">0 Active</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-title">ACTIVE KEYS <span style="color:var(--primary);">✅</span></div>
                        <div class="stat-value" id="stat-active-val">0</div>
                        <div class="stat-sub">Currently in use</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-title">TOTAL API CALLS <span style="color:var(--accent);">📈</span></div>
                        <div class="stat-value" id="stat-total-calls">0</div>
                        <div class="stat-sub">All time</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-title">TODAY'S CALLS <span style="color:var(--accent);">📅</span></div>
                        <div class="stat-value" id="stat-today-calls">0</div>
                        <div class="stat-sub">Since midnight</div>
                    </div>
                </div>

                <div class="card">
                    <div class="card-title"><span style="color:var(--primary);">+</span> Create API Key</div>
                    
                    <div class="form-group">
                        <label>API KEY NAME</label>
                        <input type="text" id="clientName" placeholder="Enter unique API key name">
                    </div>

                    <label style="font-size:0.8rem; color:var(--text-muted); margin-bottom:10px; display:block;">SELECT MODULE</label>
                    <div class="module-grid">
                        <div class="module-btn active">📞<br>NUMBER</div>
                        <div class="module-btn">🆔<br>AADHAAR</div>
                        <div class="module-btn">📄<br>RATION</div>
                        <div class="module-btn">🚗<br>VEHICLE</div>
                    </div>

                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                        <div class="form-group">
                            <label>DAILY LIMIT</label>
                            <input type="number" id="limit" value="100">
                        </div>
                        <div class="form-group">
                            <label>EXPIRY (DAYS)</label>
                            <input type="number" id="validity" value="30">
                        </div>
                    </div>

                    <button class="btn-primary" onclick="createKey()">🚀 Create Key</button>
                </div>

                <div class="card">
                    <div class="card-title">📋 All API Keys</div>
                    <table id="keysTable">
                        <thead>
                            <tr><th>KEY NAME</th><th>EXPIRES</th><th>LIMIT</th><th>USED TODAY</th><th>ACTION</th></tr>
                        </thead>
                        <tbody></tbody>
                    </table>
                </div>
            </div>
        </div>

        <script>
            window.onload = function() {
                if (localStorage.getItem('adminPass') === "admin123") {
                    showDashboard();
                }
            };

            function login() {
                const pass = document.getElementById('password').value;
                if (pass === "admin123") {
                    localStorage.setItem('adminPass', pass);
                    showDashboard();
                } else {
                    alert("Wrong Password!");
                }
            }

            function logout() {
                localStorage.removeItem('adminPass');
                location.reload();
            }

            function showDashboard() {
                document.getElementById('loginScreen').style.display = 'none';
                document.getElementById('dashboard').style.display = 'flex';
                loadData();
            }

            async function loadData() {
                const pass = localStorage.getItem('adminPass');
                const res = await fetch('/admin/get_dashboard_data?admin_pass=' + pass);
                const data = await res.json();
                
                if(!res.ok) return;

                document.getElementById('stat-total').innerText = data.stats.total_keys;
                document.getElementById('stat-active').innerText = data.stats.active_keys + " Active";
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
                        '<td><span class="badge">' + item.used_today + ' hits</span></td>' +
                        '<td><button class="btn-delete" onclick="deleteKey(\'' + item.key_string + '\')">Delete</button></td>' +
                        '</tr>';
                });
            }

            async function createKey() {
                const name = document.getElementById('clientName').value;
                const limit = document.getElementById('limit').value;
                const days = document.getElementById('validity').value;
                const pass = localStorage.getItem('adminPass');
                
                if(!name) { alert("Enter an API Name"); return; }

                const res = await fetch('/admin/generate_key?owner_name=' + name + '&request_limit=' + limit + '&validity_days=' + days + '&admin_pass=' + pass, { method: 'POST' });
                const data = await res.json();
                if(res.ok) {
                    alert("API Key Created: " + data.api_key);
                    document.getElementById('clientName').value = "";
                    loadData();
                } else { alert("Error: " + data.detail); }
            }

            async function deleteKey(keyName) {
                const pass = localStorage.getItem('adminPass');
                if(!confirm("Delete this key?")) return;
                const res = await fetch('/admin/delete_key?key_name=' + keyName + '&admin_pass=' + pass, { method: 'DELETE' });
                if(res.ok) { loadData(); }
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


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
            "key_string": key.key_string,
            "expires_at": key.expires_at,
            "request_limit": key.request_limit,
            "used_today": used_today
        })
        
    return {
        "stats": {
            "total_keys": total_keys,
            "active_keys": active_keys,
            "total_calls": total_calls,
            "today_calls": today_calls
        },
        "keys": key_list
    }

@app.post("/admin/generate_key")
def generate_key(owner_name: str, request_limit: int, validity_days: int, admin_pass: str, db: Session = Depends(get_db)):
    if admin_pass != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Wrong Admin Password")
    existing_key = db.query(models.APIKey).filter(models.APIKey.key_string == owner_name).first()
    if existing_key:
        raise HTTPException(status_code=400, detail="This API Key Name already exists.")
    expires = datetime.datetime.utcnow() + datetime.timedelta(days=validity_days)
    db_key = models.APIKey(key_string=owner_name, owner_name=owner_name, expires_at=expires, request_limit=request_limit)
    db.add(db_key)
    db.commit()
    return {"status": "success", "api_key": owner_name}

@app.delete("/admin/delete_key")
def delete_key(key_name: str, admin_pass: str, db: Session = Depends(get_db)):
    if admin_pass != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Wrong Admin Password")
    key_record = db.query(models.APIKey).filter(models.APIKey.key_string == key_name).first()
    if not key_record:
        raise HTTPException(status_code=404, detail="Key not found")
    db.delete(key_record)
    db.commit()
    return {"status": "success"}

@app.get("/")
def home():
    return {"status": "Online"}
from fastapi import FastAPI, HTTPException, Query, Depends, Form
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import Column, String
import datetime
import secrets

import models
from database import engine, SessionLocal, Base

app = FastAPI(title="Professional Phone API")

ADMIN_PASSWORD = "admin123"
DISCORD_LINK = "https://discord.gg/Qnfp2KZbW9"

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
            raise HTTPException(status_code=429, detail=f"Daily limit reached. Contact support: {DISCORD_LINK}")
        usage_record.hit_count += 1
    else:
        new_log = models.APIUsageLog(api_key_id=key_record.id, usage_date=today, hit_count=1)
        db.add(new_log)

    db.commit()
    
    current_usage = usage_record.hit_count if usage_record else 1
    limit_left = key_record.request_limit - current_usage

    record = db.query(PhoneRecord).filter(PhoneRecord.mobile == number).first()
    
    if record:
        return {
            "status": "success",
            "api_key_name": key_record.owner_name,
            "limit_left": limit_left,
            "support_discord": DISCORD_LINK,
            "data": {"mobile": record.mobile, "name": record.name, "address": record.address, "pincode": record.pincode, "city": record.city}
        }
    return {
        "status": "error", "message": "Number not found",
        "api_key_name": key_record.owner_name, "limit_left": limit_left, "support_discord": DISCORD_LINK
    }

# =====================================================================
# 2. THE ADMIN PANEL (LOGIN SCREEN)
# =====================================================================
@app.get("/admin", response_class=HTMLResponse)
def admin_login():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Admin Login</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { background: #050505; color: white; font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
            .box { background: #111; padding: 40px; border-radius: 10px; border: 1px solid #222; width: 300px; text-align: center; }
            input { width: 90%; padding: 12px; margin: 10px 0; background: #000; border: 1px solid #333; color: white; border-radius: 5px; }
            button { width: 100%; padding: 12px; background: #00ff66; color: black; border: none; border-radius: 5px; font-weight: bold; margin-top: 10px; cursor: pointer; font-size: 1rem; }
            button:hover { background: #00cc52; }
        </style>
    </head>
    <body>
        <div class="box">
            <h2 style="color:#00ff66;">Admin Login</h2>
            <form action="/admin/dashboard" method="get">
                <input type="password" name="password" placeholder="Enter Password" required>
                <button type="submit">Login</button>
            </form>
        </div>
    </body>
    </html>
    """

# =====================================================================
# 3. THE DASHBOARD (LOADED AFTER LOGIN)
# =====================================================================
@app.get("/admin/dashboard", response_class=HTMLResponse)
def admin_dashboard(password: str):
    # Check password from URL
    if password != ADMIN_PASSWORD:
        return HTMLResponse(content="<h1 style='color:red; text-align:center; margin-top:50px;'>Wrong Password! <a href='/admin'>Try Again</a></h1>", status_code=401)

    # If password is correct, show dashboard
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>MARKETPLACE - Dashboard</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
        <style>
            :root { --bg: #050505; --card: #111; --border: #222; --text: #fff; --muted: #888; --primary: #00ff66; --danger: #ef4444; }
            * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', sans-serif; }
            body { background: var(--bg); color: var(--text); display: flex; min-height: 100vh; }
            .sidebar { width: 240px; background: #000; border-right: 1px solid var(--border); padding: 20px; display: flex; flex-direction: column; }
            .logo { font-weight: 700; font-size: 1.1rem; margin-bottom: 30px; display: flex; align-items: center; gap: 8px; }
            .logo-icon { background: var(--primary); color: black; width: 24px; height: 24px; border-radius: 4px; display: flex; justify-content: center; align-items: center; font-weight: bold; }
            .nav { color: var(--muted); font-size: 0.9rem; padding: 10px; margin-bottom: 5px; border-radius: 5px; }
            .nav.active { color: var(--primary); font-weight: 600; }
            .logout { margin-top: auto; color: var(--danger); text-decoration: none; font-weight: 600; padding: 10px; }
            
            .main { flex: 1; padding: 30px; overflow-y: auto; }
            .header { display: flex; justify-content: space-between; margin-bottom: 30px; }
            .header h1 { font-size: 1.5rem; }
            
            .stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 30px; }
            .stat-card { background: var(--card); border: 1px solid var(--border); padding: 20px; border-radius: 8px; }
            .stat-title { color: var(--muted); font-size: 0.75rem; text-transform: uppercase; margin-bottom: 10px; display: flex; justify-content: space-between; }
            .stat-val { font-size: 1.8rem; font-weight: 700; }
            
            .card { background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 25px; margin-bottom: 30px; }
            .card-title { font-weight: 600; margin-bottom: 20px; display: flex; align-items: center; gap: 8px; }
            .form-group { margin-bottom: 15px; }
            .form-group label { display: block; color: var(--muted); font-size: 0.75rem; margin-bottom: 5px; text-transform: uppercase; }
            input { width: 100%; padding: 12px; background: #000; border: 1px solid var(--border); color: white; border-radius: 6px; outline: none; }
            input:focus { border-color: var(--primary); }
            .row { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
            button { background: var(--primary); color: black; border: none; padding: 12px 24px; border-radius: 6px; font-weight: 700; cursor: pointer; margin-top: 10px; }
            button:hover { background: #00cc52; }
            
            table { width: 100%; border-collapse: collapse; margin-top: 10px; }
            th, td { padding: 15px 10px; text-align: left; border-bottom: 1px solid var(--border); font-size: 0.85rem; }
            th { color: var(--muted); font-size: 0.75rem; text-transform: uppercase; }
            .badge { background: rgba(59, 130, 246, 0.1); color: #3b82f6; padding: 4px 8px; border-radius: 4px; font-size: 0.8rem; }
            .btn-del { background: transparent; border: 1px solid var(--danger); color: var(--danger); padding: 5px 10px; border-radius: 4px; cursor: pointer; }
        </style>
    </head>
    <body>
        <div class="sidebar">
            <div class="logo"><div class="logo-icon">M</div> MARKETPLACE</div>
            <div class="nav active">Dashboard</div>
            <div class="nav">API Keys</div>
            <div class="nav">Analytics</div>
            <a href="/admin" class="logout">Logout</a>
        </div>
        
        <div class="main">
            <div class="header">
                <div>
                    <h1>Good Morning, Admin</h1>
                    <p style="color:var(--muted); font-size:0.9rem; margin-top:5px;">Here's what's happening today</p>
                </div>
                <button onclick="loadData()" style="background:transparent; border:1px solid var(--border); color:white; height:fit-content;">↻ Refresh</button>
            </div>

            <div class="stats-grid">
                <div class="stat-card"><div class="stat-title">TOTAL KEYS <span>🔑</span></div><div class="stat-val" id="st-total">0</div></div>
                <div class="stat-card"><div class="stat-title">ACTIVE KEYS <span>✅</span></div><div class="stat-val" id="st-active">0</div></div>
                <div class="stat-card"><div class="stat-title">TOTAL CALLS <span>📈</span></div><div class="stat-val" id="st-calls">0</div></div>
                <div class="stat-card"><div class="stat-title">TODAY'S CALLS <span>📅</span></div><div class="stat-val" id="st-today">0</div></div>
            </div>

            <div class="card">
                <div class="card-title"><span style="color:var(--primary);">+</span> Create API Key</div>
                <div class="form-group">
                    <label>API Key Name</label>
                    <input type="text" id="name" placeholder="e.g. Shot">
                </div>
                <div class="row">
                    <div class="form-group">
                        <label>Daily Limit</label>
                        <input type="number" id="limit" value="100">
                    </div>
                    <div class="form-group">
                        <label>Expiry (Days)</label>
                        <input type="number" id="days" value="30">
                    </div>
                </div>
                <button onclick="createKey()">🚀 Create Key</button>
            </div>

            <div class="card">
                <div class="card-title">📋 All API Keys</div>
                <table>
                    <thead><tr><th>API KEY</th><th>EXPIRES</th><th>LIMIT</th><th>USED TODAY</th><th>ACTION</th></tr></thead>
                    <tbody id="tbl"></tbody>
                </table>
            </div>
        </div>

        <script>
            const pass = new URLSearchParams(window.location.search).get('password');

            function loadData() {
                fetch(`/admin/get_data?password=${pass}`)
                .then(r => r.json())
                .then(d => {
                    document.getElementById('st-total').innerText = d.stats.total;
                    document.getElementById('st-active').innerText = d.stats.active;
                    document.getElementById('st-calls').innerText = d.stats.calls;
                    document.getElementById('st-today').innerText = d.stats.today;
                    
                    let t = document.getElementById('tbl');
                    t.innerHTML = '';
                    d.keys.forEach(k => {
                        t.innerHTML += `<tr>
                            <td><b>${k.name}</b></td>
                            <td>${new Date(k.expires).toLocaleDateString()}</td>
                            <td>${k.limit}</td>
                            <td><span class="badge">${k.today} hits</span></td>
                            <td><button class="btn-del" onclick="deleteKey('${k.name}')">Delete</button></td>
                        </tr>`;
                    });
                });
            }

            function createKey() {
                let name = document.getElementById('name').value;
                let limit = document.getElementById('limit').value;
                let days = document.getElementById('days').value;
                if(!name) return alert("Enter a name");

                fetch(`/admin/create?name=${name}&limit=${limit}&days=${days}&password=${pass}`, {method:'POST'})
                .then(r => r.json()).then(d => {
                    alert(d.message);
                    document.getElementById('name').value = '';
                    loadData();
                });
            }

            function deleteKey(name) {
                if(!confirm("Delete this key?")) return;
                fetch(`/admin/delete?name=${name}&password=${pass}`, {method:'DELETE'})
                .then(r => r.json()).then(d => {
                    loadData();
                });
            }

            loadData();
        </script>
    </body>
    </html>
    """

# =====================================================================
# 4. API ROUTES FOR DASHBOARD
# =====================================================================
@app.get("/admin/get_data")
def get_data(password: str, db: Session = Depends(get_db)):
    if password != ADMIN_PASSWORD: raise HTTPException(status_code=401)
    today = datetime.date.today()
    keys = db.query(models.APIKey).all()
    logs = db.query(models.APIUsageLog).all()
    
    k_list = []
    for k in keys:
        today_hits = sum(l.hit_count for l in logs if l.api_key_id == k.id and l.usage_date == today)
        k_list.append({"name": k.key_string, "expires": k.expires_at, "limit": k.request_limit, "today": today_hits})
        
    return {
        "stats": {
            "total": len(keys), 
            "active": sum(1 for k in keys if k.is_active and k.expires_at > datetime.datetime.utcnow()), 
            "calls": sum(l.hit_count for l in logs), 
            "today": sum(l.hit_count for l in logs if l.usage_date == today)
        }, 
        "keys": k_list
    }

@app.post("/admin/create")
def create_key(name: str, limit: int, days: int, password: str, db: Session = Depends(get_db)):
    if password != ADMIN_PASSWORD: raise HTTPException(status_code=401)
    if db.query(models.APIKey).filter(models.APIKey.key_string == name).first():
        return {"message": "Key already exists!"}
    db.add(models.APIKey(key_string=name, owner_name=name, expires_at=datetime.datetime.utcnow() + datetime.timedelta(days=days), request_limit=limit))
    db.commit()
    return {"message": f"Key '{name}' created!"}

@app.delete("/admin/delete")
def delete_key(name: str, password: str, db: Session = Depends(get_db)):
    if password != ADMIN_PASSWORD: raise HTTPException(status_code=401)
    key = db.query(models.APIKey).filter(models.APIKey.key_string == name).first()
    if key: db.delete(key); db.commit()
    return {"message": "Deleted"}

@app.get("/")
def home(): return {"status": "Online"}
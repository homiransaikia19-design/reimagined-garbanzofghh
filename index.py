from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import Column, String, func
import datetime
import secrets

import models
from database import engine, SessionLocal, Base

app = FastAPI(title="Professional Phone API", description="API with daily usage tracking")

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
# 1. THE PUBLIC API ENDPOINT (Tracks Daily Usage)
# =====================================================================
@app.get("/api/infonumber")
def get_info_by_number(
    number: str = Query(..., description="The phone number to search"),
    api: str = Query(..., description="Your API Key"),
    db: Session = Depends(get_db)
):
    # A. Verify API Key
    key_record = db.query(models.APIKey).filter(models.APIKey.key_string == api).first()
    if not key_record:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    if not key_record.is_active:
        raise HTTPException(status_code=403, detail="API Key is disabled")
    if key_record.expires_at < datetime.datetime.utcnow():
        raise HTTPException(status_code=403, detail="API Key has expired")

    # B. Track Daily Usage
    today = datetime.date.today()
    usage_record = db.query(models.APIUsageLog).filter(
        models.APIUsageLog.api_key_id == key_record.id,
        models.APIUsageLog.usage_date == today
    ).first()

    if usage_record:
        # Check if they hit the limit for TODAY
        if usage_record.hit_count >= key_record.request_limit:
            raise HTTPException(status_code=429, detail="Daily API Limit Reached")
        usage_record.hit_count += 1
    else:
        # First time using it today
        new_log = models.APIUsageLog(api_key_id=key_record.id, usage_date=today, hit_count=1)
        db.add(new_log)

    db.commit()

    # C. Search Data
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
        <title>API Control Center</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
        <style>
            :root { --bg-color: #0f172a; --panel-bg: rgba(30, 41, 59, 0.7); --border-color: rgba(255, 255, 255, 0.1); --primary: #3b82f6; --text-main: #f8fafc; --text-muted: #94a3b8; --success: #10b981; }
            * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', sans-serif; }
            body { background-color: var(--bg-color); color: var(--text-main); min-height: 100vh; padding: 2rem; }
            .container { max-width: 1100px; margin: 0 auto; display: grid; grid-template-columns: 350px 1fr; gap: 2rem; }
            .panel { background: var(--panel-bg); border: 1px solid var(--border-color); border-radius: 16px; padding: 1.5rem; }
            h1 { font-size: 1.5rem; margin-bottom: 1.5rem; color: #60a5fa; }
            h2 { font-size: 1.1rem; margin-bottom: 1rem; }
            .form-group { margin-bottom: 1rem; }
            label { display: block; font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.5rem; }
            input { width: 100%; padding: 0.75rem; background: rgba(15, 23, 42, 0.6); border: 1px solid var(--border-color); border-radius: 8px; color: white; }
            button { width: 100%; padding: 0.75rem; background: var(--primary); color: white; border: none; border-radius: 8px; font-weight: 600; cursor: pointer; }
            table { width: 100%; border-collapse: collapse; margin-top: 1rem; }
            th, td { padding: 1rem; text-align: left; border-bottom: 1px solid var(--border-color); font-size: 0.85rem; }
            th { color: var(--text-muted); text-transform: uppercase; }
            .badge { padding: 4px 8px; border-radius: 20px; font-size: 0.7rem; background: rgba(16, 185, 129, 0.1); color: var(--success); }
        </style>
    </head>
    <body>
        <div class="container">
            <div>
                <div class="panel">
                    <h1>Create API Key</h1>
                    <div class="form-group">
                        <label>Admin Password</label>
                        <input type="password" id="adminPass" value="admin123">
                    </div>
                    <div class="form-group">
                        <label>Client Name</label>
                        <input type="text" id="clientName" placeholder="e.g., John Doe">
                    </div>
                    <div class="form-group">
                        <label>Daily Limit (Hits)</label>
                        <input type="number" id="limit" value="100">
                    </div>
                    <div class="form-group">
                        <label>Expiry (Days)</label>
                        <input type="number" id="validity" value="30">
                    </div>
                    <button onclick="createKey()">Generate Key</button>
                </div>
            </div>
            <div class="panel">
                <div style="display: flex; justify-content: space-between;">
                    <h2>API Clients & Usage</h2>
                    <button onclick="loadKeys()" style="width: auto; padding: 0.5rem 1rem; background: rgba(255,255,255,0.1);">Refresh</button>
                </div>
                <table id="keysTable">
                    <thead>
                        <tr><th>Client</th><th>API Key</th><th>Expires</th><th>Daily Limit</th><th>Used Today</th></tr>
                    </thead>
                    <tbody></tbody>
                </table>
            </div>
        </div>
        <script>
            async function createKey() {
                const name = document.getElementById('clientName').value;
                const limit = document.getElementById('limit').value;
                const days = document.getElementById('validity').value;
                const pass = document.getElementById('adminPass').value;
                
                const res = await fetch(`/admin/generate_key?owner_name=${name}&request_limit=${limit}&validity_days=${days}&admin_pass=${pass}`, { method: 'POST' });
                const data = await res.json();
                if(res.ok) {
                    alert("API Key Created: " + data.api_key);
                    loadKeys();
                } else { alert("Error: " + data.detail); }
            }

            async function loadKeys() {
                const pass = document.getElementById('adminPass').value;
                const res = await fetch(`/admin/get_keys_with_usage?admin_pass=${pass}`);
                const data = await res.json();
                const tbody = document.querySelector('#keysTable tbody');
                tbody.innerHTML = "";
                
                if(!res.ok) { return; }
                
                data.forEach(item => {
                    const expDate = new Date(item.expires_at).toLocaleDateString();
                    tbody.innerHTML += `
                        <tr>
                            <td><b>${item.owner_name}</b></td>
                            <td style="font-family:monospace; color:#93c5fd;">${item.key_string.substring(0, 12)}...</td>
                            <td>${expDate}</td>
                            <td>${item.request_limit}</td>
                            <td><span class="badge">${item.used_today} hits</span></td>
                        </tr>
                    `;
                });
            }
            window.onload = loadKeys;
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.post("/admin/generate_key")
def generate_key(
    owner_name: str, 
    request_limit: int,
    validity_days: int, 
    admin_pass: str, 
    db: Session = Depends(get_db)
):
    if admin_pass != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Wrong Admin Password")

    new_key = "sk_" + secrets.token_hex(16)
    expires = datetime.datetime.utcnow() + datetime.timedelta(days=validity_days)
    
    db_key = models.APIKey(
        key_string=new_key, 
        owner_name=owner_name, 
        expires_at=expires,
        request_limit=request_limit # Set custom limit
    )
    db.add(db_key)
    db.commit()
    return {"status": "success", "api_key": new_key}

@app.get("/admin/get_keys_with_usage")
def get_keys_with_usage(admin_pass: str, db: Session = Depends(get_db)):
    if admin_pass != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Wrong Admin Password")
    
    today = datetime.date.today()
    keys = db.query(models.APIKey).all()
    results = []
    
    for key in keys:
        # Find how many times this key was used TODAY
        log = db.query(models.APIUsageLog).filter(
            models.APIUsageLog.api_key_id == key.id,
            models.APIUsageLog.usage_date == today
        ).first()
        
        used_today = log.hit_count if log else 0
        
        results.append({
            "owner_name": key.owner_name,
            "key_string": key.key_string,
            "expires_at": key.expires_at,
            "request_limit": key.request_limit,
            "used_today": used_today
        })
        
    return results

@app.get("/")
def home():
    return {"status": "Online", "message": "API is running. Go to /admin."}
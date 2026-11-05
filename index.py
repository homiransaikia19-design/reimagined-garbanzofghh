from fastapi import FastAPI, HTTPException, Query, Header, Depends, Form
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import Column, String
import datetime
import secrets

# Import local modules
import models
from database import engine, SessionLocal, Base

app = FastAPI(title="Phone Info API", description="API for looking up numbers with Admin Control")

# Admin Secret Password
ADMIN_PASSWORD = "admin123"

# Define the PhoneRecord table
class PhoneRecord(Base):
    __tablename__ = "phone_numbers"
    mobile = Column(String(20), primary_key=True, index=True)
    name = Column(String(255))
    address = Column(String(500))
    pincode = Column(String(20))
    city = Column(String(100))

# Dependency to get DB session
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
    number: str = Query(..., description="The phone number to search"),
    x_api_key: str = Header(..., description="Your API Key"),
    db: Session = Depends(get_db)
):
    # A. Verify API Key exists
    key_record = db.query(models.APIKey).filter(models.APIKey.key_string == x_api_key).first()
    if not key_record:
        raise HTTPException(status_code=401, detail="Invalid API Key")
        
    # B. Verify Key is Active and Not Expired
    if not key_record.is_active:
        raise HTTPException(status_code=403, detail="API Key is disabled")
    if key_record.expires_at < datetime.datetime.utcnow():
        raise HTTPException(status_code=403, detail="API Key has expired")

    # C. Track Traffic
    key_record.total_requests += 1
    db.commit()

    # D. Search Data
    record = db.query(PhoneRecord).filter(PhoneRecord.mobile == number).first()

    # E. Return the result
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

    raise HTTPException(status_code=404, detail="Number not found in database")


# =====================================================================
# 2. THE ADMIN PANEL (HTML WRITTEN DIRECTLY IN PYTHON)
# =====================================================================
@app.get("/admin", response_class=HTMLResponse)
def admin_panel():
    # This HTML string contains your dashboard
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>API Control Center</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
        <style>
            :root {
                --bg-color: #0f172a; --panel-bg: rgba(30, 41, 59, 0.7); --border-color: rgba(255, 255, 255, 0.1);
                --primary: #3b82f6; --primary-hover: #2563eb; --text-main: #f8fafc; --text-muted: #94a3b8;
                --success: #10b981; --danger: #ef4444;
            }
            * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', sans-serif; }
            body { background-color: var(--bg-color); background-image: radial-gradient(at 0% 0%, rgba(59, 130, 246, 0.15) 0px, transparent 50%), radial-gradient(at 100% 100%, rgba(16, 185, 129, 0.1) 0px, transparent 50%); color: var(--text-main); min-height: 100vh; padding: 2rem; }
            .container { max-width: 1000px; margin: 0 auto; display: grid; grid-template-columns: 350px 1fr; gap: 2rem; }
            .panel { background: var(--panel-bg); backdrop-filter: blur(12px); border: 1px solid var(--border-color); border-radius: 16px; padding: 1.5rem; box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.5); }
            h1 { font-size: 1.5rem; font-weight: 700; margin-bottom: 1.5rem; background: linear-gradient(to right, #60a5fa, #a78bfa); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
            h2 { font-size: 1.1rem; font-weight: 600; margin-bottom: 1rem; }
            .form-group { margin-bottom: 1rem; }
            label { display: block; font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.5rem; }
            input { width: 100%; padding: 0.75rem; background: rgba(15, 23, 42, 0.6); border: 1px solid var(--border-color); border-radius: 8px; color: var(--text-main); }
            input:focus { outline: none; border-color: var(--primary); }
            button { width: 100%; padding: 0.75rem; background: var(--primary); color: white; border: none; border-radius: 8px; font-weight: 600; cursor: pointer; }
            button:hover { background: var(--primary-hover); }
            .endpoint-box { background: #ffffff; color: #1e293b; padding: 1rem; border-radius: 8px; margin-bottom: 1rem; font-family: monospace; font-size: 0.85rem; }
            .endpoint-method { display: inline-block; background: #10b981; color: white; padding: 2px 6px; border-radius: 4px; font-size: 0.7rem; font-weight: bold; margin-right: 8px; }
            table { width: 100%; border-collapse: collapse; margin-top: 1rem; }
            th, td { padding: 1rem; text-align: left; border-bottom: 1px solid var(--border-color); font-size: 0.9rem; }
            th { color: var(--text-muted); font-size: 0.75rem; text-transform: uppercase; }
            .status-badge { padding: 4px 8px; border-radius: 20px; font-size: 0.75rem; font-weight: 600; }
            .status-active { background: rgba(16, 185, 129, 0.1); color: var(--success); }
            .status-expired { background: rgba(239, 68, 68, 0.1); color: var(--danger); }
        </style>
    </head>
    <body>
        <div class="container">
            <div>
                <div class="panel" style="margin-bottom: 2rem;">
                    <h1>API Control</h1>
                    <div class="form-group">
                        <label>Admin Password</label>
                        <input type="password" id="adminPass" value="admin123">
                    </div>
                    <h2 style="margin-top: 2rem;">Create API Key</h2>
                    <div class="form-group">
                        <label>Client Name</label>
                        <input type="text" id="clientName" placeholder="e.g., Mobile App">
                    </div>
                    <div class="form-group">
                        <label>Validity (Days)</label>
                        <input type="number" id="validity" value="30">
                    </div>
                    <button onclick="createKey()">Generate Key</button>
                </div>
                <div class="panel">
                    <h2>API Endpoints</h2>
                    <div class="endpoint-box">
                        <div><span class="endpoint-method">GET</span><span style="font-weight:bold;">/api/infonumber</span></div>
                        <div style="margin-top:8px; color:#64748b; font-family:Arial; font-size:0.8rem;">
                            Query Params: <b>?number=XXXX</b><br>
                            Headers: <b>x-api-key: YOUR_KEY</b>
                        </div>
                    </div>
                </div>
            </div>
            <div class="panel">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <h2>API Usage & Traffic</h2>
                    <button onclick="loadKeys()" style="width: auto; padding: 0.5rem 1rem; background: rgba(255,255,255,0.1);">Refresh</button>
                </div>
                <table id="keysTable">
                    <thead>
                        <tr><th>Client</th><th>API Key</th><th>Expires</th><th>Status</th><th>Traffic</th></tr>
                    </thead>
                    <tbody></tbody>
                </table>
            </div>
        </div>
        <script>
            async function createKey() {
                const name = document.getElementById('clientName').value;
                const days = document.getElementById('validity').value;
                const pass = document.getElementById('adminPass').value;
                if(!name) { alert("Enter a name"); return; }
                
                const res = await fetch(`/admin/generate_key?owner_name=${name}&validity_days=${days}&admin_pass=${pass}`, { method: 'POST' });
                const data = await res.json();
                if(res.ok) {
                    alert("API Key Created: " + data.api_key);
                    loadKeys();
                } else { alert("Error: " + data.detail); }
            }

            async function loadKeys() {
                const pass = document.getElementById('adminPass').value;
                const res = await fetch(`/admin/get_keys?admin_pass=${pass}`);
                const data = await res.json();
                const tbody = document.querySelector('#keysTable tbody');
                tbody.innerHTML = "";
                
                if(!res.ok) { return; }
                
                data.forEach(key => {
                    const isExpired = new Date(key.expires_at) < new Date();
                    const statusHTML = (key.is_active && !isExpired) ? `<span class="status-badge status-active">Active</span>` : `<span class="status-badge status-expired">Expired</span>`;
                    const expDate = new Date(key.expires_at).toLocaleDateString();
                    
                    tbody.innerHTML += `
                        <tr>
                            <td><b>${key.owner_name}</b></td>
                            <td style="font-family:monospace; color:#93c5fd;">${key.key_string.substring(0, 10)}...</td>
                            <td>${expDate}</td>
                            <td>${statusHTML}</td>
                            <td style="font-weight:bold; color:var(--primary);">${key.total_requests}</td>
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
        expires_at=expires
    )
    db.add(db_key)
    db.commit()
    
    return {"status": "success", "api_key": new_key, "expires_at": expires}


@app.get("/admin/get_keys")
def get_all_keys(admin_pass: str, db: Session = Depends(get_db)):
    if admin_pass != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Wrong Admin Password")
    
    return db.query(models.APIKey).all()


@app.get("/")
def home():
    return {"status": "Online", "message": "API is running. Go to /admin for the dashboard."}
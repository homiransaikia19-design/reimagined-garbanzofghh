from fastapi import FastAPI, HTTPException, Query, Depends, Form, Cookie, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
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

# ✅ Tell Python to look for the templates folder
templates = Jinja2Templates(directory="templates")

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
# 2. THE ADMIN PANEL
# =====================================================================
@app.get("/admin", response_class=HTMLResponse)
def admin_panel(request: Request, admin_session: str = Cookie(None)):
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
    
    return templates.TemplateResponse("admin.html", {"request": request})

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
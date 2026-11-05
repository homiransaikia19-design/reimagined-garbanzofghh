from fastapi import FastAPI, HTTPException, Query, Header, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import Column, String
import datetime
import secrets

# Import local modules
import models
from database import engine, SessionLocal, Base

app = FastAPI(title="Phone Info API", description="API for looking up numbers with Admin Control")

# ✅ FIXED: Look inside your 'templates' folder
templates = Jinja2Templates(directory="templates")

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
# 2. THE ADMIN PANEL ENDPOINTS
# =====================================================================
@app.get("/admin", response_class=HTMLResponse)
def admin_panel(request: Request):
    return templates.TemplateResponse("admin.html", {"request": request})


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
    
    return {
        "status": "success", 
        "api_key": new_key, 
        "expires_at": expires
    }


@app.get("/admin/get_keys")
def get_all_keys(admin_pass: str, db: Session = Depends(get_db)):
    if admin_pass != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Wrong Admin Password")
    
    keys = db.query(models.APIKey).all()
    return keys


# =====================================================================
# 3. HOME ROUTE
# =====================================================================
@app.get("/")
def home():
    return {
        "status": "Online",
        "message": "API is running. Go to /admin for the dashboard."
    }
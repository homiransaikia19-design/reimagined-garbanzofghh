from database import SessionLocal
from sqlalchemy import Column, String
from database import Base

# Define the table so the script knows what to look for
class PhoneRecord(Base):
    __tablename__ = "phone_numbers"
    mobile = Column(String(20), primary_key=True, index=True)
    name = Column(String(255))
    address = Column(String(500))
    pincode = Column(String(20))
    city = Column(String(100))

def search_number():
    # Ask you for the number in the terminal
    search_input = input("Enter the phone number to search (or type 'exit'): ")
    
    if search_input.lower() == 'exit':
        return

    db = SessionLocal()
    
    # Search the Neon Database
    record = db.query(PhoneRecord).filter(PhoneRecord.mobile == search_input).first()
    
    if record:
        print("\n✅ FOUND IT!")
        print(f"📱 Mobile: {record.mobile}")
        print(f"👤 Name:   {record.name}")
        print(f"🏠 Address: {record.address}")
        print(f"📍 City:   {record.city}")
    else:
        print("\n❌ Number not found in the database.")
        
    db.close()
    print("-" * 30)
    search_number() # Ask again

# Start the program
if __name__ == "__main__":
    search_number()
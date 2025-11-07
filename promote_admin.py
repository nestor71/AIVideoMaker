#!/usr/bin/env python3
"""Script temporaneo per promuovere utente a admin"""
from app.core.database import SessionLocal
from app.models.user import User

db = SessionLocal()

user = db.query(User).filter(User.email == "admin@test.com").first()
if user:
    user.is_admin = True
    db.commit()
    print(f"✅ Utente {user.username} promosso a admin!")
else:
    print("❌ Utente non trovato")

db.close()

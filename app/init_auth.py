import os
from sqlalchemy import text
from app.database import engine, SessionLocal
from app.auth import hash_password


def initialize_auth():
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS app_users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(100) NOT NULL UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                role VARCHAR(20) NOT NULL DEFAULT 'viewer',
                approved BOOLEAN NOT NULL DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))

    username = os.getenv("ADMIN_USERNAME")
    password = os.getenv("ADMIN_PASSWORD")

    if not username or not password:
        raise RuntimeError("Set ADMIN_USERNAME and ADMIN_PASSWORD in .env")

    db = SessionLocal()
    try:
        existing = db.execute(
            text("SELECT id FROM app_users WHERE username=:u"),
            {"u": username}
        ).first()

        if not existing:
            db.execute(
                text("""
                    INSERT INTO app_users
                    (username, password_hash, role, approved)
                    VALUES (:u, :p, 'admin', 1)
                """),
                {"u": username, "p": hash_password(password)}
            )
            db.commit()
    finally:
        db.close()
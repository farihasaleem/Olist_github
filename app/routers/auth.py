import os

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.database import get_db
from app.auth import (
    hash_password,
    verify_password,
    create_token,
    get_current_user,
    require_admin
)

router = APIRouter()


class RegisterData(BaseModel):
    username: str
    password: str


class LoginData(BaseModel):
    username: str
    password: str


@router.post("/register")
def register(data: RegisterData, db: Session = Depends(get_db)):
    username = data.username.strip()

    if len(username) < 3 or len(data.password) < 8:
        raise HTTPException(400, "Username must be 3+ characters and password 8+ characters")

    existing = db.execute(
        text("SELECT username FROM app_users WHERE username=:u"),
        {"u": username}
    ).first()

    if existing:
        raise HTTPException(400, "Username already exists")

    db.execute(
        text("""
            INSERT INTO app_users (username, password_hash, role, approved)
            VALUES (:u, :p, 'viewer', 0)
        """),
        {"u": username, "p": hash_password(data.password)}
    )
    db.commit()

    return {"message": "Registration submitted. Wait for admin approval."}


@router.post("/login")
def login(data: LoginData, db: Session = Depends(get_db)):
    user = db.execute(
        text("""
            SELECT username, password_hash, role, approved
            FROM app_users
            WHERE username=:u
        """),
        {"u": data.username.strip()}
    ).mappings().first()

    if not user or not verify_password(data.password, user["password_hash"]):
        raise HTTPException(401, "Incorrect username or password")

    if not user["approved"]:
        raise HTTPException(403, "Your account is awaiting admin approval")

    token = create_token(user["username"], user["role"])

    return {
        "access_token": token,
        "token_type": "bearer",
        "username": user["username"],
        "role": user["role"]
    }


@router.get("/me")
def me(user=Depends(get_current_user)):
    return user


@router.get("/pending-users")
def pending_users(
    db: Session = Depends(get_db),
    admin=Depends(require_admin)
):
    rows = db.execute(
        text("""
            SELECT username
            FROM app_users
            WHERE approved=0
            ORDER BY username
        """)
    ).mappings().all()

    return {"users": [dict(row) for row in rows]}


@router.post("/approve/{username}")
def approve_user(
    username: str,
    db: Session = Depends(get_db),
    admin=Depends(require_admin)
):
    result = db.execute(
        text("""
            UPDATE app_users
            SET approved=1
            WHERE username=:u AND role='viewer'
        """),
        {"u": username}
    )
    db.commit()

    if result.rowcount == 0:
        raise HTTPException(404, "Pending user not found")

    return {"message": "User approved"}


@router.delete("/reject/{username}")
def reject_user(
    username: str,
    db: Session = Depends(get_db),
    admin=Depends(require_admin)
):
    result = db.execute(
        text("""
            DELETE FROM app_users
            WHERE username=:u AND role='viewer' AND approved=0
        """),
        {"u": username}
    )
    db.commit()

    if result.rowcount == 0:
        raise HTTPException(404, "Pending user not found")

    return {"message": "Registration rejected"}
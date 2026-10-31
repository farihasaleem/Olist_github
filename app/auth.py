import os
import time
import json
import hmac
import hashlib
import secrets
import base64

from fastapi import HTTPException, Header, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.database import get_db


SECRET_KEY = os.getenv("AUTH_SECRET_KEY", "temporary-development-secret-change-before-deploy")
TOKEN_HOURS = 12


def hash_password(password):
    salt = secrets.token_bytes(16)
    hashed = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt, 200000
    )
    return (
        base64.b64encode(salt).decode() + "$" +
        base64.b64encode(hashed).decode()
    )


def verify_password(password, stored):
    try:
        salt_text, hash_text = stored.split("$")
        salt = base64.b64decode(salt_text)
        expected = base64.b64decode(hash_text)

        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), salt, 200000
        )
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False


def create_token(username, role):
    payload = {
        "username": username,
        "role": role,
        "expires": int(time.time()) + TOKEN_HOURS * 3600
    }

    data = base64.urlsafe_b64encode(
        json.dumps(payload).encode()
    ).decode().rstrip("=")

    signature = hmac.new(
        SECRET_KEY.encode(), data.encode(), hashlib.sha256
    ).hexdigest()

    return data + "." + signature


def verify_token(token):
    try:
        data, signature = token.split(".")

        expected = hmac.new(
            SECRET_KEY.encode(), data.encode(), hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(signature, expected):
            return None

        payload = json.loads(
            base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))
        )

        if payload["expires"] < time.time():
            return None

        return payload
    except Exception:
        return None


def get_current_user(
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Please log in")

    payload = verify_token(authorization[7:])

    if not payload:
        raise HTTPException(401, "Invalid or expired login")

    user = db.execute(
        text("""
            SELECT username, role, approved
            FROM app_users
            WHERE username = :username
        """),
        {"username": payload["username"]}
    ).mappings().first()

    if not user or not user["approved"]:
        raise HTTPException(403, "Account not approved")

    if user["role"] != payload["role"]:
        raise HTTPException(403, "Account permissions changed. Log in again.")

    return dict(user)


def require_admin(user: dict = Depends(get_current_user)):
    if user["role"] != "admin":
        raise HTTPException(403, "Admin permission required")

    return user
import os
from fastapi import HTTPException
from msal import ConfidentialClientApplication
from typing import Optional
import jwt
from datetime import datetime, timedelta
from .database import SessionLocal
from .models import User

CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")
TENANT_ID = os.getenv("AZURE_TENANT_ID", "common")
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")

AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
# include openid to receive id_token
SCOPES = ["openid", "profile", "User.Read"]


def _build_msal_app(cache=None):
    return ConfidentialClientApplication(
        CLIENT_ID, authority=AUTHORITY, client_credential=CLIENT_SECRET, token_cache=cache
    )


def get_login_url(state: Optional[str] = None) -> str:
    app = _build_msal_app()
    extra = {"prompt": "select_account"}
    return app.get_authorization_request_url(scopes=SCOPES, redirect_uri=f"{BASE_URL}/auth/callback", state=state, **{"extra_query_parameters": extra})


def exchange_code_for_token(code: str) -> dict:
    app = _build_msal_app()
    result = app.acquire_token_by_authorization_code(code, scopes=SCOPES, redirect_uri=f"{BASE_URL}/auth/callback")
    if not result or "error" in result:
        raise HTTPException(status_code=400, detail=result.get("error_description") or result.get("error") if result else "token exchange failed")
    return result


def create_jwt_for_user(user: dict) -> str:
    payload = {
        "sub": user.get("username"),
        "name": user.get("display_name"),
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(hours=8),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def verify_jwt_token(token: str) -> dict:
    try:
        data = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return data
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")


def get_or_create_user_from_ms_token(ms_token: dict):
    # ms_token contains id_token_claims when openid/profile included
    claims = ms_token.get("id_token_claims") or ms_token.get("id_token_claims") or {}
    username = claims.get("preferred_username") or claims.get("upn") or claims.get("email")
    name = claims.get("name") or username
    if not username:
        # fallback to account username if present
        acct = ms_token.get("account") or {}
        username = acct.get("username") or acct.get("home_account_id")

    db = SessionLocal()
    user = db.query(User).filter(User.username == username).first()
    if not user:
        user = User(username=username, display_name=name, is_admin=False)
        db.add(user)
        db.commit()
        db.refresh(user)
    db.close()
    return user


def get_logout_url(post_logout_redirect: Optional[str] = None) -> str:
    # Azure logout endpoint
    url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/logout"
    if post_logout_redirect:
        url += f"?post_logout_redirect_uri={post_logout_redirect}"
    return url


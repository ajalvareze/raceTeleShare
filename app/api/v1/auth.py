import re
from datetime import datetime, timedelta, timezone

from authlib.integrations.httpx_client import AsyncOAuth2Client
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from itsdangerous import URLSafeTimedSerializer, BadSignature
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.security import (
    create_access_token, create_admin_token,
    generate_refresh_token, hash_refresh_token,
    hash_password, verify_password, generate_oauth_state,
)
from app.database import get_db
from app.models.oauth_account import OAuthAccount
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.user import Token, UserCreate, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()
_signer = URLSafeTimedSerializer(settings.secret_key)

OAUTH_PROVIDERS = {
    "google": {
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "userinfo_url": "https://www.googleapis.com/oauth2/v3/userinfo",
        "scope": "openid email profile",
        "client_id": lambda: settings.google_client_id,
        "client_secret": lambda: settings.google_client_secret,
    },
    "github": {
        "authorize_url": "https://github.com/login/oauth/authorize",
        "token_url": "https://github.com/login/oauth/access_token",
        "userinfo_url": "https://api.github.com/user",
        "scope": "read:user user:email",
        "client_id": lambda: settings.github_client_id,
        "client_secret": lambda: settings.github_client_secret,
    },
}

# ── Local auth ──────────────────────────────────────────────────────────────

@router.post("/register", response_model=UserOut, status_code=201)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status_code=400, detail="Username already taken")
    user = User(
        username=payload.username,
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(response: Response, form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form.username).first()
    _check_lockout(user)
    if not user or not user.hashed_password or not verify_password(form.password, user.hashed_password):
        _record_failed_attempt(db, user)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    _reset_failed_attempts(db, user)
    access_token = create_access_token(user.id)
    refresh = _issue_refresh_token(db, user)
    response.set_cookie("refresh_token", refresh, httponly=True, secure=False, samesite="lax",
                        max_age=settings.refresh_token_expire_days * 86400)
    return Token(access_token=access_token)


@router.post("/refresh", response_model=Token)
def refresh_access_token(request: Request, db: Session = Depends(get_db)):
    raw = request.cookies.get("refresh_token")
    if not raw:
        raise HTTPException(status_code=401, detail="No refresh token")
    token_hash = hash_refresh_token(raw)
    rt = db.query(RefreshToken).filter(
        RefreshToken.token_hash == token_hash,
        RefreshToken.revoked == False,  # noqa: E712
        RefreshToken.expires_at > datetime.now(timezone.utc),
    ).first()
    if not rt:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    return Token(access_token=create_access_token(rt.user_id))


@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    raw = request.cookies.get("refresh_token")
    if raw:
        token_hash = hash_refresh_token(raw)
        rt = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()
        if rt:
            rt.revoked = True
            db.commit()
    response.delete_cookie("refresh_token")
    return {"ok": True}


# ── Admin-only login ────────────────────────────────────────────────────────

@router.post("/admin/login", response_model=Token)
def admin_login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form.username).first()
    _check_lockout(user)
    if (not user or not user.hashed_password
            or not verify_password(form.password, user.hashed_password)
            or not user.is_superuser):
        _record_failed_attempt(db, user)
        raise HTTPException(status_code=403, detail="Admin access denied")
    _reset_failed_attempts(db, user)
    return Token(access_token=create_admin_token(user.id))


# ── OAuth ───────────────────────────────────────────────────────────────────

@router.get("/oauth/{provider}")
def oauth_start(provider: str, response: Response):
    cfg = _get_provider(provider)
    state = generate_oauth_state()
    signed_state = _signer.dumps(state)
    redirect_uri = f"{settings.oauth_redirect_base_url}/api/v1/auth/oauth/{provider}/callback"
    client = AsyncOAuth2Client(client_id=cfg["client_id"](), scope=cfg["scope"])
    url, _ = client.create_authorization_url(cfg["authorize_url"], state=signed_state, redirect_uri=redirect_uri)
    resp = RedirectResponse(url)
    resp.set_cookie("oauth_state", signed_state, httponly=True, max_age=600)
    return resp


@router.get("/oauth/{provider}/callback", response_class=HTMLResponse)
async def oauth_callback(provider: str, request: Request, response: Response, db: Session = Depends(get_db)):
    cfg = _get_provider(provider)
    stored_state = request.cookies.get("oauth_state", "")
    returned_state = request.query_params.get("state", "")
    try:
        _signer.loads(returned_state, max_age=600)
        if stored_state != returned_state:
            raise ValueError("state mismatch")
    except (BadSignature, ValueError):
        raise HTTPException(status_code=400, detail="Invalid OAuth state")

    redirect_uri = f"{settings.oauth_redirect_base_url}/api/v1/auth/oauth/{provider}/callback"
    async with AsyncOAuth2Client(
        client_id=cfg["client_id"](),
        client_secret=cfg["client_secret"](),
    ) as client:
        token_data = await client.fetch_token(cfg["token_url"], authorization_response=str(request.url),
                                              redirect_uri=redirect_uri)
        userinfo_resp = await client.get(cfg["userinfo_url"])
        userinfo = userinfo_resp.json()

    provider_user_id = str(userinfo.get("sub") or userinfo.get("id"))
    provider_email = userinfo.get("email") or ""
    provider_name = userinfo.get("name") or userinfo.get("login") or ""

    # Find or create user
    oauth_acc = db.query(OAuthAccount).filter_by(provider=provider, provider_user_id=provider_user_id).first()
    if oauth_acc:
        user = db.get(User, oauth_acc.user_id)
    else:
        user = db.query(User).filter(User.email == provider_email).first()
        if not user:
            username = _make_username(db, provider_name or provider_email.split("@")[0])
            user = User(username=username, email=provider_email, full_name=provider_name)
            db.add(user)
            db.flush()
        db.add(OAuthAccount(user_id=user.id, provider=provider,
                            provider_user_id=provider_user_id, provider_email=provider_email))
        db.commit()

    if not user.is_active:
        raise HTTPException(status_code=400, detail="Account disabled")
    if user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin accounts must use password login")

    access_token = create_access_token(user.id, auth_method="oauth")
    refresh = _issue_refresh_token(db, user)
    html = f"""<!doctype html><html><head><title>Logging in…</title></head><body>
<script>
  localStorage.setItem('access_token', '{access_token}');
  document.cookie = 'refresh_token={refresh}; path=/; max-age={settings.refresh_token_expire_days * 86400}; samesite=lax';
  window.location.replace('/laps');
</script></body></html>"""
    resp = HTMLResponse(html)
    resp.delete_cookie("oauth_state")
    return resp


# ── Helpers ─────────────────────────────────────────────────────────────────

def _get_provider(provider: str) -> dict:
    if provider not in OAUTH_PROVIDERS:
        raise HTTPException(status_code=404, detail=f"Unknown provider: {provider}")
    return OAUTH_PROVIDERS[provider]


def _issue_refresh_token(db: Session, user: User) -> str:
    raw = generate_refresh_token()
    expires = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    db.add(RefreshToken(user_id=user.id, token_hash=hash_refresh_token(raw), expires_at=expires))
    db.commit()
    return raw


def _check_lockout(user: User | None):
    if user and user.locked_until and user.locked_until > datetime.now(timezone.utc):
        raise HTTPException(status_code=429, detail="Account temporarily locked. Try again later.")


def _record_failed_attempt(db: Session, user: User | None):
    if not user:
        return
    user.failed_login_attempts += 1
    if user.failed_login_attempts >= 5:
        user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)
    db.commit()


def _reset_failed_attempts(db: Session, user: User):
    user.failed_login_attempts = 0
    user.locked_until = None
    db.commit()


def _make_username(db: Session, base: str) -> str:
    slug = re.sub(r"[^a-z0-9_]", "", base.lower())[:50] or "user"
    candidate = slug
    i = 1
    while db.query(User).filter(User.username == candidate).first():
        candidate = f"{slug}{i}"
        i += 1
    return candidate

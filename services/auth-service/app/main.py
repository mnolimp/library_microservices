from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import secrets
import httpx
import os
from datetime import datetime, timezone, timedelta

from app.database import get_db
from app.models import AuthUser, OAuthState
from app.schemas import RegisterRequest, LoginRequest, TokenResponse, UserProfile
from app.jwt import create_access_token, get_current_user

from passlib.context import CryptContext

app = FastAPI(
    title="Auth Service",
    description="Аутентификация и авторизация",
    version="1.0.0",
    redirect_slashes=False,
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID", "")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET", "")
GITHUB_REDIRECT_URI = os.getenv("GITHUB_REDIRECT_URI", "http://localhost:8080/auth/oauth/github/callback")

# ──────────────────────────────────────────────
# Health
# ──────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok"}


# ──────────────────────────────────────────────
# Регистрация
# ──────────────────────────────────────────────

@app.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AuthUser).where(AuthUser.email == body.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = AuthUser(
        email=body.email,
        hashed_password=pwd_context.hash(body.password),
        full_name=body.full_name,
        role="user",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token(user.id, user.email, user.role)
    return TokenResponse(access_token=token)


# ──────────────────────────────────────────────
# Вход
# ──────────────────────────────────────────────

@app.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AuthUser).where(AuthUser.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not user.hashed_password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not pwd_context.verify(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User is inactive")

    token = create_access_token(user.id, user.email, user.role)
    return TokenResponse(access_token=token)


# ──────────────────────────────────────────────
# Профиль
# ──────────────────────────────────────────────

@app.get("/me", response_model=UserProfile)
async def me(current: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AuthUser).where(AuthUser.id == int(current["sub"])))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# ──────────────────────────────────────────────
# GitHub OAuth
# ──────────────────────────────────────────────

@app.get("/oauth/github/login")
async def github_login(db: AsyncSession = Depends(get_db)):
    import logging
    logger = logging.getLogger("uvicorn.error")
    state = secrets.token_urlsafe(32)
    db.add(OAuthState(state=state))
    await db.commit()
    logger.warning(f"[login] saved state={state!r}")

    url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={GITHUB_CLIENT_ID}"
        f"&redirect_uri={GITHUB_REDIRECT_URI}"
        f"&scope=user:email"
        f"&state={state}"
    )
    return RedirectResponse(url)


@app.get("/oauth/github/callback")
async def github_callback(code: str, state: str, db: AsyncSession = Depends(get_db)):
    import logging
    logger = logging.getLogger("uvicorn.error")
    logger.warning(f"[callback] received state={state!r}")

    # Проверяем все state в БД для дебага
    all_states = await db.execute(select(OAuthState))
    all_rows = all_states.scalars().all()
    logger.warning(f"[callback] states in DB: {[r.state for r in all_rows]}")

    # Проверяем state
    result = await db.execute(select(OAuthState).where(OAuthState.state == state))
    state_row = result.scalar_one_or_none()
    if not state_row:
        raise HTTPException(status_code=400, detail="Invalid OAuth state")

    # Удаляем использованный state
    await db.delete(state_row)
    await db.commit()

    async with httpx.AsyncClient() as client:
        # Обмен code → access_token
        token_resp = await client.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json"},
            json={
                "client_id": GITHUB_CLIENT_ID,
                "client_secret": GITHUB_CLIENT_SECRET,
                "code": code,
                "redirect_uri": GITHUB_REDIRECT_URI,
            },
        )
        token_data = token_resp.json()
        github_token = token_data.get("access_token")
        if not github_token:
            raise HTTPException(status_code=400, detail="Failed to obtain GitHub token")

        # Запрос профиля
        profile_resp = await client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {github_token}", "Accept": "application/json"},
        )
        profile = profile_resp.json()

        # Запрос email (может быть скрыт в профиле)
        email = profile.get("email")
        if not email:
            emails_resp = await client.get(
                "https://api.github.com/user/emails",
                headers={"Authorization": f"Bearer {github_token}", "Accept": "application/json"},
            )
            emails = emails_resp.json()
            primary = next((e for e in emails if e.get("primary") and e.get("verified")), None)
            email = primary["email"] if primary else None

        if not email:
            raise HTTPException(status_code=400, detail="Cannot obtain email from GitHub")

    github_id = str(profile["id"])

    # Ищем существующего пользователя
    result = await db.execute(select(AuthUser).where(AuthUser.github_id == github_id))
    user = result.scalar_one_or_none()

    if not user:
        result = await db.execute(select(AuthUser).where(AuthUser.email == email))
        user = result.scalar_one_or_none()

    if user:
        user.github_id = github_id
    else:
        user = AuthUser(
            email=email,
            full_name=profile.get("name") or profile.get("login"),
            github_id=github_id,
            role="user",
        )
        db.add(user)

    await db.commit()
    await db.refresh(user)

    token = create_access_token(user.id, user.email, user.role)
    return HTMLResponse(
        content=f"""
        <html><body>
        <h2>Авторизация успешна</h2>
        <p>Ваш JWT токен:</p>
        <pre>{token}</pre>
        </body></html>
        """
    )

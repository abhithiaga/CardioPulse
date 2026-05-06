import bcrypt
import jwt
from datetime import datetime, timedelta
from typing import Optional
from app.config import settings

JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 12


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_jwt(payload: dict, expires_hours: int = JWT_EXPIRY_HOURS) -> str:
    data = payload.copy()
    data["exp"] = datetime.utcnow() + timedelta(hours=expires_hours)
    return jwt.encode(data, settings.SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_jwt(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


def risk_color(risk_level: str) -> str:
    return {
        "low": "#22c55e",
        "medium": "#f59e0b",
        "high": "#ef4444",
        "critical": "#7c3aed",
    }.get(risk_level, "#6b7280")


def risk_label(score: float) -> str:
    if score >= 0.80: return "CRITICAL"
    if score >= 0.75: return "HIGH"
    if score >= 0.45: return "MEDIUM"
    return "LOW"


def format_ms(ms: Optional[float]) -> str:
    if ms is None: return "—"
    return f"{ms:.0f} ms"


def format_mv(mv: Optional[float]) -> str:
    if mv is None: return "—"
    return f"{mv:+.3f} mV"

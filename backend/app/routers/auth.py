from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from app.utils.helpers import hash_password, verify_password, create_jwt, decode_jwt
import uuid

router = APIRouter()
security = HTTPBearer()

_users: dict = {
    "dr.chen@cardioai.health": {
        "id": "usr-001",
        "email": "dr.chen@cardioai.health",
        "full_name": "Dr. Sarah Chen",
        "role": "cardiologist",
        "hashed_password": hash_password("demo1234"),
    },
    "dr.webb@cardioai.health": {
        "id": "usr-002",
        "email": "dr.webb@cardioai.health",
        "full_name": "Dr. Marcus Webb",
        "role": "cardiologist",
        "hashed_password": hash_password("demo1234"),
    },
}


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: str = "clinician"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    full_name: str
    role: str


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest):
    user = _users.get(payload.email.lower())
    if not user or not verify_password(payload.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_jwt({"sub": user["id"], "email": payload.email, "role": user["role"]})
    return TokenResponse(
        access_token=token, user_id=user["id"],
        full_name=user["full_name"], role=user["role"]
    )


@router.post("/register", response_model=TokenResponse)
async def register(payload: RegisterRequest):
    if payload.email.lower() in _users:
        raise HTTPException(status_code=400, detail="Email already registered")
    user_id = f"usr-{str(uuid.uuid4())[:6]}"
    hashed = hash_password(payload.password)
    _users[payload.email.lower()] = {
        "id": user_id, "email": payload.email,
        "full_name": payload.full_name, "role": payload.role,
        "hashed_password": hashed,
    }
    token = create_jwt({"sub": user_id, "email": payload.email, "role": payload.role})
    return TokenResponse(access_token=token, user_id=user_id, full_name=payload.full_name, role=payload.role)


@router.get("/me")
async def me(credentials: HTTPAuthorizationCredentials = Depends(security)):
    payload = decode_jwt(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return payload

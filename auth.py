import os
from datetime import datetime, timedelta
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from database import get_db
from models import User

# ==============================
# JWT + Password Hash Setup
# ==============================
SECRET_KEY = os.getenv("SECRET_KEY", "tartan_secret_key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

router = APIRouter(prefix="/auth", tags=["Authentication"])

# ==============================
# Utility Functions
# ==============================

def hash_pw(p: str) -> str:
    """Hash password with bcrypt (truncating to 72 bytes if too long)."""
    if len(p.encode("utf-8")) > 72:
        p = p[:72]
    return pwd_ctx.hash(p)


def verify_pw(p: str, hashed: str) -> bool:
    """Verify password against stored hash."""
    return pwd_ctx.verify(p, hashed)


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    """Generate JWT access token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Retrieve current user from JWT token."""
    credentials_exception = HTTPException(status_code=401, detail="Invalid authentication credentials")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    return user


# ==============================
# Request Models
# ==============================

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    id: int
    email: EmailStr
    callsign: str | None = None


# ==============================
# Routes
# ==============================

@router.post("/register", response_model=AuthResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new pilot."""
    # Check existing user
    if db.query(User).filter(User.email == payload.email.lower()).first():
        raise HTTPException(status_code=400, detail="User already exists")

    # Generate callsign (TAD0001, TAD0002, etc.)
    user_count = db.query(User).count() + 1
    callsign = f"TAD{user_count:04d}"

    # Create user
    user = User(
        email=payload.email.lower(),
        password_hash=hash_pw(payload.password),
        callsign=callsign
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return user


@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """Login pilot and return JWT token."""
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user or not verify_pw(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token({"sub": user.email})
    return {"access_token": token, "token_type": "bearer"}

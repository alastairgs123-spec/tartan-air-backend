from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta
from typing import Optional

from database import get_db
from models import User
from schemas import RegisterIn, LoginIn, TokenOut, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = "dev-secret-change-me"  # override with ENV in prod
ALGORITHM = "HS256"
ACCESS_MIN = 60 * 24  # 24h

def hash_pw(p: str) -> str:
    return pwd_ctx.hash(p)

def verify_pw(p: str, h: str) -> bool:
    return pwd_ctx.verify(p, h)

def create_token(user_id: int) -> str:
    payload = {
        "sub": str(user_id),
        "exp": datetime.utcnow() + timedelta(minutes=ACCESS_MIN)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(db: Session = Depends(get_db), token: str = Depends(lambda: None)):
    from fastapi import Request
    # Extract from Authorization: Bearer
    def _extract_token(req: Request) -> Optional[str]:
        auth = req.headers.get("Authorization")
        if not auth or not auth.lower().startswith("bearer "):
            return None
        return auth.split(" ", 1)[1]
    req = router.dependency_overrides_context.request  # FastAPI internal
    # Fallback: create a tiny dependency that reads current request
    # Simpler approach:
    from fastapi import Request
    request: Request = router.dependency_overrides.get(Request, None) or None
    # safer approach:
    return _get_user_from_header(db)

def _get_user_from_header(db: Session):
    # workaround to access request:
    from fastapi import Request
    from fastapi import Depends
    # FastAPI trick: we'll read per-call via a small inner function
    raise RuntimeError("Use dependency `current_user` defined in main.py")

@router.post("/register", response_model=UserOut)
def register(payload: RegisterIn, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email.lower()).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(email=payload.email.lower(), password_hash=hash_pw(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@router.post("/login", response_model=TokenOut)
def login(payload: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user or not verify_pw(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_token(user.id)
    return TokenOut(access_token=token)

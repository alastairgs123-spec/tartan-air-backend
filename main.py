from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from database import Base, engine, get_db
from models import Route, User
from schemas import RouteOut, UserOut
from auth import router as auth_router, create_token, ALGORITHM, SECRET_KEY
from flights import router as flights_router
from jose import jwt, JWTError
import os

# Create tables
Base.metadata.create_all(bind=engine)

# Seed routes if empty
from va_routes import ROUTES as SEED_ROUTES
def seed_routes(db: Session):
    if db.query(Route).count() > 0:
        return
    for r in SEED_ROUTES:
        db.add(Route(dep=r["dep"], arr=r["arr"], distance_nm=r["distance_nm"], aircraft=r["aircraft"]))
    db.commit()

app = FastAPI(title="Tartan Air API", version="1.0")

# CORS (allow all for now; tighten later)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

# Dependency to get current user from Bearer token
def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    auth = request.headers.get("Authorization")
    if not auth or not auth.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = auth.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = db.query(User).get(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

@app.on_event("startup")
def startup():
    db = next(get_db())
    seed_routes(db)

@app.get("/me", response_model=UserOut, tags=["auth"])
def me(user: User = Depends(current_user)):
    return user

@app.get("/routes", response_model=list[RouteOut], tags=["routes"])
def list_routes(db: Session = Depends(get_db)):
    return db.query(Route).order_by(Route.dep, Route.arr).all()

# Routers
app.include_router(auth_router)
app.include_router(flights_router)

# Health
@app.get("/", tags=["health"])
def root():
    return {"ok": True, "service": "Tartan Air API"}

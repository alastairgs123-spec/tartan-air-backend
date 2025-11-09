from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List

from database import get_db
from models import Flight, Position, Route, User
from schemas import StartFlightIn, UpdateFlightIn, FinishFlightIn, LiveFlightOut, PositionOut
from jose import jwt, JWTError
import os

router = APIRouter(prefix="/flights", tags=["flights"])

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
ALGORITHM = "HS256"

def current_user(db: Session = Depends(get_db), authorization: str | None = None) -> User:
    # simple bearer extractor
    from fastapi import Request
    req: Request = router.dependency_overrides_context.request  # internals; fallback below if None
    try:
        # robust header read:
        auth = req.headers.get("Authorization")
    except Exception:
        auth = None
    auth = auth or authorization
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

@router.post("/start")
def start_flight(payload: StartFlightIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    route = None
    if payload.route_id:
        route = db.query(Route).get(payload.route_id)
        if not route:
            raise HTTPException(status_code=404, detail="Route not found")

    flight = Flight(
        user_id=user.id,
        route_id=route.id if route else None,
        dep=payload.dep.upper(),
        arr=payload.arr.upper(),
        status="active",
    )
    db.add(flight)
    db.commit()
    db.refresh(flight)
    return {"flight_id": flight.id, "message": "Flight started"}

@router.post("/update")
def update_flight(payload: UpdateFlightIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    flight = db.query(Flight).get(payload.flight_id)
    if not flight or flight.user_id != user.id:
        raise HTTPException(status_code=404, detail="Flight not found")

    pos = Position(
        flight_id=flight.id,
        lat=payload.lat,
        lon=payload.lon,
        alt_ft=payload.alt_ft,
        ias_kt=payload.ias_kt,
        vs_fpm=payload.vs_fpm,
        onground=payload.onground,
    )
    db.add(pos)
    db.commit()
    return {"ok": True}

@router.post("/finish")
def finish_flight(payload: FinishFlightIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    flight = db.query(Flight).get(payload.flight_id)
    if not flight or flight.user_id != user.id:
        raise HTTPException(status_code=404, detail="Flight not found")
    if flight.status == "finished":
        return {"message": "Already finished"}

    flight.end_ts = datetime.utcnow()
    # compute block time
    if flight.start_ts and flight.end_ts:
        mins = (flight.end_ts - flight.start_ts).total_seconds() / 60.0
        flight.block_minutes = round(mins, 1)

    # compute distance from positions
    from math import radians, sin, cos, sqrt, atan2
    def hav_nm(a, b):
        R_km = 6371.0
        dlat = radians(b.lat - a.lat)
        dlon = radians(b.lon - a.lon)
        A = sin(dlat/2)**2 + cos(radians(a.lat))*cos(radians(b.lat))*sin(dlon/2)**2
        c = 2*atan2(sqrt(A), sqrt(1-A))
        return R_km * c * 0.539957

    pts = db.query(Position).filter(Position.flight_id == flight.id).order_by(Position.ts.asc()).all()
    dist = 0.0
    for i in range(1, len(pts)):
        dist += hav_nm(pts[i-1], pts[i])
    flight.distance_nm = round(dist, 1)
    flight.landing_rate_fpm = payload.landing_rate_fpm
    flight.status = "finished"

    db.commit()
    return {"message": "Flight finished", "block_minutes": flight.block_minutes, "distance_nm": flight.distance_nm}

@router.get("/live", response_model=List[LiveFlightOut])
def live_flights(db: Session = Depends(get_db)):
    # active flights with last position
    active = db.query(Flight).filter(Flight.status == "active").all()
    out = []
    for f in active:
        last = db.query(Position).filter(Position.flight_id == f.id).order_by(Position.ts.desc()).first()
        if not last:
            continue
        out.append({
            "flight_id": f.id,
            "callsign": (f.user.callsign or f"user{f.user_id}"),
            "dep": f.dep,
            "arr": f.arr,
            "last_position": {
                "ts": last.ts, "lat": last.lat, "lon": last.lon,
                "alt_ft": last.alt_ft, "ias_kt": last.ias_kt,
                "vs_fpm": last.vs_fpm, "onground": last.onground
            }
        })
    return out

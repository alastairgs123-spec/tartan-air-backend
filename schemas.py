from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime

# --- Auth ---
class RegisterIn(BaseModel):
    email: EmailStr
    password: str

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserOut(BaseModel):
    id: int
    email: EmailStr
    callsign: Optional[str] = None
    class Config:
        from_attributes = True

# --- Routes ---
class RouteOut(BaseModel):
    id: int
    dep: str
    arr: str
    distance_nm: int
    aircraft: str
    class Config:
        from_attributes = True

# --- Flights ---
class StartFlightIn(BaseModel):
    route_id: Optional[int] = None
    dep: str
    arr: str

class UpdateFlightIn(BaseModel):
    flight_id: int
    lat: float
    lon: float
    alt_ft: float
    ias_kt: float
    vs_fpm: float
    onground: bool

class FinishFlightIn(BaseModel):
    flight_id: int
    landing_rate_fpm: Optional[float] = None

class PositionOut(BaseModel):
    ts: datetime
    lat: float
    lon: float
    alt_ft: float
    ias_kt: float
    vs_fpm: float
    onground: bool

class LiveFlightOut(BaseModel):
    flight_id: int
    callsign: str
    dep: str
    arr: str
    last_position: PositionOut

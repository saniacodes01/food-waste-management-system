from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime


# ── Auth ──────────────────────────────────────────────────────────────────────

class RegisterIn(BaseModel):
    role: str = Field(..., pattern="^(restaurant|ngo|delivery)$")
    name: str
    email: EmailStr
    password: str = Field(..., min_length=6)
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    description: Optional[str] = None      # ngo / restaurant
    vehicle_type: Optional[str] = None     # delivery


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    user: "UserOut"


class UserOut(BaseModel):
    id: int
    role: str
    name: str
    email: EmailStr
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    description: Optional[str] = None
    vehicle_type: Optional[str] = None
    is_available: bool
    is_approved: bool
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    description: Optional[str] = None
    vehicle_type: Optional[str] = None
    password: Optional[str] = Field(None, min_length=6)


class AvailabilityUpdate(BaseModel):
    is_available: Optional[bool] = None
    lat: Optional[float] = None
    lng: Optional[float] = None


# ── Donations ─────────────────────────────────────────────────────────────────

class DonationCreate(BaseModel):
    food_name: str
    meal_type: Optional[str] = Field(None, pattern="^(veg|non-veg)$")
    category: Optional[str] = None          # raw-food | cooked-food | packed-food
    quantity: Optional[str] = None
    notes: Optional[str] = None
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    pickup_address: str
    city: Optional[str] = None
    lat: float
    lng: float
    best_before: Optional[datetime] = None


class DonationUpdate(BaseModel):
    food_name: Optional[str] = None
    meal_type: Optional[str] = Field(None, pattern="^(veg|non-veg)$")
    category: Optional[str] = None
    quantity: Optional[str] = None
    notes: Optional[str] = None
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    pickup_address: Optional[str] = None
    city: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    best_before: Optional[datetime] = None


class PartyBrief(BaseModel):
    id: int
    name: str
    phone: Optional[str] = None
    role: str

    class Config:
        from_attributes = True


class DonationEventOut(BaseModel):
    id: int
    status: str
    actor_role: Optional[str] = None
    note: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class DonationOut(BaseModel):
    id: int
    status: str
    food_name: str
    meal_type: Optional[str] = None
    category: Optional[str] = None
    quantity: Optional[str] = None
    notes: Optional[str] = None
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    pickup_address: str
    city: Optional[str] = None
    lat: float
    lng: float
    best_before: Optional[datetime] = None
    created_at: datetime
    claimed_at: Optional[datetime] = None
    picked_up_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    distance_km: Optional[float] = None

    restaurant: Optional[PartyBrief] = None
    ngo: Optional[PartyBrief] = None
    delivery_partner: Optional[PartyBrief] = None
    events: List[DonationEventOut] = []

    class Config:
        from_attributes = True


# ── Feedback ──────────────────────────────────────────────────────────────────

class FeedbackIn(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    message: str


class FeedbackOut(BaseModel):
    id: int
    name: Optional[str] = None
    email: Optional[str] = None
    message: str
    created_at: datetime

    class Config:
        from_attributes = True


# ── Admin ─────────────────────────────────────────────────────────────────────

class AdminStats(BaseModel):
    users: dict
    donations: dict
    feedback_count: int


class ApprovalUpdate(BaseModel):
    is_approved: Optional[bool] = None
    is_active: Optional[bool] = None


Token.model_rebuild()

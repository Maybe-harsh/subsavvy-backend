from pydantic import BaseModel, EmailStr, ConfigDict
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import date, datetime

# --- USER SCHEMAS ---
class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str # Plain password coming from frontend; we will hash it before saving

class UserResponse(UserBase):
    id: UUID
    taste_profile: Optional[List[str]] = [] # <-- Just added Optional and = []
    created_at: datetime

    # This tells Pydantic to read data even if it's an SQLAlchemy model, not just a dictionary
    model_config = ConfigDict(from_attributes=True)
   
# --- PLATFORM SCHEMAS ---
class PlatformBase(BaseModel):
    name: str
    category: Optional[str] = None
    affiliate_url: Optional[str] = None

class PlatformCreate(PlatformBase):
    pass

class PlatformResponse(PlatformBase):
    id: UUID
    model_config = ConfigDict(from_attributes=True)


# --- SUBSCRIPTION SCHEMAS ---
class SubscriptionBase(BaseModel):
    platform_id: UUID
    cost: float
    billing_cycle: str = "Monthly"
    next_billing_date: date
    status: str = "Active"

class SubscriptionCreate(SubscriptionBase):
    pass

class SubscriptionResponse(SubscriptionBase):
    id: UUID
    user_id: UUID
    platform: PlatformResponse # Includes the platform details automatically
    model_config = ConfigDict(from_attributes=True)

# --- INCOMING FRONTEND REQUESTS ---
class SubscriptionCreateFrontend(BaseModel):
    platform_name: str
    cost: float
    billing_cycle: str = "monthly"
    next_billing_date: date

# --- USAGE LOG SCHEMAS ---
class UsageLogBase(BaseModel):
    subscription_id: UUID
    date_logged: date
    minutes_used: int

class UsageLogCreate(UsageLogBase):
    pass

class UsageLogResponse(UsageLogBase):
    id: UUID
    model_config = ConfigDict(from_attributes=True)

# --- EXTENSION SCHEMAS (NEW) ---
class UsageLogExtensionCreate(BaseModel):
    platform_name: str
    minutes_used: int
    date_logged: date
    title: Optional[str] = None
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from enum import Enum

class PlanTier(str, Enum):
    FREE = "FREE"
    PRO = "PRO"
    ENTERPRISE = "ENTERPRISE"

class CompanyCreate(BaseModel):
    name: str
    domain: Optional[str] = None
    plan_tier: PlanTier = PlanTier.FREE

class UserProvision(BaseModel):
    email: EmailStr
    full_name: str
    company_id: str
    role: str = "hr_admin"
    password: str = Field(..., min_length=8)

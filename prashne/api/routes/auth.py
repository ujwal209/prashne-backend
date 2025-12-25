from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any
from prashne.core.security import get_current_user
from prashne.core.database import supabase
from prashne.schemas.auth import LoginRequest

router = APIRouter()

@router.post("/login")
def login(credentials: LoginRequest):
    """
    Proxy Login: Authenticates with Supabase via Backend.
    Returns Access Token + Role from DB.
    """
    try:
        # 1. Auth with Supabase
        auth_response = supabase.auth.sign_in_with_password({
            "email": credentials.email,
            "password": credentials.password
        })
        
        session = auth_response.session
        user = auth_response.user

        if not session or not user:
            raise HTTPException(status_code=401, detail="Authentication failed")

        # 2. Fetch Role from Profiles (Source of Truth)
        try:
            profile_response = supabase.table("profiles").select("role").eq("id", user.id).single().execute()
            role = profile_response.data.get("role") if profile_response.data else "hr_user"
        except:
             # Fallback if profile missing (should not happen in prod)
             role = "hr_user"

        return {
            "access_token": session.access_token,
            "refresh_token": session.refresh_token,
            "user": {
                "id": user.id,
                "email": user.email,
                "role": role
            }
        }

    except Exception as e:
        # Check for specific Supabase error messages
        error_msg = str(e)
        if "Invalid login credentials" in error_msg:
             raise HTTPException(status_code=401, detail="Invalid email or password")
        
        print(f"Login Error: {error_msg}")
        raise HTTPException(status_code=400, detail=error_msg)

@router.get("/me", response_model=Dict[str, Any])
def validate_token(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Validates token and returns user info from the database (Profiles table).
    """
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid token: missing subject")

    # Fetch exact role from profiles table
    try:
        response = supabase.table("profiles").select("role").eq("id", user_id).single().execute()
        db_role = response.data.get("role") if response.data else "hr_user"
    except Exception as e:
        print(f"DEBUG: Failed to fetch profile for {user_id}: {e}")
        db_role = current_user.get("user_metadata", {}).get("role", "hr_user")

    return {
        "id": user_id,
        "email": current_user.get("email"),
        "role": db_role, 
        "full_payload": current_user
    }

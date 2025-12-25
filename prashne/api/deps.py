from fastapi import Depends, HTTPException, status
from typing import Dict, Any, List
from prashne.core.security import get_current_user
from prashne.core.database import supabase_admin 

def require_super_admin(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Dependency that ensures the user is a Super Admin.
    Uses supabase_admin (Service Role) to bypass RLS and guarantee we can see the profile.
    """
    user_id = current_user.get("sub")
    if not user_id:
         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not find user ID in token")

    try:
        response = supabase_admin.table("profiles").select("role").eq("id", user_id).single().execute()
        if not response.data:
             raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Profile not found.")
            
        real_role = response.data.get("role")
        if real_role != "super_admin":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access Denied: Super Admin only.")
            
        current_user["role"] = real_role
        return current_user
    except Exception as e:
        print(f"DEBUG: Super Admin Check Failed: {e}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Authorization failed.")

def require_hr_admin(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Allows 'hr_admin' or 'super_admin'.
    """
    role = _get_role_from_metadata(current_user)
    if role not in ["hr_admin", "super_admin"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"HR Admin privileges required. Found: {role}")
    return current_user

def require_hr_staff(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Allows 'hr_user', 'hr_admin', or 'super_admin'.
    """
    role = _get_role_from_metadata(current_user)
    if role not in ["hr_user", "hr_admin", "super_admin"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"HR Staff privileges required. Found: {role}")
    return current_user

def _get_role_from_metadata(user: Dict[str, Any]) -> str:
    app_meta = user.get("app_metadata", {})
    user_meta = user.get("user_metadata", {})
    return app_meta.get("role") or user_meta.get("role") or "authenticated"
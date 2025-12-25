from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any
from prashne.api.deps import require_super_admin
from prashne.schemas.admin import CompanyCreate, UserProvision
from prashne.core.database import supabase_admin, supabase # Use admin client for user creation

from prashne.core.security import get_current_user

router = APIRouter()

@router.get("/debug-me")
def debug_me(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Temporary Debug Endpoint to check why 403 is happening.
    """
    user_id = current_user.get("sub")
    print(f"DEBUG: Checking profile for User ID: {user_id}")
    
    try:
        response = supabase.table("profiles").select("*").eq("id", user_id).execute()
        return {
            "token_sub": user_id,
            "profile_found": bool(response.data),
            "profile_data": response.data,
            "token_claims": current_user
        }
    except Exception as e:
        return {"error": str(e)}

@router.post("/companies", status_code=status.HTTP_201_CREATED)
def create_company(company: CompanyCreate, admin: Dict[str, Any] = Depends(require_super_admin)):
    """
    Create a new Company / Tenant.
    """
    try:
        response = supabase_admin.table("companies").insert({
            "name": company.name,
            "domain": company.domain,
            "plan_tier": company.plan_tier.value
        }).execute()
        
        # In Supabase-py v2, response.data holds the result
        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to create company")
            
        return response.data[0]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/companies")
def list_companies(admin: Dict[str, Any] = Depends(require_super_admin)):
    """
    List all companies.
    """
    try:
        # TODO: Add pagination later
        response = supabase_admin.table("companies").select("*").execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def send_welcome_email(email: str, password: str, full_name: str):
    """
    Mock Email Notification. In Prod, use fastapi-mail or Resend.
    """
    print(f"""
    =========================================
    [EMAIL SERVER MOCK]
    To: {email}
    Subject: Welcome to Prashne HR Platform
    
    Hi {full_name},
    
    Your account has been created by the Super Admin.
    
    Login Credentials:
    Email: {email}
    Temporary Password: {password}
    
    Please login at: http://localhost:5173/login
    =========================================
    """)

@router.post("/users", status_code=status.HTTP_201_CREATED)
def provision_user(user_in: UserProvision, admin: Dict[str, Any] = Depends(require_super_admin)):
    """
    Provision a new HR Admin user.
    1. Create user in Supabase Auth.
    2. Create profile in 'profiles' table.
    3. Send Welcome Email.
    """
    try:
        # 1. Create Auth User
        # supabase.auth.admin requires service_role key
        auth_response = supabase_admin.auth.admin.create_user({
            "email": user_in.email,
            "password": user_in.password,
            "email_confirm": True, # Auto-confirm email
            "user_metadata": {"role": user_in.role} # Supabase Metadata for RLS
        })
        
        new_user = auth_response.user
        if not new_user:
             raise HTTPException(status_code=500, detail="Failed to create auth user")

        # 2. Create Profile
        profile_data = {
            "id": new_user.id,
            "email": user_in.email,
            "full_name": user_in.full_name,
            "company_id": user_in.company_id,
            "role": user_in.role # "hr_admin" or "hr_user"
        }
        
        profile_response = supabase_admin.table("profiles").insert(profile_data).execute()
        
        # 3. Send Email
        send_welcome_email(user_in.email, user_in.password, user_in.full_name)

        return {"id": new_user.id, "email": new_user.email, "profile": profile_response.data[0]}

    except Exception as e:
        # Check if user already exists
        if "User already exists" in str(e):
             raise HTTPException(status_code=400, detail="User with this email already exists")
        print(f"Provisioning Error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/stats")
def get_global_stats(admin: Dict[str, Any] = Depends(require_super_admin)):
    """
    Get global usage statistics.
    """
    try:
        # Count Companies
        companies_count = supabase_admin.table("companies").select("id", count="exact").execute().count
        
        # Count Resumes (Total)
        # Assuming there is a 'resumes' table
        try:
             resumes_count = supabase_admin.table("resumes").select("id", count="exact").execute().count
        except:
             resumes_count = 0 
             
        # Count Users (Total Profiles)
        users_count = supabase_admin.table("profiles").select("id", count="exact").execute().count

        return {
            "total_companies": companies_count,
            "total_resumes_parsed": resumes_count,
            "total_users": users_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

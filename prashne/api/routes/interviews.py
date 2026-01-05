import os
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from prashne.core.config import settings
from prashne.core.database import supabase_admin
from prashne.api.deps import get_current_user

router = APIRouter()

class InterviewCreate(BaseModel):
    job_id: str
    resume_id: str
    company_id: Optional[str] = None  # Make it optional from request

@router.post("/")
def create_interview_session(
    data: InterviewCreate,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Creates a new interview session.
    """
    try:
        # 1. Get company_id from request or user profile
        company_id = data.company_id
        
        if not company_id:
            # Try to get company_id from user's profile
            profile_res = supabase_admin.table("profiles").select("company_id").eq("id", current_user.get("sub")).single().execute()
            if profile_res.data and profile_res.data.get("company_id"):
                company_id = profile_res.data.get("company_id")
            else:
                # If still no company_id, get it from the job (if jobs had company_id)
                # For now, we'll require company_id in request or profile
                raise HTTPException(
                    status_code=400, 
                    detail="Company ID is required. Please provide company_id in request or ensure user profile has company_id"
                )

        # 2. Verify the job exists
        job_res = supabase_admin.table("jobs").select("*").eq("id", data.job_id).single().execute()
        if not job_res.data:
            raise HTTPException(status_code=404, detail="Job not found")

        # 3. Verify the resume exists
        resume_res = supabase_admin.table("resumes").select("*").eq("id", data.resume_id).single().execute()
        if not resume_res.data:
            raise HTTPException(status_code=404, detail="Resume not found")

        # 4. Create session
        session_data = {
            "job_id": data.job_id,
            "candidate_id": data.resume_id, 
            "company_id": company_id,
            "status": "pending",  # Must be one of: pending, in_progress, completed, failed
            "created_by": current_user.get("sub")
        }
        
        res = supabase_admin.table("interview_sessions").insert(session_data).execute()
        if not res.data:
            raise HTTPException(status_code=500, detail="Failed to create session")
            
        return {
            "message": "Interview session created successfully",
            "session": res.data[0]
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Create Session Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{session_id}/context")
def get_interview_context(session_id: str):
    """
    Fetches the context for the interview (Job details, Candidate details)
    and the Vapi Public Key.
    """
    try:
        # 1. Fetch Session
        session_res = supabase_admin.table("interview_sessions").select("*").eq("id", session_id).single().execute()
        if not session_res.data:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session = session_res.data
        job_id = session.get("job_id")
        resume_id = session.get("candidate_id")  # Changed from resume_id to candidate_id
        
        if not job_id or not resume_id:
            raise HTTPException(status_code=400, detail="Invalid session data: Missing job or candidate ID")

        # 2. Fetch Job Context
        job_res = supabase_admin.table("jobs").select("title, description, requirements, location, salary").eq("id", job_id).single().execute()
        job = job_res.data if job_res.data else {}

        # 3. Fetch Resume Context
        resume_res = supabase_admin.table("resumes").select("candidate_name, raw_ai_response, skills, experience_years, education").eq("id", resume_id).single().execute()
        resume = resume_res.data if resume_res.data else {}

        # 4. Return Combined Context
        return {
            "vapi_public_key": settings.VAPI_PUBLIC_KEY,
            "can_start": True,
            "session": {
                "id": session_id,
                "status": session.get("status", "pending")
            },
            "context": {
                "candidate_name": resume.get("candidate_name", "Candidate"),
                "candidate_skills": resume.get("skills", []),
                "candidate_experience": resume.get("experience_years", 0),
                "candidate_education": resume.get("education", ""),
                "job_title": job.get("title", "Role"),
                "job_description": job.get("description", ""),
                "job_requirements": job.get("requirements", []),
                "job_location": job.get("location", ""),
                "job_salary": job.get("salary", ""),
                "resume_data": resume.get("raw_ai_response", {})
            }
        }

    except Exception as e:
        print(f"Error fetching interview context: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/")
def get_interview_sessions(
    current_user: Dict[str, Any] = Depends(get_current_user),
    job_id: Optional[str] = Query(None),
    company_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None)
):
    """
    Get all interview sessions with optional filters.
    """
    try:
        # Build query with joins - FIXED: Added proper spacing in aliases
        query = supabase_admin.table("interview_sessions").select(
            """
            *,
            jobs(title, description),
            resumes(candidate_name, email),
            companies!inner(name)
            """
        )
        
        # Add filters if provided
        if job_id:
            query = query.eq("job_id", job_id)
        if company_id:
            query = query.eq("company_id", company_id)
        if status:
            query = query.eq("status", status)
        
        # Order by started_at descending
        query = query.order("started_at", desc=True)
        
        res = query.execute()
        
        # Process the data to include company name
        sessions = []
        for session in (res.data or []):
            session_data = dict(session)
            # Extract company name from the joined companies table
            if "companies" in session and session["companies"]:
                session_data["company_name"] = session["companies"].get("name")
            else:
                session_data["company_name"] = None
            sessions.append(session_data)
        
        return sessions
        
    except Exception as e:
        print(f"Error fetching interview sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{session_id}")
def get_interview_session(
    session_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get a specific interview session by ID.
    """
    try:
        res = supabase_admin.table("interview_sessions").select(
            """
            *,
            jobs(title, description, requirements, location, salary),
            resumes(candidate_name, email, phone, skills, experience_years, education),
            companies!inner(name)
            """
        ).eq("id", session_id).single().execute()
        
        if not res.data:
            raise HTTPException(status_code=404, detail="Interview session not found")
        
        # Process the data
        session_data = dict(res.data)
        if "companies" in session_data and session_data["companies"]:
            session_data["company_name"] = session_data["companies"].get("name")
        else:
            session_data["company_name"] = None
            
        return session_data
        
    except Exception as e:
        print(f"Error fetching interview session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class SessionUpdate(BaseModel):
    status: Optional[str] = None
    final_score: Optional[int] = None
    summary_report: Optional[str] = None

@router.put("/{session_id}")
def update_interview_session(
    session_id: str,
    update_data: SessionUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Update an interview session (e.g., status, final_score, summary_report).
    """
    try:
        # Check if session exists
        session_res = supabase_admin.table("interview_sessions").select("*").eq("id", session_id).single().execute()
        if not session_res.data:
            raise HTTPException(status_code=404, detail="Interview session not found")
        
        # Prepare update data
        update_dict = update_data.dict(exclude_none=True)
        
        # If status is being updated to 'completed', set completed_at
        if update_dict.get("status") == "completed":
            update_dict["completed_at"] = "now()"
        
        # Update session
        res = supabase_admin.table("interview_sessions").update(update_dict).eq("id", session_id).execute()
        if not res.data:
            raise HTTPException(status_code=500, detail="Failed to update session")
        
        return {
            "message": "Interview session updated successfully",
            "session": res.data[0]
        }
        
    except Exception as e:
        print(f"Error updating interview session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{session_id}")
def delete_interview_session(
    session_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Delete an interview session.
    """
    try:
        # Check if session exists
        session_res = supabase_admin.table("interview_sessions").select("*").eq("id", session_id).single().execute()
        if not session_res.data:
            raise HTTPException(status_code=404, detail="Interview session not found")
        
        # Delete session
        supabase_admin.table("interview_sessions").delete().eq("id", session_id).execute()
        
        return {"message": "Interview session deleted successfully"}
        
    except Exception as e:
        print(f"Error deleting interview session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{session_id}/analysis")
def get_session_analysis(
    session_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get analysis data for an interview session.
    """
    try:
        res = supabase_admin.table("interview_sessions").select(
            "final_score, summary_report, status, started_at, completed_at"
        ).eq("id", session_id).single().execute()
        
        if not res.data:
            raise HTTPException(status_code=404, detail="Interview session not found")
        
        return res.data
        
    except Exception as e:
        print(f"Error fetching session analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/user/list")
def get_user_interview_sessions(
    current_user: Dict[str, Any] = Depends(get_current_user),
    status: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """
    Get interview sessions for the current logged-in user.
    """
    try:
        user_id = current_user.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        # First, get all resume IDs for this user
        user_resumes_res = supabase_admin.table("resumes").select("id").eq("created_by", user_id).execute()
        user_resume_ids = [resume["id"] for resume in (user_resumes_res.data or [])]
        
        # We'll fetch in two parts and combine
        sessions_created = []
        sessions_as_candidate = []
        
        # 1. Fetch sessions created by the user
        if True:  # Always fetch created sessions
            query_created = supabase_admin.table("interview_sessions").select(
                """
                *,
                jobs!inner(title, description, location, salary),
                resumes!inner(candidate_name, email, skills),
                companies!inner(name)
                """
            ).eq("created_by", user_id)
            
            if status:
                query_created = query_created.eq("status", status)
            
            query_created = query_created.order("started_at", desc=True)
            
            if limit > 0:
                query_created = query_created.range(offset, offset + limit - 1)
            
            res_created = query_created.execute()
            sessions_created = res_created.data or []
        
        # 2. Fetch sessions where user is the candidate (if they have resumes)
        if user_resume_ids:
            query_candidate = supabase_admin.table("interview_sessions").select(
                """
                *,
                jobs!inner(title, description, location, salary),
                resumes!inner(candidate_name, email, skills),
                companies!inner(name)
                """
            ).in_("candidate_id", user_resume_ids)
            
            if status:
                query_candidate = query_candidate.eq("status", status)
            
            query_candidate = query_candidate.order("started_at", desc=True)
            
            if limit > 0:
                query_candidate = query_candidate.range(offset, offset + limit - 1)
            
            res_candidate = query_candidate.execute()
            sessions_as_candidate = res_candidate.data or []
        
        # Combine and deduplicate sessions
        all_sessions_dict = {}
        
        for session in sessions_created:
            session_id_val = session.get("id")
            if session_id_val not in all_sessions_dict:
                session_data = dict(session)
                session_data["is_creator"] = True
                session_data["is_candidate"] = False
                if "companies" in session_data and session_data["companies"]:
                    session_data["company_name"] = session_data["companies"].get("name")
                else:
                    session_data["company_name"] = None
                all_sessions_dict[session_id_val] = session_data
        
        for session in sessions_as_candidate:
            session_id_val = session.get("id")
            if session_id_val in all_sessions_dict:
                # If already exists (user is both creator and candidate), update flags
                all_sessions_dict[session_id_val]["is_candidate"] = True
            else:
                session_data = dict(session)
                session_data["is_creator"] = False
                session_data["is_candidate"] = True
                if "companies" in session_data and session_data["companies"]:
                    session_data["company_name"] = session_data["companies"].get("name")
                else:
                    session_data["company_name"] = None
                all_sessions_dict[session_id_val] = session_data
        
        # Convert to list and sort by started_at (newest first)
        all_sessions = list(all_sessions_dict.values())
        all_sessions.sort(key=lambda x: x.get("started_at") or "", reverse=True)
        
        # Apply limit after combining (since we fetched both types separately)
        if limit > 0:
            all_sessions = all_sessions[offset:offset + limit]
        
        return {
            "sessions": all_sessions,  # Return the full data, not formatted
            "pagination": {
                "limit": limit,
                "offset": offset,
                "total": len(all_sessions),
                "has_more": len(all_sessions) == limit if limit > 0 else False
            }
        }
        
    except Exception as e:
        print(f"Error fetching user interview sessions: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    """
    Get interview sessions for the current logged-in user.
    
    - Returns sessions where user is the creator (created_by) or candidate
    - Can filter by status
    - Supports pagination with limit and offset
    """
    try:
        user_id = current_user.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        # First, get all resume IDs for this user
        user_resumes_res = supabase_admin.table("resumes").select("id").eq("created_by", user_id).execute()
        user_resume_ids = [resume["id"] for resume in (user_resumes_res.data or [])]
        
        # We'll fetch in two parts and combine
        sessions_created = []
        sessions_as_candidate = []
        
        # 1. Fetch sessions created by the user
        if True:  # Always fetch created sessions
            query_created = supabase_admin.table("interview_sessions").select(
                """
                *,
                jobs(title, description, location, salary),
                resumes(candidate_name, email, skills),
                companies!inner(name)
                """
            ).eq("created_by", user_id)
            
            if status:
                query_created = query_created.eq("status", status)
            
            query_created = query_created.order("started_at", desc=True)
            
            if limit > 0:
                query_created = query_created.range(offset, offset + limit - 1)
            
            res_created = query_created.execute()
            sessions_created = res_created.data or []
        
        # 2. Fetch sessions where user is the candidate (if they have resumes)
        if user_resume_ids:
            query_candidate = supabase_admin.table("interview_sessions").select(
                """
                *,
                jobs(title, description, location, salary),
                resumes(candidate_name, email, skills),
                companies!inner(name)
                """
            ).in_("candidate_id", user_resume_ids)
            
            if status:
                query_candidate = query_candidate.eq("status", status)
            
            query_candidate = query_candidate.order("started_at", desc=True)
            
            if limit > 0:
                query_candidate = query_candidate.range(offset, offset + limit - 1)
            
            res_candidate = query_candidate.execute()
            sessions_as_candidate = res_candidate.data or []
        
        # Combine and deduplicate sessions
        all_sessions_dict = {}
        
        for session in sessions_created:
            session_id_val = session.get("id")
            if session_id_val not in all_sessions_dict:
                session_data = dict(session)
                session_data["is_creator"] = True
                session_data["is_candidate"] = False
                if "companies" in session_data and session_data["companies"]:
                    session_data["company_name"] = session_data["companies"].get("name")
                else:
                    session_data["company_name"] = None
                all_sessions_dict[session_id_val] = session_data
        
        for session in sessions_as_candidate:
            session_id_val = session.get("id")
            if session_id_val in all_sessions_dict:
                # If already exists (user is both creator and candidate), update flags
                all_sessions_dict[session_id_val]["is_candidate"] = True
            else:
                session_data = dict(session)
                session_data["is_creator"] = False
                session_data["is_candidate"] = True
                if "companies" in session_data and session_data["companies"]:
                    session_data["company_name"] = session_data["companies"].get("name")
                else:
                    session_data["company_name"] = None
                all_sessions_dict[session_id_val] = session_data
        
        # Convert to list and sort by started_at (newest first)
        all_sessions = list(all_sessions_dict.values())
        all_sessions.sort(key=lambda x: x.get("started_at") or "", reverse=True)
        
        # Apply limit after combining (since we fetched both types separately)
        if limit > 0:
            all_sessions = all_sessions[offset:offset + limit]
        
        # Format the response
        formatted_sessions = []
        for session in all_sessions:
            formatted_session = {
                "id": session.get("id"),
                "job_title": session.get("jobs", {}).get("title") if session.get("jobs") else None,
                "candidate_name": session.get("resumes", {}).get("candidate_name") if session.get("resumes") else None,
                "company_name": session.get("company_name"),
                "status": session.get("status"),
                "final_score": session.get("final_score"),
                "started_at": session.get("started_at"),
                "completed_at": session.get("completed_at"),
                "created_by": session.get("created_by"),
                "is_creator": session.get("is_creator", False),
                "is_candidate": session.get("is_candidate", False)
            }
            formatted_sessions.append(formatted_session)
        
        return {
            "sessions": formatted_sessions,
            "pagination": {
                "limit": limit,
                "offset": offset,
                "total": len(formatted_sessions),
                "has_more": len(formatted_sessions) == limit if limit > 0 else False
            }
        }
        
    except Exception as e:
        print(f"Error fetching user interview sessions: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
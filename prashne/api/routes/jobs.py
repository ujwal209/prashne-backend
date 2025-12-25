from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from prashne.core.database import supabase_admin
from prashne.api.deps import require_hr_staff

router = APIRouter()

from prashne.schemas.jobs import JobCreate, MatchRequest, MatchResult
from prashne.services.ai_matching import batch_match_resumes

@router.post("/match", response_model=List[MatchResult])
async def match_candidates(request: MatchRequest, current_user: Dict[str, Any] = Depends(require_hr_staff)):
    try:
        user_id = current_user.get("sub")
        query = supabase_admin.table("resumes").select("*").eq("created_by", user_id)
        
        if request.candidate_ids:
            query = query.in_("id", request.candidate_ids)
            
        res = query.execute()
        resumes = res.data
        
        if not resumes:
            return []
            
        results = await batch_match_resumes(resumes, request.jd_text)
        
        matches_to_insert = []
        for r in results:
            match_entry = {
                "job_id": request.job_id,
                "resume_id": r["candidate_id"],
                "match_score": r["score"],
                "match_reason": r["reason"],
                "created_by": user_id
            }
            matches_to_insert.append(match_entry)

        if matches_to_insert:
            try:
                supabase_admin.table("matches").upsert(matches_to_insert, on_conflict="job_id,resume_id").execute()
            except Exception as e:
                print(f"Failed to save matches: {e}")
        
        return results
    except Exception as e:
        print(f"Smart Match Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/matches")
def get_match_history(current_user: Dict[str, Any] = Depends(require_hr_staff)):
    try:
        res = supabase_admin.table("matches")\
            .select("*, job:jobs(title), resume:resumes(candidate_name)")\
            .order("created_at", desc=True)\
            .limit(100)\
            .execute()
        return res.data
    except Exception as e:
        print(f"Fetch Matches Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch history")

@router.post("/generate")
def generate_job(prompt: dict, current_user: Dict[str, Any] = Depends(require_hr_staff)):
    user_prompt = prompt.get("prompt")
    if not user_prompt:
        raise HTTPException(status_code=400, detail="Prompt is required")
        
    from prashne.services.groq_service import generate_job_description_with_ai
    result = generate_job_description_with_ai(user_prompt)
    if "error" in result:
        raise HTTPException(status_code=500, detail="AI generation failed")
    return result

@router.post("/")
def create_job(job: JobCreate, current_user: Dict[str, Any] = Depends(require_hr_staff)):
    try:
        job_data = job.model_dump()
        res = supabase_admin.table("jobs").insert(job_data).execute()
        return res.data[0]
    except Exception as e:
        print(f"Create Job Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/")
def get_jobs(current_user: Dict[str, Any] = Depends(require_hr_staff)):
    try:
        res = supabase_admin.table("jobs").select("*").order("created_at", desc=True).execute()
        return res.data
    except Exception as e:
        print(f"Fetch Jobs Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch jobs")

@router.delete("/{job_id}")
def delete_job(job_id: str, current_user: Dict[str, Any] = Depends(require_hr_staff)):
    try:
        res = supabase_admin.table("jobs").delete().eq("id", job_id).execute()
        return {"message": "Job deleted"}
    except Exception as e:
        print(f"Delete Job Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete job")

@router.put("/{job_id}")
def update_job(job_id: str, job: JobCreate, current_user: Dict[str, Any] = Depends(require_hr_staff)):
    try:
        job_data = job.model_dump()
        res = supabase_admin.table("jobs").update(job_data).eq("id", job_id).execute()
        if not res.data:
             raise HTTPException(status_code=404, detail="Job not found")
        return res.data[0]
    except Exception as e:
        print(f"Update Job Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to update job")

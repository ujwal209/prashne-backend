import json
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from typing import Dict, Any, List
from prashne.core.database import supabase_admin
from prashne.services.pdf_service import extract_text_from_pdf
from prashne.services.groq_service import parse_resume_with_ai
from prashne.api.deps import require_hr_staff
from prashne.services.cloudinary_service import upload_file_to_cloudinary

router = APIRouter()

@router.post("/upload")
async def upload_resumes(
    files: List[UploadFile] = File(...),
    current_user: Dict[str, Any] = Depends(require_hr_staff)
):
    results = []
    
    for file in files:
        if file.content_type != "application/pdf":
            results.append({"filename": file.filename, "error": "Only PDF allowed"})
            continue

        try:
            content = await file.read()
            
            # Upload to Cloudinary
            cloudinary_url = None
            try:
                cloudinary_url = upload_file_to_cloudinary(content, file.filename)
            except Exception as e:
                print(f"Cloudinary Warning: {e}")

            # Extract Text
            try:
                raw_text = extract_text_from_pdf(content)
            except:
                raw_text = ""
            
            # AI Parse
            parsed_data = {}
            if raw_text:
                parsed_data = parse_resume_with_ai(raw_text)
                if "error" in parsed_data:
                     parsed_data = {}

            # Prepare DB Entry
            resume_entry = {
                "candidate_name": parsed_data.get("full_name") or "Unknown",
                "email": parsed_data.get("email"),
                "phone": parsed_data.get("phone"),
                "skills": parsed_data.get("skills") if isinstance(parsed_data.get("skills"), list) else [],
                "experience_years": parsed_data.get("experience_years") if isinstance(parsed_data.get("experience_years"), (int, float)) else 0,
                "education": json.dumps(parsed_data.get("education")) if parsed_data.get("education") else None,
                "cloudinary_url": cloudinary_url,
                "raw_ai_response": parsed_data,
                "created_by": current_user.get("sub")
            }
            
            try:
                 db_res = supabase_admin.table("resumes").insert(resume_entry).execute()
                 results.append({
                     "filename": file.filename, 
                     "status": "success", 
                     "id": db_res.data[0]['id'],
                     "parsed": parsed_data
                 })
            except Exception as e:
                 print(f"DEBUG: DB Save Error: {e}")
                 results.append({"filename": file.filename, "error": f"DB Error: {str(e)}"})
        
        except Exception as e:
            print(f"File Processing Error: {e}")
            results.append({"filename": file.filename, "error": str(e)})

    return {"uploaded": results}

@router.get("/")
def get_resumes(current_user: Dict[str, Any] = Depends(require_hr_staff)):
    user_id = current_user.get("sub")
    try:
        # HR Staff sees only their own resumes? Or all? 
        # Usually staff sees all in a team, but filtering by 'created_by' keeps it personal for now (My Activity).
        # We can expand later. For now, preserving 'My Parsed' behavior.
        res = supabase_admin.table("resumes")\
            .select("*")\
            .eq("created_by", user_id)\
            .order("created_at", desc=True)\
            .execute()
        return res.data
    except Exception as e:
        print(f"Fetch Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch resumes")

@router.get("/stats")
def get_resume_stats(current_user: Dict[str, Any] = Depends(require_hr_staff)):
    user_id = current_user.get("sub")
    count = 0
    try:
        res = supabase_admin.table("resumes").select("id", count="exact").eq("created_by", user_id).execute()
        count = res.count
    except:
        count = 0 
    return {"total_parsed": count}

@router.delete("/{resume_id}")
def delete_resume(resume_id: str, current_user: Dict[str, Any] = Depends(require_hr_staff)):
    try:
        supabase_admin.table("resumes").delete().eq("id", resume_id).execute()
        return {"message": "Deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

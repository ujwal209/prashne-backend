from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, Any, List
from prashne.core.database import supabase_admin
from prashne.api.deps import get_current_user
from datetime import datetime, timedelta

router = APIRouter()

@router.get("/stats")
def get_dashboard_stats(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Get aggregated stats for the HR dashboard.
    """
    try:
        user_id = current_user.get("sub")
        
        # 1. Total Candidates (Resumes uploaded by this user)
        resumes_res = supabase_admin.table("resumes").select("id", count="exact").eq("created_by", user_id).execute()
        total_candidates = resumes_res.count if resumes_res.count is not None else len(resumes_res.data)

        # 2. Active Jobs (All jobs - no status or created_by column)
        jobs_res = supabase_admin.table("jobs").select("id", count="exact").execute()
        active_jobs = jobs_res.count if jobs_res.count is not None else len(jobs_res.data)

        # 3. Pending Reviews (Pending interview sessions)
        pending_res = supabase_admin.table("interview_sessions").select("id", count="exact").eq("created_by", user_id).eq("status", "pending").execute()
        pending_reviews = pending_res.count if pending_res.count is not None else len(pending_res.data)

        # 4. Today's Interviews (using started_at column)
        today_str = datetime.utcnow().date().isoformat()
        tomorrow_str = (datetime.utcnow().date() + timedelta(days=1)).isoformat()
        
        interviews_res = supabase_admin.table("interview_sessions").select("id", count="exact")\
            .eq("created_by", user_id)\
            .gte("started_at", today_str)\
            .lt("started_at", tomorrow_str)\
            .execute()
        today_interviews = interviews_res.count if interviews_res.count is not None else len(interviews_res.data)

        # 5. Matches this month (resumes uploaded this month)
        first_day_month = datetime.utcnow().replace(day=1).date().isoformat()
        matches_res = supabase_admin.table("resumes").select("id", count="exact")\
            .eq("created_by", user_id)\
            .gte("created_at", first_day_month)\
            .execute()
        matches_this_month = matches_res.count if matches_res.count is not None else len(matches_res.data)
        
        # Total Parsed (Same as total candidates)
        total_parsed = total_candidates

        return {
            "total_parsed": total_parsed,
            "total_candidates": total_candidates,
            "active_jobs": active_jobs,
            "pending_reviews": pending_reviews,
            "today_interviews": today_interviews,
            "matches_this_month": matches_this_month
        }

    except Exception as e:
        print(f"Error fetching dashboard stats: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/activities")
def get_recent_activities(
    limit: int = Query(5, ge=1, le=20),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get combined recent activity stream (Job posts, Resume uploads, Interviews created).
    """
    try:
        user_id = current_user.get("sub")
        activities = []

        # Fetch recent jobs (using created_at)
        try:
            jobs = supabase_admin.table("jobs").select("id, title, created_at")\
                .order("created_at", desc=True)\
                .limit(limit)\
                .execute().data

            for job in jobs:
                activities.append({
                    "id": f"job_{job['id']}",
                    "type": "upload",
                    "title": "New Job Posted",
                    "description": f"Posted role: {job['title']}",
                    "timestamp": job['created_at'],
                    "raw_date": datetime.fromisoformat(job['created_at'].replace('Z', '+00:00'))
                })
        except Exception as e:
            print(f"Error fetching jobs for activities: {e}")

        # Fetch recent resumes
        try:
            resumes = supabase_admin.table("resumes").select("id, candidate_name, created_at")\
                .eq("created_by", user_id)\
                .order("created_at", desc=True)\
                .limit(limit)\
                .execute().data

            for resume in resumes:
                activities.append({
                    "id": f"resume_{resume['id']}",
                    "type": "review",
                    "title": "Resume Uploaded",
                    "description": f"Added candidate: {resume['candidate_name']}",
                    "timestamp": resume['created_at'],
                    "raw_date": datetime.fromisoformat(resume['created_at'].replace('Z', '+00:00'))
                })
        except Exception as e:
            print(f"Error fetching resumes for activities: {e}")

        # Fetch recent interviews (using started_at as the timestamp)
        try:
            interviews = supabase_admin.table("interview_sessions").select("id, status, started_at, resumes(candidate_name)")\
                .eq("created_by", user_id)\
                .order("started_at", desc=True)\
                .limit(limit)\
                .execute().data

            for interview in interviews:
                candidate_name = interview.get('resumes', {}).get('candidate_name', 'Unknown')
                activities.append({
                    "id": f"interview_{interview['id']}",
                    "type": "interview",
                    "title": "Interview Scheduled",
                    "description": f"Session for {candidate_name}",
                    "timestamp": interview['started_at'],
                    "raw_date": datetime.fromisoformat(interview['started_at'].replace('Z', '+00:00'))
                })
        except Exception as e:
            print(f"Error fetching interviews for activities: {e}")

        # Sort combined list by date desc
        if activities:
            activities.sort(key=lambda x: x['raw_date'], reverse=True)
            
            # Trim to limit
            activities = activities[:limit]

            # Format timestamps as relative time
            now = datetime.now(activities[0]['raw_date'].tzinfo)

            for act in activities:
                dt = act.pop('raw_date')
                diff = now - dt
                if diff.days > 0:
                    act['timestamp'] = f"{diff.days}d ago"
                elif diff.seconds > 3600:
                    act['timestamp'] = f"{diff.seconds // 3600}h ago"
                elif diff.seconds > 60:
                    act['timestamp'] = f"{diff.seconds // 60}m ago"
                else:
                    act['timestamp'] = "Just now"

        return activities

    except Exception as e:
        print(f"Error fetching activities: {e}")
        import traceback
        traceback.print_exc()
        return []

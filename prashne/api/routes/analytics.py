from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any, List
from prashne.core.database import supabase_admin
from prashne.api.deps import require_hr_admin
from collections import Counter

router = APIRouter()

@router.get("/leaderboard")
def get_leaderboard(current_user: Dict[str, Any] = Depends(require_hr_admin)):
    """
    Get leaderboard of HR Users within the admin's company.
    Ranked by number of resumes processed.
    """
    # 1. Get current admin's company ID
    user_id = current_user.get("sub")
    profile_res = supabase_admin.table("profiles").select("company_id").eq("id", user_id).single().execute()
    
    if not profile_res.data:
        raise HTTPException(status_code=404, detail="Admin profile not found")
        
    company_id = profile_res.data.get("company_id")
    if not company_id:
        return [] # No company, no team to show
        
    # 2. Fetch all profiles for this company (The "Team")
    team_res = supabase_admin.table("profiles").select("id, email, full_name, role").eq("company_id", company_id).execute()
    team_members = team_res.data
    
    if not team_members:
        return []
        
    team_map = {m['id']: m for m in team_members}
    team_ids = list(team_map.keys())
    
    # 3. Aggregate resume counts for these users
    # Since we can't do complex GROUP BY easily with simplified client, we fetch created_by column for ALL resumes created by these users
    # This might be heavy if millions of rows, but for "HR Team" scale it's fine.
    # Alternatives: RPC call to Postgres function.
    
    resumes_res = supabase_admin.table("resumes").select("created_by").in_("created_by", team_ids).execute()
    resume_counts = Counter(r['created_by'] for r in resumes_res.data)
    
    # 4. Construct Leaderboard
    leaderboard = []
    for member in team_members:
        count = resume_counts.get(member['id'], 0)
        leaderboard.append({
            "user_id": member['id'],
            "name": member.get('full_name') or member['email'].split('@')[0],
            "email": member['email'],
            "role": member['role'],
            "count": count
        })
        
    # 5. Sort Descending
    leaderboard.sort(key=lambda x: x['count'], reverse=True)
    
    # 6. Assign Rank
    for i, entry in enumerate(leaderboard):
        entry['rank'] = i + 1
        
    return leaderboard

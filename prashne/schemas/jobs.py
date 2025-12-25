from pydantic import BaseModel
from typing import List, Optional

class JobCreate(BaseModel):
    title: str
    description: str
    requirements: List[str] = []
    location: Optional[str] = None
    salary: Optional[str] = None

class MatchRequest(BaseModel):
    jd_text: str
    job_id: Optional[str] = None
    candidate_ids: Optional[List[str]] = None

class MatchResult(BaseModel):
    candidate_id: str
    candidate_name: str
    score: int
    reason: str
    missing_skills: List[str]

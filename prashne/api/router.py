from fastapi import APIRouter
# 1. Update the import to match 'livekit_token'
from prashne.api.routes import auth, admin, resumes, jobs, analytics, interviews, dashboard, livekit_token 

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(admin.router, prefix="/admin", tags=["Super Admin"])
api_router.include_router(resumes.router, prefix="/resumes", tags=["Resumes"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["Jobs"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
api_router.include_router(interviews.router, prefix="/interviews", tags=["Interviews"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])

# 2. Register the router from livekit_token.py
api_router.include_router(livekit_token.router, prefix="/livekit", tags=["LiveKit"])
from fastapi import APIRouter, Depends, HTTPException
from livekit import api
from typing import Dict, Any
from prashne.core.config import settings
from prashne.api.deps import get_current_user

router = APIRouter()

@router.get("/token/{session_id}")
async def get_livekit_token(
    session_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Generates a LiveKit Access Token for a specific interview session.
    """
    try:
        # Create a grant for the room
        grant = api.VideoGrant(
            room_join=True,
            room=session_id,
            can_publish=True,
            can_subscribe=True
        )

        # Create the token
        token = api.AccessToken(
            settings.LIVEKIT_API_KEY,
            settings.LIVEKIT_API_SECRET
        ).with_identity(current_user["sub"]) \
         .with_name(current_user.get("email", "Candidate")) \
         .with_grants(grant)

        return {"token": token.to_jwt(), "server_url": settings.LIVEKIT_URL}

    except Exception as e:
        print(f"LiveKit Token Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate token")
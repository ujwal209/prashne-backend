from fastapi import APIRouter, Request, HTTPException
from livekit import api

router = APIRouter()

# Initialize the WebhookReceiver with your API Key and Secret
# This ensures that only LiveKit can trigger your agent
webhook_receiver = api.WebhookReceiver(
    os.getenv("LIVEKIT_API_KEY"),
    os.getenv("LIVEKIT_API_SECRET")
)

@router.post("/livekit")
async def livekit_webhook(request: Request):
    # Get the raw body and the authorization header
    body = await request.body()
    auth_header = request.headers.get("Authorization")
    
    try:
        # Verify the webhook is actually from LiveKit
        event = webhook_receiver.receive(body.decode("utf-8"), auth_header)
        
        # We only care when a human (candidate) joins
        if event.event == "participant_joined":
            room_name = event.room.name
            participant_identity = event.participant.identity
            
            # Filter out the AI itself so we don't loop
            if not participant_identity.startswith("interviewer-ai"):
                print(f"Candidate {participant_identity} joined room {room_name}")
                # TRIGGER AGENT HERE (See Step 3)
                
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
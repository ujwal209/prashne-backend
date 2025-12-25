from typing import Dict, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from prashne.core.config import settings

security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """
    Validates the Bearer token and returns the decoded payload.
    """
    token = credentials.credentials
    
    try:
        # ------------------------------------------------------------------
        # FIX 1: Explicitly tell PyJWT we expect audience="authenticated"
        # FIX 2: Add leeway=60 to tolerate clock drift (iat error)
        # ------------------------------------------------------------------
        
        # Try validating with the Raw Secret first
        try:
            payload = jwt.decode(
                token, 
                settings.JWT_SECRET, 
                algorithms=["HS256"], 
                audience="authenticated",  # <--- CRITICAL FIX: Matches Supabase 'aud'
                leeway=60                  # <--- CRITICAL FIX: Prevents 'iat' errors
            )
            return payload

        except jwt.InvalidSignatureError:
            # Fallback: Try Base64 Decoded Secret (Common for some Supabase configs)
            import base64
            decoded_secret = base64.b64decode(settings.JWT_SECRET)
            
            payload = jwt.decode(
                token, 
                decoded_secret, 
                algorithms=["HS256"], 
                audience="authenticated", # <--- CRITICAL FIX
                leeway=60                 # <--- CRITICAL FIX
            )
            return payload

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidAudienceError:
        # This gives you a clear error if the 'aud' claim doesn't match
        print("DEBUG ERROR: Token audience mismatch. Expected 'authenticated'.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid audience. Expected 'authenticated'.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        print(f"DEBUG: JWT Validation Failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
import os
import base64
from elevenlabs.client import ElevenLabs
from prashne.core.config import settings

def generate_voice_audio(text: str) -> str:
    """
    Generates audio using ElevenLabs API.
    Returns a Base64 encoded Data URI string (audio/mpeg).
    """
    api_key = settings.ELEVEN_LABS_API_KEY
    if not api_key:
        print("Warning: ElevenLabs API Key missing in settings")
        return None
        
    try:
        client = ElevenLabs(api_key=api_key)
        
        # Generate audio (returns a generator of bytes)
        audio_generator = client.generate(
            text=text,
            voice="Brian", # Professional British voice, or use 'Adam', 'Rachel'
            model="eleven_multilingual_v2"
        )
        
        # Consume the generator to get full byte sequence
        audio_bytes = b"".join(audio_generator)
        
        b64 = base64.b64encode(audio_bytes).decode('utf-8')
        return f"data:audio/mpeg;base64,{b64}"

    except Exception as e:
        print(f"ElevenLabs TTS Error: {e}")
        return None

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    SUPABASE_URL: str
    SUPABASE_KEY: str
    JWT_SECRET: str
    SUPABASE_SERVICE_ROLE_KEY: str
    GROQ_API_KEY: str
    CLOUDINARY_CLOUD_NAME: str
    CLOUDINARY_API_KEY: str
    CLOUDINARY_API_SECRET: str

    class Config:
        env_file = "../../.env"
        # Adjust path if running from server/prashne/main.py or similar
        # Since .env is in /server and config is in /server/prashne/core,
        # relative path from the running app (likely run from /server/) needs consideration.
        # But typically pydantic loads from CWD or explicit path.
        # We will point to the parent of parent folder if we run from prashne module, 
        # but safely we can just look at "../.env" relative to app root or just ".env" if we run from server root.
        # Let's assume the user runs `uvicorn prashne.main:app` from `d:\prashne-fullstack\server`.
        env_file = ".env"

settings = Settings()

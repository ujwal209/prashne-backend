from supabase import create_client, Client
from prashne.core.config import settings

# Standard Client (Anon Key) - For public/RLS protected access
supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

# Admin Client (Service Role Key) - For bypassing RLS and User Management
supabase_admin: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)

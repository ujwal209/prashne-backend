import asyncio
import logging
from livekit.agents import AutoSubscribe, JobContext, WorkerOptions, cli, llm
from livekit.agents.pipeline import VoicePipelineAgent
from livekit.plugins import groq, deepgram, silero
from prashne.core.database import supabase_admin
from prashne.core.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("prashne-worker")

async def entrypoint(ctx: JobContext):
    """
    Main logic when the AI joins a room.
    """
    # 1. Connect to the Room
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    
    # 2. Fetch Context (Resume/Job) from Supabase based on Room Name (Session ID)
    session_id = ctx.room.name
    logger.info(f"Joining session: {session_id}")
    
    try:
        # Fetch detailed context
        res = supabase_admin.table("interview_sessions").select(
            "*, jobs(title, description, requirements), resumes(candidate_name, skills, experience_years)"
        ).eq("id", session_id).single().execute()
        
        data = res.data
        if not data:
            logger.error("Session not found")
            return

        candidate_name = data['resumes']['candidate_name']
        job_title = data['jobs']['title']
        requirements = ", ".join(data['jobs']['requirements'])
        
        # 3. Construct System Prompt
        system_prompt = f"""
        You are Prashne AI, an expert technical interviewer.
        Candidate: {candidate_name}
        Role: {job_title}
        Requirements: {requirements}
        
        RULES:
        - Ask ONE technical question at a time.
        - Wait for the user to answer.
        - If the user is interrupted, STOP speaking immediately.
        - Keep responses concise (under 2 sentences).
        """
        
        initial_ctx = llm.ChatContext().append(
            role="system",
            text=system_prompt
        )

        # 4. Initialize the Voice Agent
        agent = VoicePipelineAgent(
            vad=silero.VAD.load(),           # Voice Activity Detection (Handles Interruption)
            stt=deepgram.STT(),              # Speech-to-Text (Fastest)
            llm=groq.LLM(
                model="llama-3.3-70b-versatile",
                api_key=settings.GROQ_API_KEY
            ),
            tts=deepgram.TTS(),              # Text-to-Speech (Fast & Cheap)
            chat_ctx=initial_ctx
        )

        # 5. Start the Assistant
        participant = await ctx.wait_for_participant()
        agent.start(ctx.room, participant)

        # 6. Greeter Message
        await agent.say(f"Hello {candidate_name}. I am ready to start your interview for the {job_title} role. Shall we begin?", allow_interruptions=True)

    except Exception as e:
        logger.error(f"Worker Error: {e}")

if __name__ == "__main__":
    # Ensure env vars are loaded
    if not settings.LIVEKIT_URL:
        raise ValueError("LIVEKIT_URL is not set")
        
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
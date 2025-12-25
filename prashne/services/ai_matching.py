import json
import asyncio
from typing import Dict, Any, List
from groq import Groq
from prashne.core.config import settings

client = Groq(api_key=settings.GROQ_API_KEY)
MODEL_NAME = "llama-3.3-70b-versatile"

async def match_resume_to_jd(resume_json: Dict[str, Any], jd_text: str) -> Dict[str, Any]:
    """
    Compare a single resume (JSON) against a JD (text) using AI.
    """
    # Defensive programming: ensure resume_json is not overly huge
    resume_str = json.dumps(resume_json, default=str)[:8000] # Truncate to avoid context limit
    jd_snippet = jd_text[:5000]

    system_prompt = """
    You are an expert Technical Recruiter. Compare the Candidate Profile against the Job Description.
    
    1. Analyze overlap in skills, experience, and role alignment.
    2. Be strict. If they lack required core tech or experience years, score below 50.
    
    Return STRICT JSON with these keys:
    - score: integer (0-100)
    - reason: A single concise sentence explaining the score.
    - missing_skills: A list of specific skills/qualifications the candidate lacks based on the JD.
    """

    user_message = f"""
    Job Description:
    {jd_snippet}

    Candidate Profile:
    {resume_str}
    """

    try:
        # Run synchronous Groq call in a thread pool to avoid blocking the event loop
        loop = asyncio.get_event_loop()
        completion = await loop.run_in_executor(None, lambda: client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        ))

        content = completion.choices[0].message.content
        data = json.loads(content)
        
        # Ensure strict typing returns
        return {
            "score": data.get("score", 0),
            "reason": data.get("reason", "Analysis failed"),
            "missing_skills": data.get("missing_skills", [])
        }
    except Exception as e:
        print(f"Match Error: {e}")
        return {
            "score": 0,
            "reason": "AI Analysis Error",
            "missing_skills": []
        }

async def batch_match_resumes(resumes: List[Dict[str, Any]], jd_text: str) -> List[Dict[str, Any]]:
    """
    Process matches concurrently.
    """
    tasks = []
    
    for resume in resumes:
        # Extract relevant fields to keep context small
        # We need the ID for the result, but logic only needs profile data
        profile = resume.get("raw_ai_response", {}) 
        # Add candidate_name if not in raw_ai_response
        if "candidate_name" not in profile:
             profile["candidate_name"] = resume.get("candidate_name", "Unknown")
        if "experience_years" not in profile:
             profile["experience_years"] = resume.get("experience_years", 0)

        tasks.append(match_resume_to_jd(profile, jd_text))
    
    # Run all
    results_data = await asyncio.gather(*tasks)
    
    # Merge results with Resume IDs
    final_results = []
    for i, res in enumerate(resumes):
        match_data = results_data[i]
        final_results.append({
            "candidate_id": res["id"],
            "candidate_name": res.get("candidate_name", "Unknown"),
            **match_data
        })
        
    # Sort by score descending
    final_results.sort(key=lambda x: x["score"], reverse=True)
    
    return final_results

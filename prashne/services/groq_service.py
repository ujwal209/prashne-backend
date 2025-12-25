import json
from groq import Groq
from prashne.core.config import settings
from typing import Dict, Any

client = Groq(api_key=settings.GROQ_API_KEY)

def parse_resume_with_ai(text: str) -> dict:
    """
    Parses resume text into structured JSON using Groq LLM.
    """
    prompt = f"""
    You are an expert HR Parser. Extract these exact fields from the resume text below:
    - full_name (string)
    - email (string)
    - phone (string)
    - skills (list of strings)
    - experience_years (number, estimate if needed)
    - education (list of objects with degree, school, year)
    - summary (short professional summary)

    Resume Text:
    {text[:15000]}  # Truncate to safe limit

    Return ONLY valid JSON. No markdown formatting.
    """

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            response_format={"type": "json_object"}
        )
        
        result = completion.choices[0].message.content
        return json.loads(result)
    except Exception as e:
        print(f"Groq API Error: {e}")
        return {"error": "AI Parsing Failed", "details": str(e)}

def generate_job_description_with_ai(prompt: str) -> Dict[str, Any]:
    """
    Generate a job description from a user prompt using Groq Llama 3.
    Returns structured JSON: title, description, requirements (list), salary, location.
    """
    system_prompt = """
    You are an expert HR Recruiter. Generate a detailed Job Description based on the user's request.
    Output purely JSON with these keys:
    - title: A professional job title
    - description: A compelling 2-3 paragraph description
    - requirements: A list of 5-8 bullet points (technical & soft skills)
    - salary: An estimated salary range (e.g. '$120k - $150k')
    - location: Suggested location type (e.g. 'Remote', 'Hybrid', or 'San Francisco, CA')

    Do not include any preamble. Just the JSON.
    """

    try:
        completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Create a job description for: {prompt}"}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.7,
            response_format={"type": "json_object"}
        )
        
        content = completion.choices[0].message.content
        return json.loads(content)
    except Exception as e:
        print(f"Groq JD Gen Error: {e}")
        return {"error": str(e)}

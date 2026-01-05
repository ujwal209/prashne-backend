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
def conduct_interview(
    jd_text: str, 
    resume_text: str, 
    history: list, 
    last_answer: str
) -> Dict[str, Any]:
    """
    Core AI Interview Logic.
    Decides the next question based on the candidate's last answer, the Job Description, and the Resume.
    """
    
    system_prompt = f"""
    You are an expert Technical Interviewer conducting a real-time interview.
    
    Context:
    - Job Description: {jd_text[:4000]}
    - Candidate Resume: {resume_text[:4000]}
    
    Goal:
    - Assess the candidate's fit for the role in a ~15 minute session (approx 5-8 questions).
    - Be adaptive: 
      - If the candidate answers CORRECTLY and deeply, ask a harder follow-up or move to a more complex topic.
      - If they struggle, ask a simpler question or pivot to a strength area from their resume.
    - Maintain a professional, conversational tone.
    
    Current State:
    - You have already asked some questions.
    - The candidate just provided an answer.
    
    Task:
    1. Evaluate the candidate's last answer (Hidden-School-Grade: 1-10).
    2. Provide short feedback (internal use).
    3. Formulate the NEXT question to ask the candidate.
    
    Output JSON ONLY:
    {{
        "evaluation_score": 7,
        "feedback": "Good understanding of React hooks, but missed the dependency array nuance.",
        "next_question": "That's a solid start. Can you explain a scenario where omitting the dependency array might cause an infinite loop?",
        "is_interview_over": false
    }}
    
    If you feel you have enough signal or 8 questions have passed, set "is_interview_over": true and say "Thank you for your time..." in next_question.
    """

    # Format history for the LLM
    messages = [{"role": "system", "content": system_prompt}]
    
    # Add recent history context (limit to last 10 turns to save context window)
    for turn in history[-10:]: 
        role = "assistant" if turn['sender'] == 'ai' else "user"
        messages.append({"role": role, "content": turn['message_text']})
        
    # Add the latest user answer if not already in history
    if last_answer:
        messages.append({"role": "user", "content": last_answer})

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.6,
            response_format={"type": "json_object"}
        )
        return json.loads(completion.choices[0].message.content)
    except Exception as e:
        print(f"Interview Logic Error: {e}")
        return {
            "evaluation_score": 0,
            "feedback": "Error processing answer.",
            "next_question": "I apologize, I missed that. Could you repeat?",
            "is_interview_over": False
        }

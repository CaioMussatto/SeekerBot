import os
import json
from openai import OpenAI

class AIManager:
    """
    A unified interface to interact with Large Language Models (LLMs)
    for resume tailoring and job matching analysis.
    """

    def __init__(self, base_url: str = None, api_key: str = None, model_name: str = None):
        # Setup to automatically pull from environment variables (like Groq or OpenAI)
        # Using Groq's base URL and Llama 3 as standard for fast/free evaluation if not specified
        self.client = OpenAI(
            base_url=base_url or os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1"),
            api_key=api_key or os.getenv("GROQ_API_KEY", os.getenv("OPENAI_API_KEY", "no-key-needed"))
        )
        self.model_name = model_name or os.getenv("LLM_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct")

    def evaluate_job_match(self, master_cv: str, job_description: str) -> dict:
        """
        Compares the CV text against a job description and returns a strict match score and rationale.
        """
        # =====================================================================
        # THE ELITE RECRUITER PROMPT
        # =====================================================================
        system_prompt = (
            "You are a strict, elite Tech Recruiter and an advanced ATS screening AI. "
            "Evaluate the Candidate's CV against the Job Description. "
            "Calculate the 'score' (integer 0-100) strictly based on this rubric:\n"
            "- 40%: Hard Skills & Tech Stack match (Do they have the exact tools/languages required?).\n"
            "- 40%: Experience level match (Penalize heavily if the job requires Senior/Lead experience (e.g., 5+ years) and the candidate is Junior/Mid).\n"
            "- 20%: Domain knowledge, education, and soft skills.\n\n"
            "Be extremely critical. A score above 80 should be rare and reserved ONLY for candidates who meet almost all requirements.\n\n"
            "Return ONLY a valid JSON object with EXACTLY these two keys:\n"
            "1. 'score': <int>\n"
            "2. 'rationale': <A short paragraph in Portuguese (max 3 sentences) explaining the main reason for the score. "
            "Focus on the biggest gap or the strongest match. Be direct and professional.>"
        )

        # Truncate CV slightly if it's monstrously huge to prevent Token Limits (approx 15000 chars)
        safe_cv = master_cv[:15000] if master_cv else ""
        
        user_prompt = (
            f"--- CANDIDATE CV ---\n{safe_cv}\n\n"
            f"--- TARGET JOB DESCRIPTION ---\n{job_description}"
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1, # Keep it low so the AI is analytical, not creative
                response_format={"type": "json_object"} 
            )
            
            result_str = response.choices[0].message.content
            return json.loads(result_str)
            
        except Exception as e:
            error_msg = str(e).lower()
            print(f"❌ AI API Error: {error_msg}")
            
            # CRITICAL: If we hit a Rate Limit (429), we MUST raise the error
            # so the web interface can stop and warn the user.
            if "429" in error_msg or "rate limit" in error_msg or "too many requests" in error_msg:
                raise Exception("API_RATE_LIMIT_429")
                
            # For other generic errors, we return a 0 so the rest of the jobs can still be processed
            return {"score": 0, "rationale": "Falha ao gerar avaliação devido a um erro na IA."}


# ==============================================================================
# SECTION: WRAPPER FOR IN-MEMORY WEB PROCESSING
# ==============================================================================

def evaluate_jobs_in_memory(jobs_list: list, cv_text: str) -> list:
    """
    Takes a list of JobInMemory objects and the extracted CV text.
    Runs them through the AI and populates their score and rationale.
    """
    if not jobs_list:
        return []
        
    ai = AIManager()
    
    for idx, job in enumerate(jobs_list):
        print(f"   [{idx+1}/{len(jobs_list)}] Scoring: {job.title} at {job.company}...")
        
        # If there's no description, we can't really score it properly
        jd = job.description if job.description and len(job.description) > 50 else job.title
        
        # Evaluate
        result = ai.evaluate_job_match(cv_text, jd)
        
        # Populate the in-memory object
        job.match_score = result.get("score", 0)
        job.rationale = result.get("rationale", "Sem justificativa.")
        
    return jobs_list
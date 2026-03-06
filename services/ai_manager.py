import os
import json
from openai import OpenAI

class AIManager:
    """
    A unified interface to interact with Large Language Models (LLMs)
    for resume tailoring and job matching analysis.
    """

    def __init__(self, base_url: str, api_key: str = "no-key-needed", model_name: str = "meta-llama/llama-4-scout-17b-16e-instruct"):
        self.client = OpenAI(
            base_url=base_url,
            api_key=api_key
        )
        self.model_name = model_name

    def generate_master_cv(self, cv_texts: list[str]) -> str:
        """
        Merges multiple resume texts into a single, comprehensive Master CV.
        """
        system_prompt = (
            "You are an Expert Career Coach and IT Recruiter. "
            "I will provide you with text extracted from different versions of a candidate's resume. "
            "Your task is to merge them into a single, highly professional 'Master CV'. "
            "Remove all redundancies, combine complementary information, and organize it clearly into standard sections: "
            "Professional Summary, Core Skills, Professional Experience, Education, and Languages. "
            "CRITICAL RULE: Keep the output strictly in the original language of the documents (Portuguese) and use a professional tone."
        )

        combined_text = "\n\n--- NEXT CV VERSION ---\n\n".join(cv_texts)
        user_prompt = f"Here are the CV versions to merge:\n\n{combined_text}"

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2 
            )
            return response.choices[0].message.content
            
        except Exception as e:
            return f"Error generating Master CV: {str(e)}"

    def evaluate_job_match(self, master_cv: str, job_description: str) -> dict:
        """
        Compares the Master CV against a job description and returns a strict match score and rationale.
        """
        # =====================================================================
        # THE ELITE RECRUITER PROMPT
        # =====================================================================
        system_prompt = (
    "You are an elite, unforgiving Tech Recruiter and a highly advanced ATS (Applicant Tracking System) screening algorithm. "
    "Your objective is to ruthlessly evaluate the provided Candidate Master CV against the Target Job Description. "
    "Calculate the 'score' (integer 0-100) strictly based on this rubric:\n\n"
    "1. 40%: Hard Skills & Tech Stack match. (Strictly check for exact matches in languages, frameworks, and tools. Deduct points for every missing mandatory skill).\n"
    "2. 40%: Seniority & Experience Level. (CRITICAL RULE: If the job demands Senior/Lead or 5+ years of experience, and the candidate is Junior/Mid or lacks explicit industry years, apply a MASSIVE PENALTY. Academic experience does NOT count as senior industry experience unless explicitly stated in the job description).\n"
    "3. 20%: Domain Knowledge, Education, and Soft Skills.\n\n"
    "CALIBRATION RULE: Be extremely critical. Do not be generous. An average match should score between 40-60. Scores above 80 must be exceptionally rare, reserved ONLY for candidates who possess a perfect 1:1 match in BOTH the exact tech stack and the required years of experience.\n\n"
    "OUTPUT RULE: Return ONLY a raw, valid JSON object. DO NOT wrap the output in markdown blocks (e.g., no ```json). DO NOT add introductory or concluding text. "
    "The JSON must have EXACTLY these two keys:\n"
    "{\n"
    "  \"score\": <int>,\n"
    "  \"rationale\": \"<A short, punchy paragraph in Portuguese (max 3 sentences) explaining the score. Focus strictly on the biggest missing gap (skills/seniority) or the strongest exact match. Be direct, analytical, and professional.>\"\n"
    "}"
        )

        user_prompt = (
            f"--- CANDIDATE MASTER CV ---\n{master_cv}\n\n"
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
            print(f"❌ AI Evaluation Error: {str(e)}")
            return {"score": 0, "rationale": "Falha ao gerar avaliação devido a um erro na IA."}
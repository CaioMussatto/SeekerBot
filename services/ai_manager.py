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
            "You are a strict, elite Tech Recruiter and an advanced ATS screening AI. "
            "Evaluate the Candidate's Master CV against the Job Description. "
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
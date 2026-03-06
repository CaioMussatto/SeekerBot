import os
from openai import OpenAI

def get_expanded_terms(base_term: str) -> list:
    """
    Uses the Groq API (Llama) to expand a job search term into 5 highly relevant variations.
    Returns a list of strings.
    """
    api_key = os.getenv("GROQ_API_KEY")
    
    if not api_key:
        print("⚠️ GROQ_API_KEY not found. Defaulting to the original search term.")
        return [base_term]

    client = OpenAI(
        base_url="https://api.groq.com/openai/v1",
        api_key=api_key
    )

    # Strict English prompt to ensure the LLM outputs ONLY a comma-separated list
    system_prompt = (
      "You are an elite Senior Tech Recruiter and an ATS (Applicant Tracking System) algorithm expert. "
    "Your objective is to maximize job search visibility by expanding a single job title into EXACTLY 5 high-conversion, real-world variations used by companies in actual job postings. "
    "CRITICAL RULES: "
    "1. TARGETING: Focus strictly on highly searchable, direct market synonyms. Do not invent broad or unrelated categories. "
    "2. LANGUAGE BILINGUAL BALANCE: If the user's input is in Portuguese, you MUST provide 3 highly accurate Portuguese variations AND exactly 2 industry-standard English variations (e.g., if input is 'Cientista de Dados', you must include 'Data Scientist'). "
    "3. ABSOLUTE FORMATTING RULE: Return ONLY a raw, comma-separated list of the 9 terms. NO quotes, NO bullet points, NO introductory text, NO periods at the end, NO line breaks. JUST the words separated by commas."
    )

    try:
        print(f"🧠 Querying AI to expand search term: '{base_term}'...")
        response = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Term: {base_term}"}
            ],
            temperature=0.3, # Low temperature for strict compliance
            max_tokens=60
        )
        
        ai_output = response.choices[0].message.content.strip()
        expanded_terms = [term.strip() for term in ai_output.split(',')]
        
        final_list = [base_term]
        
        for term in expanded_terms:
            if term and term.lower() not in [t.lower() for t in final_list]:
                final_list.append(term)
                
        # Ensure we return a maximum of 10 terms
        final_list = final_list[:10]
        
        print(f"✅ Expanded terms: {final_list}")
        return final_list

    except Exception as e:
        print(f"❌ Error expanding terms with AI: {e}")
        return [base_term]
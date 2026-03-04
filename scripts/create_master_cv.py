import os
from dotenv import load_dotenv
from core.database import SessionLocal
from models.resume import Resume
from services.ai_manager import AIManager

# Load environment variables
load_dotenv()

def build_master_cv():
    """
    Fetches all raw CVs from the database, sends them to the AI to generate 
    a Master CV, and saves the final result back to the database.
    """
    db = SessionLocal()
    print("🔍 Fetching raw CVs from the database...")
    
    try:
        # 1. Fetch resumes that are NOT the master yet
        raw_cvs = db.query(Resume).filter(Resume.is_master == False).all()
        
        if not raw_cvs:
            print("⚠️ No raw CVs found in the database. Run load_cvs.py first.")
            return
        
        print(f"✅ Found {len(raw_cvs)} CV(s). Preparing to send to AI...")
        
        # Extract just the text content into a list
        cv_texts = [cv.content for cv in raw_cvs]
        
        # 2. Initialize our AI Manager
        api_key = os.getenv("GROQ_API_KEY")
        ai = AIManager(
            base_url="https://api.groq.com/openai/v1",
            api_key=api_key,
            model_name="meta-llama/llama-4-scout-17b-16e-instruct"
        )
        
        print("🧠 AI is processing and merging your CVs. This might take 10-20 seconds...")
        # 3. Call the AI
        master_cv_text = ai.generate_master_cv(cv_texts)
        
        if master_cv_text.startswith("Error"):
            print(f"❌ Failed to generate Master CV: {master_cv_text}")
            return
        
        # 4. Save the new Master CV to the database
        print("💾 Saving the new Master CV to the database...")
        new_master_cv = Resume(
            title="Master_AI_CV",
            content=master_cv_text,
            is_master=True # This flags it as our main resume for future job matching!
        )
        
        db.add(new_master_cv)
        db.commit()
        print("🎉 Success! Master CV generated and saved to the database.")
        
        # Print a small preview
        print("\n--- MASTER CV PREVIEW ---")
        print(master_cv_text[:800] + "...\n\n(truncated for preview)")
        print("-------------------------")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Database Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    build_master_cv()
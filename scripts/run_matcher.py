import os
import time
from dotenv import load_dotenv
from core.database import SessionLocal
from models.job import Job
from models.resume import Resume
from services.ai_manager import AIManager

# Load environment variables
load_dotenv()

def run_job_matcher():
    """
    Fetches the Master CV and all unscored jobs from the database,
    evaluates them using the AI Manager, and saves the scores back.
    """
    db = SessionLocal()
    
    print("🧠 Initializing AI Matcher...")
    
    try:
        # 1. Fetch the Master CV
        master_cv_record = db.query(Resume).filter(Resume.is_master == True).first()
        
        if not master_cv_record:
            print("❌ Error: No Master CV found in the database. Run create_master_cv.py first.")
            return
            
        master_cv = master_cv_record.content
        
        # 2. Fetch jobs that haven't been scored yet
        unscored_jobs = db.query(Job).filter(Job.match_score == None).all()
        
        if not unscored_jobs:
            print("✅ All jobs have already been scored. Nothing to do!")
            return
            
        print(f"🔍 Found {len(unscored_jobs)} jobs waiting for evaluation.\n")
        
        # 3. Initialize AI Manager using EXACTLY the Groq credentials from your .env
        api_key = os.getenv("GROQ_API_KEY")
        
        if not api_key:
            print("❌ Error: GROQ_API_KEY not found in .env file.")
            return
            
        ai = AIManager(
            base_url="https://api.groq.com/openai/v1",
            api_key=api_key,
            model_name="meta-llama/llama-4-scout-17b-16e-instruct"
        )
        
        # 4. Process each job
        processed_count = 0
        
        for job in unscored_jobs:
            print(f"⚙️  Evaluating: '{job.title}' at {job.company}...")
            
            # Call the AI
            evaluation = ai.evaluate_job_match(master_cv, job.description)
            
            # Update the job record
            job.match_score = evaluation.get("score", 0)
            job.match_rationale = evaluation.get("rationale", "No rationale provided.")
            
            print(f"   🎯 Score: {job.match_score}/100")
            print(f"   📝 Rationale: {job.match_rationale}\n")
            
            processed_count += 1
            
            # Commit every 5 jobs to save progress incrementally
            if processed_count % 5 == 0:
                db.commit()
                print("   💾 Progress saved to database.")
                
            # Rate limiting protection (avoid API spam)
            time.sleep(2)
            
        # Final commit for any remaining jobs
        db.commit()
        
        print("="*50)
        print(f"🎉 MATCHING COMPLETE!")
        print(f"📈 Successfully evaluated {processed_count} jobs.")
        print("="*50)
        
    except Exception as e:
        db.rollback()
        print(f"❌ Database or execution error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    run_job_matcher()
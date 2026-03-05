import os
import time
from flask import Flask, render_template, request, redirect, url_for
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import markdown
from dotenv import load_dotenv

# --- Local Project Imports ---
# Ensuring imports match your exact folder structure
from core.database import DATABASE_URL
from models.job import Job
from services.seeker import fetch_and_save_jobs
from scripts.run_matcher import run_job_matcher
from services.term_expander import get_expanded_terms  # <-- IMPORTING THE NEW AI EXPANDER

# Load environment variables from .env file
load_dotenv()

# Initialize Flask Application
app = Flask(__name__)

# Toggle for Database Usage (Defaults to True as the app relies heavily on it)
USE_DB = os.getenv("USE_DB", "True") == "True"

def get_session():
    """
    Creates and returns a new SQLAlchemy database session.
    Ensures a clean connection URL is used for the engine.
    """
    clean_url = DATABASE_URL.split("?")[0] if DATABASE_URL else "sqlite:///jobs_data.db"
    engine = create_engine(clean_url)
    Session = sessionmaker(bind=engine)
    return Session()

@app.route('/')
def index():
    """
    Main route. Renders the dashboard with AI-filtered jobs.
    Only shows jobs that have a match_score >= min_score (default 80),
    and have not been applied to or rejected.
    """
    # Get the minimum score threshold from URL parameters, default to 80
    min_score = int(request.args.get('min_score', 80))
    jobs = []
    
    if USE_DB:
        try:
            session = get_session()
            
            # Fetch jobs that passed the AI evaluation threshold and are pending action
            jobs = session.query(Job).filter(
                Job.applied == False, 
                Job.rejected == False,
                Job.match_score != None,
                Job.match_score >= min_score
            ).order_by(Job.match_score.desc(), Job.id.desc()).all() # Highest scores first
            
            # Process descriptions with Markdown and format dates for the frontend
            for job in jobs:
                job.formatted_description = markdown.markdown(job.description or "")
                
                if hasattr(job.created_at, 'strftime'):
                    job.display_created_at = job.created_at.strftime('%d/%m/%Y %H:%M')
                else:
                    job.display_created_at = str(job.created_at)
                    
            session.close()
        except Exception as e:
            print(f"❌ Error in Index route: {e}")
    
    return render_template('index.html', jobs=jobs, can_use_db=USE_DB, mode="AI Filtered Mode")


@app.route('/refresh', methods=['POST'])
def refresh():
    """
    Triggers the scraper to fetch new jobs from the web, 
    automatically saves them to the DB, and then runs the AI Matcher.
    Applies the PRG (Post/Redirect/Get) pattern to prevent state loss.
    Now enhanced with AI Query Expansion to search for multiple job title variations.
    """
    # Extract parameters from the frontend form
    base_term = request.form.get('term', 'Engenheiro')
    min_score = int(request.form.get('min_score', 80))
    filter_words = request.form.get('filter_words', '')
    location = request.form.get('location', 'Brazil')
    results_wanted = int(request.form.get('results_wanted', 60))
    hours_old = int(request.form.get('hours_old', 24))
    
    # 1. Expand the search term using AI
    expanded_terms = get_expanded_terms(base_term)
    
    # Calculate how many results to fetch per term to avoid overwhelming the scraper
    # e.g., if user wants 60 results and we have 5 terms, we fetch 12 per term.
    # Minimum of 10 to ensure the scraper has enough surface area.
    results_per_term = max(10, results_wanted // len(expanded_terms))
    
    print(f"\n🚀 Starting Expanded Search for: {base_term}")
    print(f"🎯 Target total results: {results_wanted} (Scraping ~{results_per_term} per term)")
    
    # 2. Fetch jobs from the web iterating over all expanded terms
    for index, current_term in enumerate(expanded_terms):
        print(f"\n[{index + 1}/{len(expanded_terms)}] 👉 Executing search for: '{current_term}'")
        
        fetch_and_save_jobs(
            term=current_term, 
            location=location,
            results_wanted=results_per_term,
            hours_old=hours_old,
            filter_words=filter_words
        )
        
        # Anti-Ban Protection: Sleep between requests (except after the last one)
        if index < len(expanded_terms) - 1:
            print("⏳ Sleeping for 15 seconds to prevent IP rate-limiting...")
            time.sleep(15)

    # 3. RUN AI AUTOMATICALLY
    # Now that new jobs from all terms are in the database, run the AI to evaluate them.
    if USE_DB:
        print("\n🧠 Starting AI to evaluate all newly pending jobs...")
        try:
            run_job_matcher()
        except Exception as e:
            print(f"❌ Error running AI automatically: {e}")

    # 4. Redirect back to the index, keeping the score filter alive in the URL
    return redirect(url_for('index', min_score=min_score))


@app.route('/run_ai')
def run_ai_manual():
    """
    Manual trigger for the AI evaluation process.
    Useful if the automatic process was interrupted or failed due to API limits.
    """
    if USE_DB:
        try:
            print("🧠 Manually triggering AI evaluation...")
            run_job_matcher()
        except Exception as e:
            print(f"❌ Error running AI manually: {e}")
            
    # Redirects back to the exact page the user was on (preserves active filters)
    return redirect(request.referrer or url_for('index'))


@app.route('/apply/<int:job_id>')
def apply(job_id):
    """
    Toggles the 'applied' status of a job. 
    If marked as applied, it will disappear from the main dashboard.
    """
    if USE_DB:
        session = get_session()
        # FIXED: Using session.get() instead of the legacy query(Job).get()
        job = session.get(Job, job_id)
        if job:
            job.applied = not job.applied
            session.commit()
        session.close()
        
    # Redirects back to the exact page the user was on (preserves active filters)
    return redirect(request.referrer or url_for('index'))


@app.route('/delete/<int:job_id>')
def delete_job(job_id):
    """
    Performs a 'Soft Delete' by marking the job as rejected.
    This keeps the job in the database (preventing the scraper from fetching it again)
    but hides it from the user interface.
    """
    if USE_DB:
        session = get_session()
        # FIXED: Using session.get() instead of the legacy query(Job).get()
        job = session.get(Job, job_id)
        if job:
            job.rejected = True 
            session.commit()
        session.close()
        
    # Redirects back to the exact page the user was on (preserves active filters)
    return redirect(request.referrer or url_for('index'))


if __name__ == '__main__':
    # Start the Flask web server
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port, debug=True)
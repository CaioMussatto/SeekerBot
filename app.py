import os
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
    """
    # Extract parameters from the frontend form
    term = request.form.get('term', 'Engenheiro')
    min_score = int(request.form.get('min_score', 80))
    filter_words = request.form.get('filter_words', '')
    location = request.form.get('location', 'Brazil')
    results_wanted = int(request.form.get('results_wanted', 60))
    hours_old = int(request.form.get('hours_old', 24))
    
    # 1. Fetch jobs from the web using exactly the parameters expected by services/seeker.py
    # Note: fetch_and_save_jobs handles DB insertion automatically internally.
    fetch_and_save_jobs(
        term=term, 
        location=location,
        results_wanted=results_wanted,
        hours_old=hours_old,
        filter_words=filter_words
    )

    # 2. RUN AI AUTOMATICALLY
    # Now that new jobs are in the database, we run the AI to evaluate them.
    if USE_DB:
        print("🧠 Starting AI to evaluate pending jobs...")
        try:
            run_job_matcher()
        except Exception as e:
            print(f"❌ Error running AI automatically: {e}")

    # 3. Prepare the job list for display (Reading from Database)
    display_jobs = []
    if USE_DB:
        session = get_session()
        
        # Display ONLY jobs that meet the AI threshold
        display_jobs = session.query(Job).filter(
            Job.rejected == False,
            Job.applied == False,
            Job.match_score != None,
            Job.match_score >= min_score
        ).order_by(Job.match_score.desc(), Job.id.desc()).all()
        
        for j in display_jobs:
            j.formatted_description = markdown.markdown(j.description or "")
            if hasattr(j.created_at, 'strftime'):
                j.display_created_at = j.created_at.strftime('%d/%m/%Y %H:%M')
                
        session.close()

    # Render the template with the newly fetched and filtered jobs
    return render_template('index.html', jobs=display_jobs, can_use_db=USE_DB, mode=f"Threshold: {min_score}%")


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
            
    # Redirects back to home page after finishing
    return redirect(url_for('index'))


@app.route('/apply/<int:job_id>')
def apply(job_id):
    """
    Toggles the 'applied' status of a job. 
    If marked as applied, it will disappear from the main dashboard.
    """
    if USE_DB:
        session = get_session()
        job = session.query(Job).get(job_id)
        if job:
            job.applied = not job.applied
            session.commit()
        session.close()
    return redirect(url_for('index'))


@app.route('/delete/<int:job_id>')
def delete_job(job_id):
    """
    Performs a 'Soft Delete' by marking the job as rejected.
    This keeps the job in the database (preventing the scraper from fetching it again)
    but hides it from the user interface.
    """
    if USE_DB:
        session = get_session()
        job = session.query(Job).get(job_id)
        if job:
            job.rejected = True 
            session.commit()
        session.close()
    return redirect(url_for('index'))


if __name__ == '__main__':
    # Start the Flask web server
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port, debug=True)
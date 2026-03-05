import os
import time
from flask import Flask, render_template, request, session, flash
import markdown
from dotenv import load_dotenv
from pypdf import PdfReader

# --- Local Project Imports ---
# Notice we removed database imports completely!
# Note: We will need to update seeker.py and ai_manager.py in the next steps 
# to return data instead of saving to a DB.
from services.seeker import fetch_jobs_in_memory
from services.ai_manager import evaluate_jobs_in_memory
from services.term_expander import get_expanded_terms

# Load environment variables from .env file
load_dotenv()

# Initialize Flask Application
app = Flask(__name__)
# Secret key is required to use Flask 'session' (to keep the CV in memory temporarily)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "super-secret-bioinfo-key")

@app.route('/')
def index():
    """
    Main route. Renders the initial dashboard.
    Since there's no database, it loads an empty state until the user performs a search.
    """
    # Check if the user already has a CV stored in their active session
    has_cv_in_memory = 'cv_text' in session
    
    return render_template(
        'index.html', 
        jobs=[], 
        has_cv_in_memory=has_cv_in_memory
    )

@app.route('/search', methods=['POST'])
def search_and_evaluate():
    """
    Handles the stateless flow:
    1. Receives uploaded CV(s) and extracts text (saving to temporary session).
    2. Expands search terms using AI (max 5).
    3. Scrapes jobs across platforms into memory.
    4. Evaluates jobs against the CV text using AI.
    5. Returns the filtered results directly to the frontend.
    """
    # --------------------------------------------------------------------------
    # 1. HANDLE CV UPLOADS & TEXT EXTRACTION
    # --------------------------------------------------------------------------
    cv_files = request.files.getlist('cv_files')
    extracted_cv_text = ""
    
    # If the user uploaded new files, parse them
    if cv_files and cv_files[0].filename != '':
        for file in cv_files:
            if file.filename.lower().endswith('.pdf'):
                try:
                    reader = PdfReader(file)
                    for page in reader.pages:
                        extracted_cv_text += page.extract_text() + "\n\n"
                except Exception as e:
                    print(f"❌ Error reading PDF {file.filename}: {e}")
        
        # Save the combined text to the user's temporary browser session
        if extracted_cv_text.strip():
            session['cv_text'] = extracted_cv_text
            
    # If no new files were uploaded, try to use the one already in the session
    else:
        extracted_cv_text = session.get('cv_text', '')

    # Guard clause: We cannot run the AI without a CV
    if not extracted_cv_text.strip():
        flash("Please upload at least one PDF resume to proceed.", "error")
        return render_template('index.html', jobs=[], has_cv_in_memory=False)

    # --------------------------------------------------------------------------
    # 2. GET FORM PARAMETERS
    # --------------------------------------------------------------------------
    base_term = request.form.get('term', 'Engenheiro')
    min_score = int(request.form.get('min_score', 80)) # User defined threshold
    filter_words = request.form.get('filter_words', '')
    location = request.form.get('location', 'Brazil')
    results_wanted = int(request.form.get('results_wanted', 30))
    hours_old = int(request.form.get('hours_old', 24))

    # --------------------------------------------------------------------------
    # 3. EXPAND TERMS (LIMITED TO 5)
    # --------------------------------------------------------------------------
    expanded_terms = get_expanded_terms(base_term)
    
    # FORCE CAP AT 5 TERMS to prevent taking too long or hitting rate limits
    expanded_terms = expanded_terms[:5] 
    
    results_per_term = max(10, results_wanted // len(expanded_terms))
    
    print(f"\n🚀 Stateless Search Started for: {base_term}")
    print(f"🎯 Threshold: {min_score} | Target results: {results_wanted}")

    # --------------------------------------------------------------------------
    # 4. SCRAPE JOBS INTO MEMORY
    # --------------------------------------------------------------------------
    all_scraped_jobs = []
    
    for index, current_term in enumerate(expanded_terms):
        print(f"\n[{index + 1}/{len(expanded_terms)}] 👉 Scraping: '{current_term}'")
        
        # We will modify seeker.py to return a list of dictionaries/objects, not save to DB
        jobs_found = fetch_jobs_in_memory(
            term=current_term, 
            location=location,
            results_wanted=results_per_term,
            hours_old=hours_old,
            filter_words=filter_words
        )
        all_scraped_jobs.extend(jobs_found)
        
        if index < len(expanded_terms) - 1:
            time.sleep(10) # Reduced sleep a bit for better web UX

    if not all_scraped_jobs:
        flash("No jobs found with these parameters. Try expanding your search.", "warning")
        return render_template('index.html', jobs=[], has_cv_in_memory=True)

    # --------------------------------------------------------------------------
    # 5. AI EVALUATION & ERROR HANDLING (RATE LIMITS)
    # --------------------------------------------------------------------------
    all_scraped_jobs = all_scraped_jobs[:results_wanted]
    
    evaluated_jobs = []
    print(f"\n🧠 Evaluating {len(all_scraped_jobs)} jobs against uploaded CV...")
    
    try:
        # We will modify ai_manager.py to accept a list of jobs and the CV text directly
        evaluated_jobs = evaluate_jobs_in_memory(all_scraped_jobs, extracted_cv_text)
    
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "rate limit" in error_msg.lower():
            flash("🤖 AI Rate Limit Reached! The Groq API is overwhelmed. Please wait a few minutes and try again.", "error")
        else:
            flash(f"🤖 AI Evaluation Error: {error_msg}", "error")
        print(f"❌ AI Error: {error_msg}")
        return render_template('index.html', jobs=[], has_cv_in_memory=True)

    # --------------------------------------------------------------------------
    # 6. APPLY THRESHOLD & FORMATTING
    # --------------------------------------------------------------------------
    final_jobs = []
    for job in evaluated_jobs:
        if job.match_score and job.match_score >= min_score:
            # Process markdown for the web
            job.formatted_description = markdown.markdown(job.description or "")
            final_jobs.append(job)
            
    # Sort highest scores first
    final_jobs.sort(key=lambda x: x.match_score, reverse=True)

    print(f"✅ Finished! {len(final_jobs)} jobs passed the >= {min_score} threshold.")

    return render_template('index.html', jobs=final_jobs, has_cv_in_memory=True)

@app.route('/clear_cv', methods=['POST'])
def clear_cv():
    """Route to let the user flush their CV from the active session."""
    session.pop('cv_text', None)
    flash("CV removed from memory.", "info")
    return render_template('index.html', jobs=[], has_cv_in_memory=False)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port, debug=True)
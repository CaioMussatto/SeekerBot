import os
from datetime import datetime
from jobspy import scrape_jobs
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Job, DATABASE_URL

def fetch_and_save_jobs(term, google_term, save_to_db=False, results_wanted=30, hours_old=336, filter_words="", location="Brazil"):
    CAN_WRITE = os.environ.get("USE_DB", "True") == "True"
    if not CAN_WRITE:
        save_to_db = False

    try:
        jobs_df = scrape_jobs(
            site_name=["google", "linkedin", "indeed"],
            search_term=term,
            google_search_term=google_term,
            location=location,
            results_wanted=int(results_wanted),
            hours_old=int(hours_old),
            country_indeed="brazil",
            linkedin_fetch_description=True,
            enforce_desktop=True
        )

        if jobs_df is None or jobs_df.empty:
            return []
        
        jobs_list = jobs_df.to_dict('records')

    except Exception as e:
        print(f"❌ Erro: {e}")
        return []

    found_jobs = []
    keywords = [w.strip().lower() for w in filter_words.split(",") if w.strip()]

    for row in jobs_list:
        title = str(row.get('title', '')).lower()
        desc = str(row.get('description', '')).lower()
        full_text = title + " " + desc
        
        if keywords:
            if not any(word in full_text for word in keywords): continue
        else:
            if term.lower() not in title: continue

        # --- PADRONIZAÇÃO DE DATA ---
        raw_published = row.get('date_posted')
        published_formatted = "N/A"
        
        if raw_published:
            try:
                # Se vier como string YYYY-MM-DD, converte para DD/MM/YYYY
                dt = datetime.strptime(str(raw_published), '%Y-%m-%d')
                published_formatted = dt.strftime('%d/%m/%Y')
            except:
                published_formatted = str(raw_published) # Fallback caso o formato mude

        job_dict = {
            "title": row.get('title'),
            "company": row.get('company'),
            "location": row.get('location'),
            "link": row.get('job_url'),
            "description": row.get('description') or "Sem descrição.",
            "source": row.get('site'),
            "published_at": published_formatted,
            "created_at": datetime.utcnow()
        }
        found_jobs.append(job_dict)

    if save_to_db and CAN_WRITE:
        engine = create_engine(DATABASE_URL)
        Session = sessionmaker(bind=engine)
        session = Session()
        try:
            for j in found_jobs:
                exists = session.query(Job).filter(Job.link == j['link']).first()
                if not exists:
                    session.add(Job(**j))
            session.commit()
        finally:
            session.close()

    return found_jobs
import os
from dotenv import load_dotenv
from jobspy import scrape_jobs
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Job, DATABASE_URL

load_dotenv()

def fetch_and_save_jobs(term, google_term, save_to_db=False, results_wanted=20, hours_old=336, filter_words=""):
    print(f"🚀 Buscando: '{term}' | Filtro: '{filter_words}' | Salvar: {save_to_db}")
    
    try:
        jobs = scrape_jobs(
            site_name=["linkedin", "indeed", "google"],
            search_term=term,
            google_search_term=google_term,
            location="Brazil", 
            country_indeed="brazil", 
            results_wanted=int(results_wanted),
            hours_old=int(hours_old), 
            linkedin_fetch_description=True 
        )
    except Exception as e:
        print(f"❌ Erro no Scraping: {e}")
        return []

    if jobs.empty: return []

    found_jobs = []
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    required_keywords = [w.strip().lower() for w in filter_words.split(",") if w.strip()]

    for _, row in jobs.iterrows():
        desc = str(row.get('description', '')).lower()
        title = str(row.get('title', '')).lower()
        full_text = desc + " " + title
        
        if required_keywords:
            if not all(word in full_text for word in required_keywords):
                continue 

        job_dict = {
            "title": row.get('title'),
            "company": row.get('company'),
            "location": row.get('location'),
            "link": row.get('job_url'),
            "description": row.get('description'),
            "source": row.get('site')
        }
        found_jobs.append(job_dict)

        if save_to_db:
            exists = session.query(Job).filter(Job.link == job_dict['link']).first()
            if not exists:
                new_job = Job(**job_dict)
                session.add(new_job)

    if save_to_db:
        session.commit()
    session.close()
    return found_jobs
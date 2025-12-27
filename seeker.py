import os
import unicodedata
from datetime import datetime
from jobspy import scrape_jobs
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Job, DATABASE_URL

def normalize_text(text):
    """Remove acentos e converte para minúsculas para uma busca robusta."""
    if not text:
        return ""
    text = str(text).lower()
    return "".join(
        c for c in unicodedata.normalize('NFD', text)
        if unicodedata.category(c) != 'Mn'
    )

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
            enforce_desktop=True,
            delay=5 
        )

        if jobs_df is None or jobs_df.empty:
            print("DEBUG: O JobSpy retornou zero resultados.")
            return []
        
        jobs_list = jobs_df.to_dict('records')
        print(f"DEBUG: Encontradas {len(jobs_list)} vagas brutas no total.")

    except Exception as e:
        print(f"❌ Erro durante o scraping: {e}")
        return []

    found_jobs = []
    keywords = [normalize_text(w.strip()) for w in filter_words.split(",") if w.strip()]

    for row in jobs_list:
        title_raw = str(row.get('title', ''))
        desc_raw = str(row.get('description', ''))
        
        title_norm = normalize_text(title_raw)
        desc_norm = normalize_text(desc_raw)
        full_text_norm = title_norm + " " + desc_norm
        
        if keywords:
            if not all(word in full_text_norm for word in keywords):
                continue
        else:
            pass

        raw_published = row.get('date_posted')
        published_formatted = "N/A"
        
        if raw_published:
            try:
                dt = datetime.strptime(str(raw_published), '%Y-%m-%d')
                published_formatted = dt.strftime('%d/%m/%Y')
            except:
                published_formatted = str(raw_published)

        job_dict = {
            "title": title_raw,
            "company": row.get('company'),
            "location": row.get('location'),
            "link": row.get('job_url'),
            "description": desc_raw or "Sem descrição disponível (Acesse o link para detalhes).",
            "source": row.get('site'),
            "published_at": published_formatted,
            "created_at": datetime.utcnow()
        }
        found_jobs.append(job_dict)

    print(f"DEBUG: {len(found_jobs)} vagas aprovadas para exibição.")

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
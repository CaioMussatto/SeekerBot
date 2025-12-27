import os
import unicodedata
import re
from datetime import datetime
from jobspy import scrape_jobs
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Job, DATABASE_URL

def normalize_text(text):
    if not text: return ""
    return "".join(c for c in unicodedata.normalize('NFD', str(text).lower()) if unicodedata.category(c) != 'Mn')

def format_date_br(date_val):
    if not date_val or str(date_val).lower() == 'none': return "N/A"
    try:
        clean_str = str(date_val).split('T')[0].split()[0]
        if '-' in clean_str:
            dt = datetime.strptime(clean_str, '%Y-%m-%d')
            return dt.strftime('%d/%m/%Y')
        if hasattr(date_val, 'strftime'):
            return date_val.strftime('%d/%m/%Y')
    except: pass
    return str(date_val)

def fetch_and_save_jobs(term, google_term, save_to_db=False, results_wanted=30, hours_old=336, filter_words="", location="Brazil"):
    try:
        jobs_df = scrape_jobs(
            site_name=["google", "linkedin", "indeed"],
            search_term=term,
            google_search_term=google_term if google_term else f"vagas de {term} em {location}",
            location=location,
            results_wanted=int(results_wanted),
            hours_old=int(hours_old),
            country_indeed="brazil", 
            lang_google="pt",        
            linkedin_fetch_description=True,
            enforce_desktop=True,
            delay=5
        )
        if jobs_df is None or jobs_df.empty: return []
        jobs_list = jobs_df.to_dict('records')
    except Exception as e:
        print(f"❌ Erro: {e}")
        return []

    found_jobs = []
    norm_term = normalize_text(term)

    for row in jobs_list:
        title_raw = str(row.get('title', ''))
        desc_raw = str(row.get('description', ''))
        title_norm = normalize_text(title_raw)
        desc_norm = normalize_text(desc_raw)

        adj_pattern = rf"(relacionamento|contas|faturamento|auditoria|venda|promoção|auxiliar de|assistente de)\s+{norm_term}"
        if re.search(adj_pattern, title_norm):
            continue 

        is_academic = bool(re.search(rf"(superior|graduacao|formacao|bacharelado).{{0,50}}{norm_term}", desc_norm))
        is_benefit = bool(re.search(rf"(convenio|plano|assistencia|seguro).{{0,20}}{norm_term}", desc_norm))
        
      
        approved = False
        if norm_term in title_norm and not re.search(adj_pattern, title_norm):
            approved = True
        elif is_academic:
            approved = True
        
        if is_benefit and not (norm_term in title_norm and not re.search(adj_pattern, title_norm)) and not is_academic:
            approved = False

        if not approved:
            continue

        job_dict = {
            "title": title_raw,
            "company": row.get('company'),
            "location": row.get('location'),
            "link": row.get('job_url'),
            "description": desc_raw or "Detalhes no link.",
            "source": str(row.get('site')).lower(),
            "published_at": format_date_br(row.get('date_posted')),
            "created_at": datetime.utcnow().strftime('%d/%m/%Y')
        }
        found_jobs.append(job_dict)

    return found_jobs
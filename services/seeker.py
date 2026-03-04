import os
import unicodedata
import re
from datetime import datetime, timedelta, timezone
import pandas as pd
from jobspy import scrape_jobs
from core.database import SessionLocal
from models.job import Job

# ==============================================================================
# SECTION 1: TEXT TREATMENT UTILITIES
# ==============================================================================

def normalize_text(text: str) -> str:
    """
    Aggressive string cleaning: removes accents, converts to lowercase,
    and strips special characters to ensure precise matching for deduplication.
    """
    if not text or pd.isna(text): 
        return ""
    normalized = "".join(
        c for c in unicodedata.normalize('NFD', str(text).lower()) 
        if unicodedata.category(c) != 'Mn'
    )
    # Remove everything that is not a letter or number (helps with deduplication)
    normalized = re.sub(r'[^a-z0-9]', '', normalized)
    return normalized.strip()

# ==============================================================================
# SECTION 2: DATE PARSING ENGINE
# ==============================================================================

def parse_relative_date(date_str: str) -> str | None:
    """
    Parses relative time expressions commonly returned by job boards 
    (e.g., '2 days ago', 'há 3 semanas') into an exact date string.
    """
    if not date_str or str(date_str).lower() in ['none', 'nan', 'n/a', '']:
        return None
    
    text = str(date_str).lower().strip()
    today = datetime.now()
    text = re.sub(r'\s+', ' ', text)
    
    # Immediate time matches
    if any(x in text for x in ['seg', 'sec', 'second', 'segundo', 'min', 'minuto', 'minute', 'h', 'hora', 'hour', 'hr', 'agora', 'now', 'today', 'hoje', 'just now']):
        return today.strftime('%d/%m/%Y')

    # Days matches
    match_days = re.search(r'(\d+)\s*(d|dia|day)s?', text)
    if match_days:
        return (today - timedelta(days=int(match_days.group(1)))).strftime('%d/%m/%Y')

    # Weeks matches
    match_weeks = re.search(r'(\d+)\s*(w|sem|semana|week)s?', text)
    if match_weeks:
        return (today - timedelta(weeks=int(match_weeks.group(1)))).strftime('%d/%m/%Y')

    # Months matches
    match_months = re.search(r'(\d+)\s*(m|mes|month|mês)s?', text)
    if match_months:
        return (today - timedelta(days=int(match_months.group(1))*30)).strftime('%d/%m/%Y')

    # Portuguese specific expressions
    if 'há' in text or 'ha' in text:
        match = re.search(r'(\d+)', text)
        if match:
             val = int(match.group(1))
             if 'hora' in text: return today.strftime('%d/%m/%Y')
             elif 'semana' in text: return (today - timedelta(days=val*7)).strftime('%d/%m/%Y')
             elif 'mês' in text or 'mes' in text: return (today - timedelta(days=val*30)).strftime('%d/%m/%Y')
             else: return (today - timedelta(days=val)).strftime('%d/%m/%Y')
    
    return None

def format_date_br(date_val) -> str:
    """
    Formats any date input into the Brazilian standard DD/MM/YYYY.
    """
    if not date_val or str(date_val).lower() in ['none', 'nan', 'n/a', '']: 
        return "N/A"
    try:
        if hasattr(date_val, 'strftime'): 
            return date_val.strftime('%d/%m/%Y')
        
        date_str = str(date_val).strip()
        iso_match = re.match(r'(\d{4}-\d{2}-\d{2})', date_str)
        if iso_match: 
            return datetime.strptime(iso_match.group(1), '%Y-%m-%d').strftime('%d/%m/%Y')
        
        if re.match(r'\d{2}/\d{2}/\d{4}', date_str): 
            return date_str
            
        parsed = parse_relative_date(date_str)
        return parsed if parsed else date_str[:10]
    except:
        return "N/A"

# ==============================================================================
# SECTION 3: COLLECTION AND FILTERING LOGIC
# ==============================================================================

def fetch_and_save_jobs(term: str, location: str = "Brazil", results_wanted: int = 30, hours_old: int = 24, filter_words: str = "") -> list:
    """
    Fetches job postings from multiple platforms, applies exclusion filters, 
    deduplicates against the database, and saves the new entries.
    """
    print(f"🕵️  Starting focused search: '{term}' in '{location}' (Last {hours_old}h)...")
    
    target_country = 'brazil'
    if location.lower() in ['usa', 'eua', 'us', 'united states']: 
        target_country = 'usa'
    elif location.lower() in ['uk', 'united kingdom']: 
        target_country = 'uk'

    try:
        jobs_df = scrape_jobs(
            site_name=["linkedin", "indeed", "glassdoor"],
            search_term=term,
            location=location,
            results_wanted=results_wanted,
            hours_old=hours_old,
            country_indeed=target_country,
            is_remote=False,    
            linkedin_fetch_description=True,
            description_format="markdown",
            delay=5
        )
    except Exception as e:
        print(f"❌ Critical failure in scraper: {e}")
        return []

    if jobs_df is None or jobs_df.empty:
        print("⚠️ No jobs found by the scrapers in this run.")
        return []

    all_found_jobs = jobs_df.to_dict('records')
    
    # --- PREPARING IN-MEMORY DEDUPLICATION ---
    db = SessionLocal()
    
    # 1. Fetch all existing links from the DB
    existing_links = {job.link for job in db.query(Job.link).all()}
    
    # 2. Create strict fingerprints for existing jobs (Title + Company)
    existing_fingerprints = set()
    for job in db.query(Job.title, Job.company).all():
        tit_norm = normalize_text(job.title)
        comp_norm = normalize_text(job.company)
        existing_fingerprints.add(f"{tit_norm}{comp_norm}")

    stats = {
        "approved": 0, "duplicated": 0, "rejected_exclusion": 0, "rejected_invalid": 0
    }
    
    final_jobs_list = []
    
    for row in all_found_jobs:
        title = str(row.get('title', ''))
        company = str(row.get('company', ''))
        link = str(row.get('job_url', ''))
        desc = str(row.get('description', ''))
        
        # Validation
        if not title or not link or pd.isna(title) or pd.isna(link):
            stats["rejected_invalid"] += 1
            continue

        # --- BULLETPROOF DEDUPLICATION ---
        
        # Filter 1: Exact URL match
        if link in existing_links:
            stats["duplicated"] += 1
            continue
            
        # Filter 2: Normalized Fingerprint Match (Cross-platform)
        current_tit_norm = normalize_text(title)
        current_comp_norm = normalize_text(company)
        current_fingerprint = f"{current_tit_norm}{current_comp_norm}"
        
        if current_fingerprint in existing_fingerprints:
            stats["duplicated"] += 1
            continue

        # --- EXCLUSION FILTERS (Marketing / Unrelated Engineering) ---
        block_eng = ("engineer" in current_tit_norm or "engenheiro" in current_tit_norm) and \
                    ("engineer" not in normalize_text(term) and "engenheiro" not in normalize_text(term))
        marketing_pattern = r"(sales|venda|representative|suporte|atendimento|comercial|vendedor|midia|marketing)"
        
        if re.search(marketing_pattern, current_tit_norm) or block_eng:
            stats["rejected_exclusion"] += 1
            continue

        # --- APPROVAL AND PREPARATION ---
        stats["approved"] += 1
        
        # Add to local memory to prevent duplicates within the same scraping batch
        existing_links.add(link)
        existing_fingerprints.add(current_fingerprint)

        new_job = Job(
            title=title,
            company=company,
            location=str(row.get('location', 'Not provided')),
            link=link,
            description=desc or "Detailed description available on the source link.",
            source=str(row.get('site', 'unknown')).lower(),
            published_at=format_date_br(row.get('date_posted'))
            # created_at is handled automatically by the SQLAlchemy model
        )
        final_jobs_list.append(new_job)

    # --- TRACKING REPORT ---
    print(f"\n" + "="*60)
    print(f"📊 TRACKING REPORT (Reinforced Deduplication)")
    print(f"="*60)
    print(f"✅ New Jobs Approved:         {stats['approved']}")
    print(f"🔄 Discarded (Duplicates):    {stats['duplicated']}")
    print(f"❌ Rejected by Filters:       {stats['rejected_exclusion']}")
    print(f"="*60 + "\n")

    # --- DATABASE PERSISTENCE ---
    if final_jobs_list:
        try:
            db.add_all(final_jobs_list)
            db.commit()
            print(f"💾 DATABASE: {len(final_jobs_list)} new records successfully saved.")
        except Exception as e:
            db.rollback()
            print(f"❌ DB ERROR: Failed to persist jobs: {e}")
    
    db.close()
    return final_jobs_list
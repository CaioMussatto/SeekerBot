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
    CRITICAL FIX: Spaces are now preserved to allow regex word boundaries (\b) to work.
    """
    if not text or pd.isna(text): 
        return ""
    normalized = "".join(
        c for c in unicodedata.normalize('NFD', str(text).lower()) 
        if unicodedata.category(c) != 'Mn'
    )
    # Keep letters, numbers, AND spaces (\s). Replace multiple spaces with a single space.
    normalized = re.sub(r'[^a-z0-9\s]', '', normalized)
    normalized = re.sub(r'\s+', ' ', normalized)
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
    Supports Multi-Country Remote searching.
    """
    print(f"🕵️  Starting focused search: '{term}' in '{location}' (Last {hours_old}h)...")
    
    # --- REMOTE & MULTI-COUNTRY LOGIC ---
    is_remote_search = False
    locations_to_scrape = [location]
    
    if location.lower().strip() in ['remote', 'remoto']:
        is_remote_search = True
        locations_to_scrape = ['USA', 'UK', 'Ireland']
        results_wanted = max(10, results_wanted // 3) 
    elif 'remote' in location.lower() or 'remoto' in location.lower():
        is_remote_search = True

    all_dfs = []
    
    for loc in locations_to_scrape:
        target_country = 'brazil'
        loc_lower = loc.lower()
        if loc_lower in ['usa', 'eua', 'us', 'united states']: 
            target_country = 'usa'
        elif loc_lower in ['uk', 'united kingdom']: 
            target_country = 'uk'
        elif loc_lower in ['ireland', 'irlanda']:
            target_country = 'ireland'

        try:
            print(f"   -> Scraping location: {loc} (is_remote={is_remote_search})...")
            df = scrape_jobs(
                site_name=["linkedin", "indeed", "glassdoor"],
                search_term=term,
                location=loc,
                results_wanted=results_wanted,
                hours_old=hours_old,
                country_indeed=target_country,
                is_remote=is_remote_search,    
                linkedin_fetch_description=True,
                description_format="markdown",
                delay=5
            )
            if df is not None and not df.empty:
                all_dfs.append(df)
        except Exception as e:
            print(f"❌ Critical failure in scraper for {loc}: {e}")

    if not all_dfs:
        print("⚠️ No jobs found by the scrapers in this run.")
        return []

    jobs_df = pd.concat(all_dfs, ignore_index=True)
    all_found_jobs = jobs_df.to_dict('records')
    
    # --- PREPARING IN-MEMORY DEDUPLICATION ---
    db = SessionLocal()
    existing_links = {job.link for job in db.query(Job.link).all()}
    
    existing_fingerprints = set()
    for job in db.query(Job.title, Job.company).all():
        tit_norm = normalize_text(job.title)
        comp_norm = normalize_text(job.company)
        existing_fingerprints.add(f"{tit_norm}{comp_norm}")

    # Detailed Stats and Logs
    stats = {
        "approved": 0, "duplicated": 0, "rejected_missing_keyword": 0, "rejected_strict_relevance": 0, "rejected_invalid": 0
    }
    
    log_duplicates = []
    log_rejected_keywords = []
    log_rejected_relevance = []
    
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
        if link in existing_links:
            stats["duplicated"] += 1
            log_duplicates.append(f"[{company}] {title} (DB Link Match)")
            continue
            
        current_tit_norm = normalize_text(title)
        current_comp_norm = normalize_text(company)
        current_fingerprint = f"{current_tit_norm}{current_comp_norm}"
        
        if current_fingerprint in existing_fingerprints:
            stats["duplicated"] += 1
            log_duplicates.append(f"[{company}] {title} (Fingerprint Match)")
            continue

        desc_norm = normalize_text(desc)

        # =====================================================================
        # --- GENERALIZED RELEVANCE FILTER ---
        # =====================================================================
        
        # 1. Dynamic User INCLUSION (filter_words from the frontend)
        missing_mandatory_keyword = False
        missing_word_name = ""
        if filter_words:
            required_words = [normalize_text(w.strip()) for w in filter_words.split(',')]
            for req_word in required_words:
                if req_word and req_word not in current_tit_norm and req_word not in desc_norm:
                    missing_mandatory_keyword = True
                    missing_word_name = req_word
                    break 
                    
        if missing_mandatory_keyword:
            stats["rejected_missing_keyword"] += 1
            log_rejected_keywords.append(f"[{company}] {title} -> Missing keyword: '{missing_word_name}'")
            continue

        # 2. Strict Relevance Check (Title Priority + Word Boundaries + Stop Words)
        term_norm = normalize_text(term)
        
        # Stop Words Filter: Removes prepositions and generic words 
        # to prevent false positives like matching "de", "em", "analista".
        stop_words = {'de', 'da', 'do', 'das', 'dos', 'em', 'para', 'com', 'e', 'o', 'a', 'analista', 'pessoa', 'pleno', 'senior', 'junior', 'sr', 'jr', 'of', 'and', 'for', 'in'}
        term_words = [w for w in term_norm.split() if w not in stop_words and len(w) > 2]
        
        # Check if any CORE word from the search term is in the title
        is_in_title = any(word in current_tit_norm for word in term_words) if term_words else False
        
        strict_pattern = r'\b' + re.escape(term_norm) + r'\b'
        is_in_desc_strictly = bool(re.search(strict_pattern, desc_norm))
        
        if not (is_in_title or is_in_desc_strictly):
            stats["rejected_strict_relevance"] += 1
            log_rejected_relevance.append(f"[{company}] {title} -> No core relation to '{term}'")
            continue
            
        # =====================================================================

        # --- APPROVAL AND PREPARATION ---
        stats["approved"] += 1
        existing_links.add(link)
        existing_fingerprints.add(current_fingerprint)

        job_location = str(row.get('location', 'Not provided'))
        is_job_remote = row.get('is_remote', False)
        if is_remote_search or is_job_remote:
            if "remote" not in job_location.lower():
                job_location = f"Remote, {job_location}"

        new_job = Job(
            title=title,
            company=company,
            location=job_location,
            link=link,
            description=desc or "Detailed description available on the source link.",
            source=str(row.get('site', 'unknown')).lower(),
            published_at=format_date_br(row.get('date_posted'))
        )
        final_jobs_list.append(new_job)

    # --- TRACKING REPORT ---
    print(f"\n" + "="*70)
    print(f"📊 TRACKING REPORT FOR: '{term}'")
    print(f"="*70)
    print(f"✅ New Jobs Approved:         {stats['approved']}")
    print(f"🔄 Discarded (Duplicates):    {stats['duplicated']}")
    print(f"❌ Rejected (No Keywords):    {stats['rejected_missing_keyword']}")
    print(f"❌ Rejected (Irrelevant):     {stats['rejected_strict_relevance']}")
    
    # Print Sample Logs for transparency (Cap at 5 per category to avoid terminal flood)
    if log_duplicates:
        print("\n  🔄 Duplicates Sample:")
        for log in log_duplicates[:5]: print(f"     - {log}")
        if len(log_duplicates) > 5: print(f"     ... and {len(log_duplicates) - 5} more.")
            
    if log_rejected_keywords:
        print("\n  ❌ Missing User Keyword Sample:")
        for log in log_rejected_keywords[:5]: print(f"     - {log}")
        if len(log_rejected_keywords) > 5: print(f"     ... and {len(log_rejected_keywords) - 5} more.")

    if log_rejected_relevance:
        print("\n  ❌ Irrelevant Job Sample (Saved API Tokens!):")
        for log in log_rejected_relevance[:5]: print(f"     - {log}")
        if len(log_rejected_relevance) > 5: print(f"     ... and {len(log_rejected_relevance) - 5} more.")
        
    print(f"="*70 + "\n")

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
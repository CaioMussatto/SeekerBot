import time
from services.seeker import fetch_and_save_jobs

def run_job_search():
    """
    Main entry point to execute the job scraper for multiple roles.
    Iterates through a list of target roles and saves results to the PostgreSQL database.
    """
    print("🚀 Starting the automated job search process...")
    
    # Define your target search parameters here
    target_roles = ["Bioinformatics", "Data Scientist"]
    target_location = "Brazil"
    search_window_hours = 72  # Looking for jobs posted in the last 3 days
    max_results_per_role = 30 # Limit to avoid getting blocked by platforms
    
    total_saved = 0
    
    for role in target_roles:
        print(f"\n" + "="*50)
        print(f"🔍 INITIATING SEARCH FOR: {role.upper()}")
        print(f"="*50)
        
        # Call the scraper service
        saved_jobs = fetch_and_save_jobs(
            term=role,
            location=target_location,
            results_wanted=max_results_per_role,
            hours_old=search_window_hours
        )
        
        total_saved += len(saved_jobs)
        
        # Add a small delay between different roles to mimic human behavior
        # and prevent temporary IP bans from job boards.
        if role != target_roles[-1]:
            print("\n⏳ Waiting 10 seconds before the next search to avoid rate limits...")
            time.sleep(10)
            
    print("\n" + "*"*50)
    print(f"🎉 JOB SEARCH COMPLETED!")
    print(f"📈 Total new unique jobs added to database: {total_saved}")
    print("*"*50 + "\n")

if __name__ == "__main__":
    run_job_search()
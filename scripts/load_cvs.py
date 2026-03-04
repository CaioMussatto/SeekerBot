import os
from pypdf import PdfReader
from core.database import SessionLocal
from models.resume import Resume

def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extracts all text from a given PDF file.
    
    Args:
        pdf_path (str): The relative or absolute path to the PDF file.
        
    Returns:
        str: The extracted text from all pages of the PDF.
    """
    try:
        reader = PdfReader(pdf_path)
        full_text = ""
        
        # Iterate through all pages and extract text
        for page in reader.pages:
            text = page.extract_text()
            if text:
                full_text += text + "\n"
                
        return full_text.strip()
    except Exception as e:
        print(f"❌ Error reading {pdf_path}: {e}")
        return ""

def load_cvs_to_db():
    """
    Scans the 'docs_cv' folder, extracts text from each PDF, 
    and saves the content into the PostgreSQL 'resumes' table.
    """
    cv_folder = "docs_cv"
    
    # Check if the folder exists
    if not os.path.exists(cv_folder):
        print(f"❌ Error: The folder '{cv_folder}' does not exist.")
        return

    # Open a connection session to the database
    db = SessionLocal()
    
    try:
        # Loop through all files in the docs_cv directory
        for filename in os.listdir(cv_folder):
            if filename.endswith(".pdf"):
                file_path = os.path.join(cv_folder, filename)
                print(f"📄 Processing: {filename}...")
                
                # Extract the text
                extracted_text = extract_text_from_pdf(file_path)
                
                if extracted_text:
                    # Create a new Resume record
                    # We use the filename as the title for now
                    new_resume = Resume(
                        title=filename,
                        content=extracted_text,
                        is_master=False # These are raw CVs, not the AI generated Master yet
                    )
                    
                    # Add to the database session
                    db.add(new_resume)
                    print(f"   ✅ Added '{filename}' to the database queue.")
                else:
                    print(f"   ⚠️ Warning: No text extracted from '{filename}'.")
        
        # Commit the transaction to save all records to PostgreSQL
        db.commit()
        print("\n🎉 Success: All CVs have been saved to the database!")
        
    except Exception as e:
        # If anything goes wrong, rollback the changes to prevent data corruption
        db.rollback()
        print(f"❌ Database error: {e}")
    finally:
        # Always close the database connection
        db.close()

if __name__ == "__main__":
    load_cvs_to_db()
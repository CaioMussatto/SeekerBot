import os
from flask import Flask, render_template, request, redirect, url_for
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import markdown
from dotenv import load_dotenv
from database import Job, DATABASE_URL
from seeker import fetch_and_save_jobs

load_dotenv()
app = Flask(__name__)
USE_DB = os.getenv("USE_DB", "True") == "True"

def get_session():
    # Garante conexão limpa
    clean_url = DATABASE_URL.split("?")[0] if DATABASE_URL else "sqlite:///jobs_data.db"
    engine = create_engine(clean_url)
    Session = sessionmaker(bind=engine)
    return Session()

@app.route('/')
def index():
    jobs = []
    if USE_DB:
        try:
            session = get_session()
            # AQUI ESTÁ A PROTEÇÃO: Só mostra o que não foi rejeitado e não aplicado
            jobs = session.query(Job).filter(
                Job.applied == False, 
                Job.rejected == False
            ).order_by(Job.id.desc()).all()
            
            for job in jobs:
                job.formatted_description = markdown.markdown(job.description or "")
                # Formatação Segura de Data
                if hasattr(job.created_at, 'strftime'):
                    job.display_created_at = job.created_at.strftime('%d/%m/%Y %H:%M')
                else:
                    job.display_created_at = str(job.created_at)
            session.close()
        except Exception as e:
            print(f"❌ Erro no Index: {e}")
    
    return render_template('index.html', jobs=jobs, can_use_db=USE_DB, mode="Modo Pessoal")

@app.route('/refresh', methods=['POST'])
def refresh():
    term = request.form.get('term')
    save_db = request.form.get('save_db') == 'on'
    
    # Chama o seeker
    new_jobs_list = fetch_and_save_jobs(
        term=term, 
        google_term=request.form.get('google_term'),
        save_to_db=save_db,
        results_wanted=int(request.form.get('results_wanted', 60)),
        hours_old=int(request.form.get('hours_old', 24)),
        location=request.form.get('location', 'Brazil')
    )

    display_jobs = []
    if save_db and USE_DB:
        session = get_session()
        # Exibe apenas as vagas novas que NÃO foram rejeitadas anteriormente
        display_jobs = session.query(Job).filter(
            Job.rejected == False,
            Job.applied == False
        ).order_by(Job.id.desc()).limit(len(new_jobs_list)).all()
        
        for j in display_jobs:
            j.formatted_description = markdown.markdown(j.description or "")
            if hasattr(j.created_at, 'strftime'):
                j.display_created_at = j.created_at.strftime('%d/%m/%Y %H:%M')
        session.close()
    else:
        # Modo Efêmero (Sem Banco)
        for item in new_jobs_list:
            temp_job = type('Job', (), item)
            temp_job.id = None
            temp_job.applied = False
            temp_job.rejected = False
            temp_job.formatted_description = markdown.markdown(item.get('description', ''))
            
            val_date = item.get('created_at')
            if hasattr(val_date, 'strftime'):
                temp_job.display_created_at = val_date.strftime('%d/%m/%Y %H:%M')
            else:
                temp_job.display_created_at = str(val_date)
            
            display_jobs.append(temp_job)

    return render_template('index.html', jobs=display_jobs, can_use_db=USE_DB, mode="Novas Vagas")

@app.route('/apply/<int:job_id>')
def apply(job_id):
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
    if USE_DB:
        session = get_session()
        job = session.query(Job).get(job_id)
        if job:
            # SOFT DELETE: Marca como rejeitada, mas mantém no banco
            # Isso impede que o Seeker salve ela de novo no futuro
            job.rejected = True 
            session.commit()
        session.close()
    return redirect(url_for('index'))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port, debug=True)
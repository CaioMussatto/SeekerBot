import os
from flask import Flask, render_template, request, redirect, url_for
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import markdown
from database import Job, DATABASE_URL
from seeker import fetch_and_save_jobs

app = Flask(__name__)

# Configurações de Modo (Público vs Pessoal)
USE_DB = os.getenv("USE_DB", "True") == "True"

def get_session():
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    return Session()

@app.route('/')
def index():
    jobs = []
    mode_text = "Modo Pessoal (Geral)" if USE_DB else "Modo Público (Sessão)"
    
    if USE_DB:
        session = get_session()
        # MUDANÇA AQUI: Filtra para mostrar apenas as NÃO aplicadas
        jobs = session.query(Job).filter(Job.applied == False).order_by(Job.created_at.desc()).all()
        session.close()
    
    for job in jobs:
        job.formatted_description = markdown.markdown(job.description or "")
        
    return render_template('index.html', jobs=jobs, can_use_db=USE_DB, mode=mode_text)

@app.route('/refresh', methods=['POST'])
def refresh():
    term = request.form.get('term')
    google_term = request.form.get('google_term')
    location = request.form.get('location', 'Brazil')
    results_wanted = request.form.get('results_wanted', 30)
    hours_old = request.form.get('hours_old', 336)
    filter_words = request.form.get('filter_words', "")
    save_db = request.form.get('save_db') == 'on'

    # Chama o robô (seeker.py)
    new_jobs = fetch_and_save_jobs(
        term=term,
        google_term=google_term,
        save_to_db=save_db,
        results_wanted=results_wanted,
        hours_old=hours_old,
        filter_words=filter_words,
        location=location
    )

    if USE_DB:
        return redirect(url_for('index'))
    else:
        # No modo público, passamos as vagas direto para o template sem salvar
        for job in new_jobs:
            job['formatted_description'] = markdown.markdown(job['description'] or "")
        return render_template('index.html', jobs=new_jobs, can_use_db=False, mode="Busca em Tempo Real")

@app.route('/apply/<int:job_id>')
def apply(job_id):
    if not USE_DB:
        return redirect(url_for('index'))
    
    session = get_session()
    job = session.query(Job).get(job_id)
    if job:
        job.applied = not job.applied  # Inverte o status (Toggle)
        session.commit()
    session.close()
    return redirect(url_for('index'))

@app.route('/delete/<int:job_id>')
def delete_job(job_id):
    if not USE_DB:
        return redirect(url_for('index'))
    
    session = get_session()
    job = session.query(Job).get(job_id)
    if job:
        session.delete(job)
        session.commit()
    session.close()
    return redirect(url_for('index'))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
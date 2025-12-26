from flask import Flask, render_template, redirect, url_for, request, session as flask_session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Job, DATABASE_URL
from seeker import fetch_and_save_jobs
import markdown

app = Flask(__name__)
app.secret_key = "caio_key_final_v2" 
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

def format_job_description(text):
    if not text: 
        return "Sem descrição."
    try:
        return markdown.markdown(text)
    except Exception:
        return text

@app.route('/')
def index():
    temp_results = flask_session.get('temp_results')
    
    if temp_results:
        for j in temp_results:
            j['formatted_description'] = format_job_description(j.get('description', ''))
        return render_template('index.html', jobs=temp_results, mode="Simulação")

    db_session = Session()
    try:
        db_jobs = db_session.query(Job).filter(Job.applied == False).order_by(Job.created_at.desc()).all()
        for j in db_jobs:
            j.formatted_description = format_job_description(j.description)
        return render_template('index.html', jobs=db_jobs, mode="Banco de Dados")
    finally:
        db_session.close()

@app.route('/refresh', methods=['POST'])
def refresh():
    if 'temp_results' in flask_session:
        flask_session.pop('temp_results')

    term = request.form.get('term', 'bioinformatics')
    g_term = request.form.get('google_term', 'bioinformatics jobs Brazil')
    f_words = request.form.get('filter_words', "")
    results_q = request.form.get('results_wanted', 20)
    hours_q = request.form.get('hours_old', 336)
    save = "save_db" in request.form
    
    results = fetch_and_save_jobs(
        term=term, 
        google_term=g_term, 
        save_to_db=save,
        results_wanted=results_q,
        hours_old=hours_q,
        filter_words=f_words
    )
    
    # Se NÃO for salvar no banco, joga na sessão para o index ler
    if not save:
        flask_session['temp_results'] = results
        
    return redirect(url_for('index'))

@app.route('/apply/<int:job_id>')
def apply(job_id):
    db_session = Session()
    try:
        job = db_session.query(Job).get(job_id)
        if job:
            job.applied = True
            db_session.commit()
    finally:
        db_session.close()
    return redirect(url_for('index'))

@app.route('/delete/<int:job_id>')
def delete_job(job_id):
    db_session = Session()
    try:
        job = db_session.query(Job).get(job_id)
        if job:
            db_session.delete(job)
            db_session.commit()
    finally:
        db_session.close()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
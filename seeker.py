import os
import unicodedata
import re
from datetime import datetime, timedelta
from jobspy import scrape_jobs
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from database import Job, DATABASE_URL

# ==============================================================================
# SEÇÃO 1: UTILITÁRIOS DE TRATAMENTO DE TEXTO E NORMALIZAÇÃO
# ==============================================================================

def normalize_text(text):
    """
    Realiza a limpeza profunda de strings para garantir que o match de termos
    ignore acentos, variações de caixa (Upper/Lower) e caracteres especiais.
    Essencial para que 'Ciência' e 'ciencia' sejam tratados como iguais.
    """
    if not text: 
        return ""
    # Normalização NFD para separar caracteres de seus acentos
    normalized = "".join(
        c for c in unicodedata.normalize('NFD', str(text).lower()) 
        if unicodedata.category(c) != 'Mn'
    )
    return normalized.strip()

# ==============================================================================
# SEÇÃO 2: MOTOR DE PARSE DE DATAS (O MAIS COMPLETO)
# ==============================================================================

def parse_relative_date(date_str):
    """
    Converte expressões de tempo relativo (comuns em APIs de busca) em datas reais.
    Esta função é extensa para cobrir todas as variações de LinkedIn, Indeed e Google.
    """
    if not date_str or str(date_str).lower() in ['none', 'nan', 'n/a', '']:
        return None
    
    text = str(date_str).lower().strip()
    today = datetime.now()
    text = re.sub(r'\s+', ' ', text)
    
    # --- Verificação de Tempo Imediato ---
    if any(x in text for x in ['seg', 'sec', 'second', 'segundo']):
        return today.strftime('%d/%m/%Y')
    
    if any(x in text for x in ['min', 'minuto', 'minute']):
        return today.strftime('%d/%m/%Y')
        
    if any(x in text for x in ['h', 'hora', 'hour', 'hr']):
        return today.strftime('%d/%m/%Y')
        
    if any(x in text for x in ['agora', 'now', 'today', 'hoje', 'just now']):
        return today.strftime('%d/%m/%Y')

    # --- Verificação de Dias ---
    match_days = re.search(r'(\d+)\s*(d|dia|day)s?', text)
    if match_days:
        try:
            val = int(match_days.group(1))
            return (today - timedelta(days=val)).strftime('%d/%m/%Y')
        except:
            pass

    # --- Verificação de Semanas ---
    match_weeks = re.search(r'(\d+)\s*(w|sem|semana|week)s?', text)
    if match_weeks:
        try:
            val = int(match_weeks.group(1))
            return (today - timedelta(weeks=val)).strftime('%d/%m/%Y')
        except:
            pass

    # --- Verificação de Meses ---
    match_months = re.search(r'(\d+)\s*(m|mes|month|mês)s?', text)
    if match_months:
        try:
            val = int(match_months.group(1))
            return (today - timedelta(days=val*30)).strftime('%d/%m/%Y')
        except:
            pass

    # --- Tratamento de Expressões em Português ('há X dias') ---
    if 'há' in text or 'ha' in text:
        match = re.search(r'(\d+)', text)
        if match:
             try:
                val = int(match.group(1))
                if 'hora' in text: 
                    return today.strftime('%d/%m/%Y')
                elif 'semana' in text: 
                    return (today - timedelta(days=val*7)).strftime('%d/%m/%Y')
                elif 'mês' in text or 'mes' in text: 
                    return (today - timedelta(days=val*30)).strftime('%d/%m/%Y')
                else: 
                    return (today - timedelta(days=val)).strftime('%d/%m/%Y')
             except:
                 pass
    
    return None

def format_date_br(date_val):
    """
    Formata qualquer entrada de data para o padrão brasileiro DD/MM/YYYY.
    Lida com objetos datetime nativos e strings de diversos formatos.
    """
    if not date_val or str(date_val).lower() in ['none', 'nan', 'n/a', '']: 
        return "N/A"
    
    try:
        # Caso o objeto já seja um Datetime
        if hasattr(date_val, 'strftime'): 
            return date_val.strftime('%d/%m/%Y')
        
        date_str = str(date_val).strip()
        
        # Padrão ISO YYYY-MM-DD (Comum no retorno de APIs)
        iso_match = re.match(r'(\d{4}-\d{2}-\d{2})', date_str)
        if iso_match: 
            dt_obj = datetime.strptime(iso_match.group(1), '%Y-%m-%d')
            return dt_obj.strftime('%d/%m/%Y')
        
        # Se já estiver formatado corretamente
        if re.match(r'\d{2}/\d{2}/\d{4}', date_str): 
            return date_str
            
        # Tenta o motor de parse relativo
        parsed = parse_relative_date(date_str)
        if parsed:
            return parsed
            
        return date_str[:10]
    except Exception as e:
        print(f"⚠️ Alerta: Falha ao formatar data '{date_val}': {e}")
        return "N/A"

# ==============================================================================
# SEÇÃO 3: LÓGICA DE COLETA E FILTRAGEM (RAIO-X)
# ==============================================================================

def fetch_and_save_jobs(term, google_term, save_to_db=False, results_wanted=60, 
                        hours_old=24, filter_words="", location="Brazil"):
    """
    Função principal que coordena o scraper e aplica os filtros multicamadas
    antes de persistir os dados no banco SQLite.
    """
    search_queue = [] 
    
    # Determinação da estratégia de busca baseada na localização
    if location and location.lower() == 'remote':
        print(f"🌍 ESTRATÉGIA GLOBAL: Iniciando busca remota em 11 países...")
        countries = ['usa', 'canada', 'italy', 'uk', 'germany', 'spain', 'france', 'switzerland', 'netherlands', 'ireland', 'belgium']
        limit_per = max(10, int(results_wanted / 3))
        for c in countries:
            search_queue.append({'country': c, 'search_loc': '', 'is_remote': True, 'limit': limit_per})
    else:
        print(f"🕵️  BUSCA FOCADA: {term} em {location}")
        target_c = 'brazil'
        loc_lower = location.lower()
        if loc_lower in ['usa', 'eua', 'us', 'united states']: target_c = 'usa'
        elif loc_lower in ['uk', 'united kingdom']: target_c = 'uk'
        search_queue.append({'country': target_c, 'search_loc': location, 'is_remote': False, 'limit': results_wanted})

    all_found_jobs = []
    
    # Execução do Ciclo de Scraping
    for task in search_queue:
        try:
            current_search_term = term
            g_term = google_term if google_term else f"{term} jobs"
            
            # Tratamento especial para termos de Bioinformática no exterior
            if task['country'] != 'brazil' and 'informática' in term.lower():
                g_term = g_term.replace('informática', 'informatics').replace('informatica', 'informatics')
                current_search_term = "Bioinformatics"

            print(f"   🚀 Consultando provedores em {task['country']}...")
            jobs_df = scrape_jobs(
                site_name=["linkedin", "indeed", "google"], 
                search_term=current_search_term,
                google_search_term=g_term,
                location=task['search_loc'], 
                results_wanted=task['limit'],
                hours_old=int(hours_old),
                country_indeed=task['country'], 
                is_remote=task['is_remote'],    
                linkedin_fetch_description=True,
                description_format="markdown",
                delay=3, 
                verbose=0 
            )
            
            if jobs_df is not None and not jobs_df.empty:
                jobs_df['origin_country'] = task['country']
                all_found_jobs.extend(jobs_df.to_dict('records'))
                print(f"   ✅ Sucesso: {len(jobs_df)} vagas encontradas.")
        except Exception as e:
            print(f"   ❌ Falha crítica no scraper ({task['country']}): {e}")

    if not all_found_jobs:
        print("⚠️ Aviso: Nenhum dado retornado pelos scrapers para os critérios informados.")
        return []

    # --- CONFIGURAÇÃO DE SINÔNIMOS INTELIGENTES (Sem Engenharia Indesejada) ---
    norm_term = normalize_text(term)
    term_variants = {norm_term}
    
    # Mapeamento para expandir a busca sem perder a precisão técnica
    synonyms_map = {
        "especialista de dados": ["data specialist", "data expert", "analista de dados", "data analyst", "cientista de dados", "data scientist"],
        "cientista de dados": ["data scientist", "machine learning scientist", "estatistico", "data science"],
        "analista de dados": ["data analyst", "analytics", "bi analyst", "business intelligence", "analista de bi"],
        "bioinformatica": ["bioinformatics", "bioinformatician", "computational biology", "biologia computacional", "genomics", "genomica"],
        "bioinformatician": ["bioinformatics", "bioinformatica", "genomics", "genomica", "computational biology"]
    }

    # Integração dos sinônimos às variantes de busca
    for key, values in synonyms_map.items():
        if key in norm_term or norm_term in key:
            for v in values:
                term_variants.add(normalize_text(v))
    
    # Variantes gramaticais de segurança para bioinfo
    if 'informatica' in norm_term: term_variants.add(norm_term.replace('informatica', 'informatics'))
    if 'informatics' in norm_term: term_variants.add(norm_term.replace('informatics', 'informatica'))

    # --- INÍCIO DO PROCESSO DE FILTRAGEM (RAIO-X DETALHADO) ---
    final_jobs_list = []
    agora_br = datetime.utcnow() - timedelta(hours=3)
    filter_list = [f.strip().lower() for f in filter_words.split(",") if f.strip()] if filter_words else []

    # Inicialização da Sessão do Banco de Dados
    engine = create_engine(DATABASE_URL.split("?")[0])
    Session = sessionmaker(bind=engine)
    session = Session()

    # Estrutura de estatísticas para o Tracking
    stats = {
        "aprovadas": 0, 
        "duplicadas": 0, 
        "repro_no_term": 0,
        "repro_exclusion": 0, 
        "repro_non_tech": 0, 
        "repro_user_filter": 0, 
        "repro_invalid": 0
    }

    print(f"📊 Iniciando análise de {len(all_found_jobs)} registros brutos...")

    for row in all_found_jobs:
        title = str(row.get('title', ''))
        company = str(row.get('company', ''))
        link = str(row.get('job_url', ''))
        desc = str(row.get('description', ''))
        
        # 0. Validação de Integridade
        if not title or not link:
            stats["repro_invalid"] += 1
            continue

        # 1. Filtro de Duplicidade (Nível de Banco e Título)
        exists = session.query(Job).filter(
            (Job.link == link) | 
            ((func.lower(Job.title) == title.lower()) & (func.lower(Job.company) == company.lower()))
        ).first()
        
        if exists:
            stats["duplicadas"] += 1
            continue

        title_norm = normalize_text(title)
        desc_norm = normalize_text(desc)
        
        # 2. Match de Termos (Variantes + Sinônimos)
        term_in_title = any(t in title_norm for t in term_variants)
        term_in_desc = any(t in desc_norm for t in term_variants)
        
        if not (term_in_title or term_in_desc):
            stats["repro_no_term"] += 1
            continue

        # 3. FILTRO DE EXCLUSÃO (VENDAS + ENGENHARIA + MARKETING DIGITAL / TRAFEGO)
        # Regra 3.1: Bloqueio de Engenharia (a menos que seja o foco da busca)
        block_eng = ("engineer" in title_norm or "engenheiro" in title_norm) and \
                    ("engineer" not in norm_term and "engenheiro" not in norm_term)
        
        # Regra 3.2: Bloqueio de Marketing, Tráfego e E-commerce (Ruído detectado)
        marketing_pattern = r"(sales|venda|representative|billing|suporte|support|customer|atendimento|comercial|vendedor|ecomm|cro|trafego|traffic|performance|midia|marketing|perfumaria|social media)"
        
        if re.search(marketing_pattern, title_norm) or block_eng:
            stats["repro_exclusion"] += 1
            continue

        # 4. Filtro de Contexto Técnico/Acadêmico
        # Exigimos ferramentas ou qualificações para evitar cargos meramente administrativos
        acad_regex = r"(phd|msc|degree|bachelor|university|graduacao|superior|cientista|scientist|analyst|analista|engineer|pesquisador|data|dados|python|sql|r-lang|biologia|biology|genomica|genomics|biostatistics)"
        is_tech = bool(re.search(acad_regex, desc_norm)) or bool(re.search(acad_regex, title_norm))
        
        # Se o termo principal não está no título, a descrição PRECISA ser técnica para validar
        if not term_in_title and not is_tech:
            stats["repro_non_tech"] += 1
            continue

        # 5. Filtro Personalizado do Usuário (Input manual na tela)
        if filter_list:
            if not any(f in title_norm or f in desc_norm for f in filter_list):
                stats["repro_user_filter"] += 1
                continue

        # --- FASE DE APROVAÇÃO ---
        stats["aprovadas"] += 1
        
        # Normalização de Localização para Exibição
        loc_final = row.get('location', 'Remoto')
        if task['is_remote'] and row.get('origin_country') != 'brazil':
            loc_country = str(row.get('origin_country')).upper()
            loc_final = f"Remoto ({loc_country})"

        final_jobs_list.append({
            "title": title,
            "company": company,
            "location": loc_final,
            "link": link,
            "description": desc or "Descrição detalhada disponível no link de origem.",
            "source": str(row.get('site')).lower(),
            "applied": False,
            "rejected": False,
            "published_at": format_date_br(row.get('date_posted')),
            "created_at": agora_br
        })

    # --- RELATÓRIO DE TRACKING (LOG DETALHADO NO TERMINAL) ---
    print(f"\n" + "="*60)
    print(f"🔍 RELATÓRIO DE TRACKING (RAIO-X COMPLETO - V350)")
    print(f"="*60)
    print(f"✅ Novas Vagas Aprovadas:      {stats['aprovadas']}")
    print(f"🔄 Descartadas (Duplicadas):     {stats['duplicadas']}")
    print(f"❌ Reprovadas por Filtros:")
    print(f"   - Termo não encontrado:        {stats['repro_no_term']}")
    print(f"   - Título Proibido (Mkt/Eng):   {stats['repro_exclusion']}")
    print(f"   - Falta de Contexto Técnico:   {stats['repro_non_tech']}")
    print(f"   - Filtro Manual da Interface:  {stats['repro_user_filter']}")
    print(f"   - Erro de Integridade/Nulos:   {stats['repro_invalid']}")
    print(f"="*60 + "\n")

    if save_to_db and final_jobs_list:
        try:
            for item in final_jobs_list:
                session.add(Job(**item))
            session.commit()
            print(f"💾 DATABASE: {len(final_jobs_list)} novos registros salvos com sucesso.")
        except Exception as e:
            session.rollback()
            print(f"❌ ERRO DE BANCO: Falha ao persistir vagas: {e}")
    
    session.close()
    return final_jobs_list


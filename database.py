import os
import sys
import datetime
from dotenv import load_dotenv
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, create_engine
from sqlalchemy.orm import declarative_base

load_dotenv()

USE_DB_ENV = os.getenv("USE_DB", "True") == "True"
raw_url = os.getenv("DATABASE_URL")

if not raw_url:
    if USE_DB_ENV:
        print("❌ ERRO: DATABASE_URL não encontrada no .env")
        sys.exit(1)
    else:
        DATABASE_URL = "sqlite:///./public_mode_temp.db"
        print("⚠️ Modo Público Ativo: Usando SQLite temporário.")
else:
    clean_url = raw_url.split("?")[0]
    DATABASE_URL = clean_url.replace("postgres://", "postgresql://")

Base = declarative_base()

class Job(Base):
    __tablename__ = 'jobs'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    company = Column(String(255))
    location = Column(String(255))
    link = Column(Text, unique=True, nullable=False)
    description = Column(Text)
    source = Column(String(100))
    applied = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    # NOVO CAMPO: Data que a vaga foi postada no LinkedIn/Indeed/Google
    published_at = Column(String(50)) 

engine = create_engine(DATABASE_URL)

def init_db(reset=False):
    try:
        if reset:
            print(" Resetando banco de dados...")
            Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)
        print(f"✅ Banco iniciado!")
    except Exception as e:
        print(f"❌ Erro ao conectar: {e}")

if __name__ == "__main__":
    init_db(reset="--reset" in sys.argv)
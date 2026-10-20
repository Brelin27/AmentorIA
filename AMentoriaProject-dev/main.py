import os
# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import chat, auth, alunos, files
from core.database import engine
from models import models

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Tutor Socrático ENEM", version="0.1.0")

# Preserva as origens locais/originais e permite configurar a URL do ambiente de testes.
allowed_origins = ["http://localhost:3000", "https://amentoria-project.vercel.app"]
allowed_origins.extend(
    origin.strip().rstrip("/")
    for origin in os.getenv("FRONTEND_URL", "").split(",")
    if origin.strip()
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["Autenticação"])
app.include_router(chat.router, prefix="/api/chat", tags=["Tutoria e Chat"])
app.include_router(alunos.router, prefix="/api/alunos", tags=["Gestão de Alunos"])
app.include_router(files.router, prefix="/api/files", tags=["Arquivos de Conhecimento"])


@app.get("/")
def home():
    return {"status": "API do Tutor Socrático está online!"}
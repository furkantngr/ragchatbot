# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.services.logging_service import init_db # <-- YENİ
from app.models.schemas import Question, Answer
from app.services.rag_service import initialize_rag, get_answer

@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_rag()
    init_db()
    yield

app = FastAPI(title="Kurumsal RAG (Text-Only)", version="2.1", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"status": "Active", "mode": "Text-Only"}

@app.post("/soru-sor", response_model=Answer)
async def ask(request: Question):
    response_text = await get_answer(request.query)
    return Answer(response=response_text)
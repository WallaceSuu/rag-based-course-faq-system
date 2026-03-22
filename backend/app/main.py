import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .db import get_logs, init_db, log_query
from .evaluation import evaluate
from .generation import generate_answer
from .hallucination import detect_hallucination
from .ingest import ingest_folder
from .retrieval import retrieve

load_dotenv()


def _golden_dataset_path() -> Path:
    env = os.getenv("GOLDEN_DATASET_PATH")
    if env:
        return Path(env)
    docker_default = Path("/app/data/golden_dataset.json")
    if docker_default.is_file():
        return docker_default
    return Path(__file__).resolve().parent.parent / "data" / "golden_dataset.json"


class QueryRequest(BaseModel):
    question: str


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="Course RAG QA API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/ingest")
def ingest_endpoint() -> Dict[str, Any]:
    slides_path = os.getenv("SLIDES_PATH", "/app/slides")
    return ingest_folder(slides_path)


@app.post("/query")
def query_endpoint(req: QueryRequest) -> Dict[str, Any]:
    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question is required.")

    chunks = retrieve(question, top_k=5)
    answer = generate_answer(question, chunks)
    hallucination = detect_hallucination(question, answer, chunks)

    log_query(
        question=question,
        answer=answer,
        retrieved_chunks=chunks,
        hallucinated=hallucination["hallucinated"],
        detail=hallucination["detail"],
    )

    return {
        "answer": answer,
        "chunks": chunks,
        "hallucination": hallucination,
    }


@app.get("/logs")
def logs_endpoint():
    return get_logs()


@app.post("/evaluate")
def evaluate_endpoint() -> Dict[str, Any]:
    """
    Batch-evaluate baseline (no RAG) vs RAG on a golden question list.
    JSON file: list of objects with a \"question\" string.
    Path: GOLDEN_DATASET_PATH, else /app/data/golden_dataset.json in Docker, else backend/data/golden_dataset.json.
    """
    p = _golden_dataset_path()
    if not p.is_file():
        raise HTTPException(
            status_code=400,
            detail=f"Golden dataset not found at {p}. Set GOLDEN_DATASET_PATH or add the file.",
        )
    return evaluate(str(p.resolve()))

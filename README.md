# RAG-Based Course Q&A System with Hallucination Detection

Production-ready Retrieval-Augmented Generation (RAG) app for university course material Q&A with hallucination detection and measurable evaluation against a no-retrieval LLM baseline.

## Results

this project does not just implement RAG, it evaluates whether retrieval actually makes answers safer and more grounded.

Using course notes from a course I am taking, **ELEC 472 Artificial Intelligence (Chapters 1-5)** and a **50-question golden dataset**, `backend/app/evaluation.py` compares a baseline LLM against the RAG pipeline on answer quality, hallucination behavior, retrieval quality, and abstention behavior.

**Main takeaway:** the RAG system reduces hallucinations from **82% to 28%**, a **54 percentage-point drop** compared with the baseline model.

| Metric              | Baseline LLM | RAG System | Why it matters                                                                                        |
| ------------------- | ------------ | ---------- | ----------------------------------------------------------------------------------------------------- |
| Questions evaluated | 50           | 50         | Evaluated on a fixed golden dataset rather than anecdotal prompts                                     |
| Accuracy            | 68%          | 62%        | Measures end-to-end answer correctness                                                                |
| Hallucination rate  | 82%          | 28%        | Lower is better; shows the RAG pipeline is substantially more grounded                                |
| Retrieval Hit@5     | N/A          | 12%        | Checks whether relevant evidence appears in the top 5 retrieved chunks                                |
| Retrieval MRR       | N/A          | 0.068      | Measures how early relevant evidence appears in ranked retrieval results                              |
| Abstention accuracy | N/A          | 50%        | Measures whether the system appropriately says "I don't know" when the notes do not support an answer |

These results show a realistic tradeoff that matters in production AI systems: the baseline LLM is slightly higher on raw accuracy, but the RAG system is much less likely to fabricate unsupported answers.

## Stack

- Frontend: React + Vite (`http://localhost:5173`)
- Backend: FastAPI (`http://localhost:8000`)
- Vector DB: PostgreSQL 16 + pgvector (`http://localhost:5432`)
- Embeddings: `text-embedding-3-small`
- Generation + judge: `gpt-4o-mini`
- Runtime: Docker Compose

## Project Structure

```
project/
├── docker-compose.yml
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── .env.example
│   └── app/
│       ├── main.py
│       ├── ingest.py
│       ├── retrieval.py
│       ├── generation.py
│       ├── hallucination.py
│       └── db.py
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   └── src/
│       ├── App.jsx
│       └── components/
└── slides/
```

## Environment Variables

Create `backend/.env` from `backend/.env.example`:

```
OPENAI_API_KEY=your_key_here
DATABASE_URL=postgresql://postgres:password@db:5432/courserag
```

## Run

1. Put course files in `slides/` (`.pdf`, `.pptx`, `.docx`)
2. Start all services:

```bash
docker-compose up --build
```

3. Trigger ingestion:

```bash
curl -X POST http://localhost:8000/ingest
```

4. Open dashboard:

- [http://localhost:5173](http://localhost:5173)

## API Endpoints

- `POST /ingest` ingests `/app/slides`
- `POST /query` body: `{"question": "..."}` runs retrieve -> generate -> judge -> logs
- `GET /logs` returns query logs newest first

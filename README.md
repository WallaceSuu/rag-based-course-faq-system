# RAG-Based Course Q&A System with Hallucination Detection

Production-ready Retrieval-Augmented Generation (RAG) app for university course material Q&A with hallucination detection.

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

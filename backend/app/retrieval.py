import json
from typing import Dict, List

from openai import OpenAI

try:
    from .db import get_conn
except ImportError:
    # Allow imports when sibling modules are executed as top-level scripts.
    from db import get_conn


def retrieve(question: str, top_k: int = 5) -> List[Dict]:
    client = OpenAI()
    emb = client.embeddings.create(model="text-embedding-3-small", input=question)
    query_embedding = emb.data[0].embedding
    embedding_json = json.dumps(query_embedding)

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT content, source, chapter, page_number,
                       1 - (embedding <=> %s::vector) AS similarity
                FROM chunks
                ORDER BY embedding <=> %s::vector
                LIMIT %s;
                """,
                (embedding_json, embedding_json, top_k),
            )
            rows = cur.fetchall()
            return [
                {
                    "content": row[0],
                    "source": row[1],
                    "chapter": row[2],
                    "page_number": row[3],
                    "similarity": float(row[4]) if row[4] is not None else 0.0,
                }
                for row in rows
            ]
    finally:
        conn.close()

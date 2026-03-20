import json
import os
from typing import Any, Dict, List

import psycopg2
from psycopg2.extras import RealDictCursor


def get_conn():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL is not set")
    return psycopg2.connect(database_url)


def init_db() -> None:
    schema_sql = """
    CREATE EXTENSION IF NOT EXISTS vector;

    CREATE TABLE IF NOT EXISTS chunks (
        id            SERIAL PRIMARY KEY,
        source        TEXT,
        chapter       TEXT,
        page_number   INTEGER,
        content       TEXT,
        embedding     vector(1536)
    );

    CREATE TABLE IF NOT EXISTS query_logs (
        id                  SERIAL PRIMARY KEY,
        question            TEXT,
        answer              TEXT,
        retrieved_chunks    JSONB,
        hallucination_flag  BOOLEAN,
        hallucination_detail TEXT,
        created_at          TIMESTAMP DEFAULT NOW()
    );
    """
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(schema_sql)
        conn.commit()
    finally:
        conn.close()


def source_already_ingested(source: str) -> bool:
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM chunks WHERE source = %s LIMIT 1;", (source,))
            return cur.fetchone() is not None
    finally:
        conn.close()


def insert_chunks(rows: List[Dict[str, Any]]) -> int:
    if not rows:
        return 0

    conn = get_conn()
    inserted = 0
    try:
        with conn.cursor() as cur:
            for row in rows:
                embedding_json = json.dumps(row["embedding"])
                cur.execute(
                    """
                    INSERT INTO chunks (source, chapter, page_number, content, embedding)
                    VALUES (%s, %s, %s, %s, %s::vector);
                    """,
                    (
                        row["source"],
                        row["chapter"],
                        row["page_number"],
                        row["content"],
                        embedding_json,
                    ),
                )
                inserted += 1
        conn.commit()
        return inserted
    finally:
        conn.close()


def log_query(
    question: str,
    answer: str,
    retrieved_chunks: List[Dict[str, Any]],
    hallucinated: bool,
    detail: str,
) -> None:
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO query_logs (
                    question, answer, retrieved_chunks, hallucination_flag, hallucination_detail
                ) VALUES (%s, %s, %s::jsonb, %s, %s);
                """,
                (
                    question,
                    answer,
                    json.dumps(retrieved_chunks),
                    hallucinated,
                    detail,
                ),
            )
        conn.commit()
    finally:
        conn.close()


def get_logs() -> List[Dict[str, Any]]:
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM query_logs ORDER BY created_at DESC;")
            rows = cur.fetchall()
            return [dict(row) for row in rows]
    finally:
        conn.close()

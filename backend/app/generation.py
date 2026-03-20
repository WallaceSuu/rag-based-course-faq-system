from typing import Dict, List

from openai import OpenAI


def _format_chunks(chunks: List[Dict]) -> str:
    lines = []
    for i, chunk in enumerate(chunks, start=1):
        lines.append(
            f"{i}. [{chunk['source']}, page {chunk['page_number']}]\n{chunk['content']}"
        )
    return "\n\n".join(lines)


def generate_answer(question: str, chunks: List[Dict]) -> str:
    client = OpenAI()
    context_block = _format_chunks(chunks)
    system_prompt = f"""
You are a helpful teaching assistant for an Artificial Intelligence course.
Answer the student's question using ONLY the context chunks provided below.
For each claim in your answer, cite the source and page number in brackets e.g. [Chapter1.pptx, slide 4].
If the context does not contain enough information to answer the question, say so explicitly.
Do not use any outside knowledge.

Context:
{context_block}
""".strip()

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ],
    )
    return response.choices[0].message.content or ""

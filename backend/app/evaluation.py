import json
from pathlib import Path
from typing import Any, Dict, List
from openai import OpenAI

from .generation import generate_answer
from .hallucination import detect_hallucination
from .retrieval import retrieve


def baseline_answer(question: str) -> str:
    # Baseline call without retrieval context (Just LLM, no RAG)
    client = OpenAI()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0,
        messages=[
            {"role": "system", "content": "You are a helpful AI assistant."},
            {"role": "user", "content": question},
        ],
    )
    return response.choices[0].message.content or ""


def evaluate(golden_dataset_path: str) -> Dict[str, Any]:
    with Path(golden_dataset_path).open(encoding="utf-8") as f:
        dataset = json.load(f)

    results: List[Dict[str, Any]] = []
    for item in dataset:
        question = str(item["question"]).strip()
        if not question:
            continue

        baseline_ans = baseline_answer(question)
        baseline_halluc = detect_hallucination(question, baseline_ans, [])

        chunks = retrieve(question)
        rag_ans = generate_answer(question, chunks)
        rag_halluc = detect_hallucination(question, rag_ans, chunks)

        results.append(
            {
                "question": question,
                "baseline_hallucinated": baseline_halluc["hallucinated"],
                "rag_hallucinated": rag_halluc["hallucinated"],
            }
        )

    total = len(results)
    if total == 0:
        summary = {
            "total_questions": 0,
            "baseline_hallucination_rate": 0.0,
            "rag_hallucination_rate": 0.0,
            "improvement": 0.0,
            "results": results,
        }
        print("No valid questions found in dataset.")
        return summary

    baseline_halluc_rate = sum(r["baseline_hallucinated"] for r in results) / total
    rag_halluc_rate = sum(r["rag_hallucinated"] for r in results) / total
    improvement = baseline_halluc_rate - rag_halluc_rate

    print(f"Baseline hallucination rate: {baseline_halluc_rate:.0%}")
    print(f"RAG hallucination rate:      {rag_halluc_rate:.0%}")
    print(f"Improvement:                 {improvement:.0%}")

    return {
        "total_questions": total,
        "baseline_hallucination_rate": baseline_halluc_rate,
        "rag_hallucination_rate": rag_halluc_rate,
        "improvement": improvement,
        "results": results,
    }
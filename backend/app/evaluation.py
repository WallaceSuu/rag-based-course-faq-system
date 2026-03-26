import json
import os
from pathlib import Path
from statistics import mean
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from dotenv import load_dotenv
from openai import OpenAI

try:
    from .generation import generate_answer
    from .hallucination import detect_hallucination
    from .retrieval import retrieve
except ImportError:
    # Allow direct execution via `py .\evaluation.py` from `backend/app`.
    from generation import generate_answer
    from hallucination import detect_hallucination
    from retrieval import retrieve


def _get_client() -> OpenAI:
    return OpenAI()


load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def baseline_answer(question: str) -> str:
    # Baseline call without retrieval context (just LLM, no RAG)
    response = _get_client().chat.completions.create(
        model="gpt-4o-mini",
        temperature=0,
        messages=[
            {"role": "system", "content": "You are a helpful AI assistant."},
            {"role": "user", "content": question},
        ],
    )
    return response.choices[0].message.content or ""


def _safe_rate(numerator: float, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def _bool_to_int(value: bool) -> int:
    return 1 if value else 0


def _looks_like_abstention(answer: str) -> bool:
    normalized = answer.lower()
    patterns = [
        "do not provide enough information",
        "does not provide enough information",
        "not enough information",
        "insufficient information",
        "cannot answer",
        "can't answer",
        "unable to answer",
        "not in the provided",
        "not in the uploaded slides",
        "outside the provided context",
        "outside the provided slides",
    ]
    return any(pattern in normalized for pattern in patterns)


def _build_expected_pairs(item: Dict[str, Any]) -> Set[Tuple[str, int]]:
    refs = item.get("evidence_refs") or []
    pairs: Set[Tuple[str, int]] = set()
    for ref in refs:
        source = str(ref.get("source", "")).strip()
        slide_number = ref.get("slide_number")
        if not source or slide_number is None:
            continue
        try:
            pairs.add((source, int(slide_number)))
        except (TypeError, ValueError):
            continue
    return pairs


def _retrieval_metrics(item: Dict[str, Any], chunks: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    expected_pairs = _build_expected_pairs(item)
    evaluation_mode = str(item.get("evaluation_mode", "answerable"))

    if evaluation_mode != "answerable" or not expected_pairs:
        return {
            "evaluated": False,
            "relevant_rank": None,
            "hit_at_1": None,
            "hit_at_3": None,
            "hit_at_5": None,
            "mrr": None,
            "context_precision_at_5": None,
        }

    rank: Optional[int] = None
    relevant_count = 0

    for index, chunk in enumerate(chunks, start=1):
        source = str(chunk.get("source", "")).strip()
        page_number = chunk.get("page_number")
        if not source or page_number is None:
            continue
        try:
            candidate = (source, int(page_number))
        except (TypeError, ValueError):
            continue
        if candidate in expected_pairs:
            relevant_count += 1
            if rank is None:
                rank = index

    top_k = min(5, len(chunks))
    return {
        "evaluated": True,
        "relevant_rank": rank,
        "hit_at_1": bool(rank is not None and rank <= 1),
        "hit_at_3": bool(rank is not None and rank <= 3),
        "hit_at_5": bool(rank is not None and rank <= 5),
        "mrr": (1.0 / rank) if rank is not None else 0.0,
        "context_precision_at_5": _safe_rate(relevant_count, top_k) if top_k else 0.0,
    }


def _judge_answer(
    question: str,
    expected_answer: str,
    actual_answer: str,
    evaluation_mode: str,
    evidence_refs: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    system_prompt = """
You are evaluating answers from a course-material QA system.

Score the answer against the expected answer and the evaluation mode.

Evaluation modes:
- answerable: the answer should be correct, grounded, and reasonably complete.
- should_abstain: the answer should clearly say the provided slides/context do not contain enough information.

Scoring rubric:
- 1.0 = correct and complete
- 0.5 = partially correct or incomplete
- 0.0 = incorrect or inappropriate

Return ONLY JSON with this schema:
{
  "correct": true,
  "score": 1.0,
  "abstained": false,
  "detail": "brief explanation"
}
""".strip()

    payload = {
        "question": question,
        "expected_answer": expected_answer,
        "actual_answer": actual_answer,
        "evaluation_mode": evaluation_mode,
        "evidence_refs": evidence_refs,
    }

    response = _get_client().chat.completions.create(
        model="gpt-4o-mini",
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(payload)},
        ],
    )

    raw = response.choices[0].message.content or "{}"
    parsed = json.loads(raw)
    score = parsed.get("score", 0.0)

    try:
        numeric_score = max(0.0, min(1.0, float(score)))
    except (TypeError, ValueError):
        numeric_score = 0.0

    return {
        "correct": bool(parsed.get("correct", False)),
        "score": numeric_score,
        "abstained": bool(parsed.get("abstained", False)),
        "detail": str(parsed.get("detail", "No detail provided.")),
    }


def _evaluate_single_answer(
    question: str,
    expected_answer: str,
    actual_answer: str,
    evaluation_mode: str,
    evidence_refs: Sequence[Dict[str, Any]],
    chunks: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    judged = _judge_answer(
        question=question,
        expected_answer=expected_answer,
        actual_answer=actual_answer,
        evaluation_mode=evaluation_mode,
        evidence_refs=evidence_refs,
    )
    hallucination = detect_hallucination(question, actual_answer, list(chunks))
    heuristic_abstained = _looks_like_abstention(actual_answer)

    return {
        "answer": actual_answer,
        "correct": judged["correct"],
        "correctness_score": judged["score"],
        "abstained": bool(judged["abstained"] or heuristic_abstained),
        "judgment_detail": judged["detail"],
        "hallucinated": hallucination["hallucinated"],
        "hallucination_detail": hallucination["detail"],
    }


def _summarize_subset(results: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(results)
    if total == 0:
        return {
            "total_questions": 0,
            "baseline_accuracy": 0.0,
            "rag_accuracy": 0.0,
            "baseline_avg_correctness_score": 0.0,
            "rag_avg_correctness_score": 0.0,
            "baseline_hallucination_rate": 0.0,
            "rag_hallucination_rate": 0.0,
            "baseline_faithfulness_rate": 0.0,
            "rag_faithfulness_rate": 0.0,
            "baseline_abstention_accuracy": 0.0,
            "rag_abstention_accuracy": 0.0,
            "retrieval_questions_evaluated": 0,
            "retrieval_hit_at_1": 0.0,
            "retrieval_hit_at_3": 0.0,
            "retrieval_hit_at_5": 0.0,
            "retrieval_mrr": 0.0,
            "context_precision_at_5": 0.0,
        }

    baseline_correct = sum(_bool_to_int(r["baseline"]["correct"]) for r in results)
    rag_correct = sum(_bool_to_int(r["rag"]["correct"]) for r in results)
    baseline_hallucinated = sum(_bool_to_int(r["baseline"]["hallucinated"]) for r in results)
    rag_hallucinated = sum(_bool_to_int(r["rag"]["hallucinated"]) for r in results)

    abstention_subset = [r for r in results if r["evaluation_mode"] == "should_abstain"]
    retrieval_subset = [r["retrieval"] for r in results if r["retrieval"]["evaluated"]]

    return {
        "total_questions": total,
        "baseline_accuracy": _safe_rate(baseline_correct, total),
        "rag_accuracy": _safe_rate(rag_correct, total),
        "baseline_avg_correctness_score": mean(r["baseline"]["correctness_score"] for r in results),
        "rag_avg_correctness_score": mean(r["rag"]["correctness_score"] for r in results),
        "baseline_hallucination_rate": _safe_rate(baseline_hallucinated, total),
        "rag_hallucination_rate": _safe_rate(rag_hallucinated, total),
        "baseline_faithfulness_rate": 1.0 - _safe_rate(baseline_hallucinated, total),
        "rag_faithfulness_rate": 1.0 - _safe_rate(rag_hallucinated, total),
        "baseline_abstention_accuracy": _safe_rate(
            sum(_bool_to_int(r["baseline"]["abstained"]) for r in abstention_subset),
            len(abstention_subset),
        ),
        "rag_abstention_accuracy": _safe_rate(
            sum(_bool_to_int(r["rag"]["abstained"]) for r in abstention_subset),
            len(abstention_subset),
        ),
        "retrieval_questions_evaluated": len(retrieval_subset),
        "retrieval_hit_at_1": _safe_rate(
            sum(_bool_to_int(bool(r["hit_at_1"])) for r in retrieval_subset),
            len(retrieval_subset),
        ),
        "retrieval_hit_at_3": _safe_rate(
            sum(_bool_to_int(bool(r["hit_at_3"])) for r in retrieval_subset),
            len(retrieval_subset),
        ),
        "retrieval_hit_at_5": _safe_rate(
            sum(_bool_to_int(bool(r["hit_at_5"])) for r in retrieval_subset),
            len(retrieval_subset),
        ),
        "retrieval_mrr": mean(r["mrr"] for r in retrieval_subset) if retrieval_subset else 0.0,
        "context_precision_at_5": (
            mean(r["context_precision_at_5"] for r in retrieval_subset) if retrieval_subset else 0.0
        ),
    }


def evaluate(golden_dataset_path: str) -> Dict[str, Any]:
    with Path(golden_dataset_path).open(encoding="utf-8") as f:
        dataset = json.load(f)

    results: List[Dict[str, Any]] = []
    for item in dataset:
        question = str(item.get("question", "")).strip()
        if not question:
            continue

        expected_answer = str(item.get("answer", "")).strip()
        evaluation_mode = str(item.get("evaluation_mode", "answerable"))
        evidence_refs = item.get("evidence_refs") or []

        baseline_ans = baseline_answer(question)
        chunks = retrieve(question)
        rag_ans = generate_answer(question, chunks)

        baseline_eval = _evaluate_single_answer(
            question=question,
            expected_answer=expected_answer,
            actual_answer=baseline_ans,
            evaluation_mode=evaluation_mode,
            evidence_refs=evidence_refs,
            chunks=[],
        )
        rag_eval = _evaluate_single_answer(
            question=question,
            expected_answer=expected_answer,
            actual_answer=rag_ans,
            evaluation_mode=evaluation_mode,
            evidence_refs=evidence_refs,
            chunks=chunks,
        )
        retrieval_eval = _retrieval_metrics(item, chunks)

        results.append(
            {
                "id": item.get("id"),
                "category": item.get("category"),
                "type": item.get("type"),
                "evaluation_mode": evaluation_mode,
                "question": question,
                "expected_answer": expected_answer,
                "evidence_refs": evidence_refs,
                "retrieval": retrieval_eval,
                "baseline": baseline_eval,
                "rag": rag_eval,
                "retrieved_chunks": [
                    {
                        "source": chunk.get("source"),
                        "slide_number": chunk.get("page_number"),
                        "similarity": chunk.get("similarity"),
                    }
                    for chunk in chunks
                ],
            }
        )

    overall = _summarize_subset(results)
    by_type = {
        result_type: _summarize_subset([r for r in results if r["type"] == result_type])
        for result_type in sorted({str(r["type"]) for r in results})
    }
    by_category = {
        category: _summarize_subset([r for r in results if r["category"] == category])
        for category in sorted({str(r["category"]) for r in results})
    }

    summary = {
        "total_questions": overall["total_questions"],
        "baseline": {
            "accuracy": overall["baseline_accuracy"],
            "avg_correctness_score": overall["baseline_avg_correctness_score"],
            "hallucination_rate": overall["baseline_hallucination_rate"],
            "faithfulness_rate": overall["baseline_faithfulness_rate"],
            "abstention_accuracy": overall["baseline_abstention_accuracy"],
        },
        "rag": {
            "accuracy": overall["rag_accuracy"],
            "avg_correctness_score": overall["rag_avg_correctness_score"],
            "hallucination_rate": overall["rag_hallucination_rate"],
            "faithfulness_rate": overall["rag_faithfulness_rate"],
            "abstention_accuracy": overall["rag_abstention_accuracy"],
        },
        "retrieval": {
            "questions_evaluated": overall["retrieval_questions_evaluated"],
            "hit_at_1": overall["retrieval_hit_at_1"],
            "hit_at_3": overall["retrieval_hit_at_3"],
            "hit_at_5": overall["retrieval_hit_at_5"],
            "mrr": overall["retrieval_mrr"],
            "context_precision_at_5": overall["context_precision_at_5"],
        },
        "deltas": {
            "accuracy": overall["rag_accuracy"] - overall["baseline_accuracy"],
            "hallucination_rate": (
                overall["baseline_hallucination_rate"] - overall["rag_hallucination_rate"]
            ),
            "faithfulness_rate": (
                overall["rag_faithfulness_rate"] - overall["baseline_faithfulness_rate"]
            ),
            "abstention_accuracy": (
                overall["rag_abstention_accuracy"] - overall["baseline_abstention_accuracy"]
            ),
        },
        "by_type": by_type,
        "by_category": by_category,
        "results": results,
    }

    print(f"Questions evaluated:          {summary['total_questions']}")
    print(f"Baseline accuracy:            {summary['baseline']['accuracy']:.0%}")
    print(f"RAG accuracy:                 {summary['rag']['accuracy']:.0%}")
    print(f"Baseline hallucination rate:  {summary['baseline']['hallucination_rate']:.0%}")
    print(f"RAG hallucination rate:       {summary['rag']['hallucination_rate']:.0%}")
    print(f"RAG retrieval Hit@5:          {summary['retrieval']['hit_at_5']:.0%}")
    print(f"RAG retrieval MRR:            {summary['retrieval']['mrr']:.3f}")
    print(f"RAG abstention accuracy:      {summary['rag']['abstention_accuracy']:.0%}")

    return summary


if __name__ == "__main__":
    import sys

    path = os.environ.get("GOLDEN_DATASET_PATH")
    if not path and len(sys.argv) > 1:
        path = sys.argv[1]
    if not path:
        path = str(Path(__file__).resolve().parent.parent / "data" / "golden_dataset.json")
    summary = evaluate(path)

    output_path = os.environ.get("EVALUATION_OUTPUT_PATH")
    if not output_path and len(sys.argv) > 2:
        output_path = sys.argv[2]

    if output_path:
        Path(output_path).write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(f"Saved evaluation summary to {output_path}")
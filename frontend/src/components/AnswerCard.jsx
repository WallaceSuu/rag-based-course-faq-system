import HallucinationBadge from "./HallucinationBadge";

export default function AnswerCard({ answer, hallucination }) {
  if (!answer) return null;

  return (
    <section className="panel">
      <h2>Answer</h2>
      <p className="answer-text">{answer}</p>
      <HallucinationBadge hallucination={hallucination} />
    </section>
  );
}

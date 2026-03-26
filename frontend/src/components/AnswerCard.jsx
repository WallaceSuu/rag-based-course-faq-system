import HallucinationBadge from "./HallucinationBadge";

export default function AnswerCard({ answer, hallucination }) {
  if (!answer) return null;

  return (
    <section className="panel answer-panel">
      <div className="section-heading">
        <p className="section-kicker">Synthesis</p>
        <h2>Answer</h2>
      </div>
      <div className="answer-body">
        <p className="answer-text">{answer}</p>
      </div>
      <HallucinationBadge hallucination={hallucination} />
    </section>
  );
}

export default function HallucinationBadge({ hallucination }) {
  if (!hallucination) return null;

  const isHallucinated = hallucination.hallucinated;
  return (
    <div className={`badge ${isHallucinated ? "badge-red" : "badge-green"}`}>
      <div className="badge-heading">
        <span className="badge-label">Grounding signal</span>
        <strong>{isHallucinated ? "Hallucination risk detected" : "Answer appears grounded"}</strong>
      </div>
      {hallucination.detail && <p className="badge-detail">{hallucination.detail}</p>}
    </div>
  );
}

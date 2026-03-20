export default function HallucinationBadge({ hallucination }) {
  if (!hallucination) return null;

  const isHallucinated = hallucination.hallucinated;
  return (
    <div className={`badge ${isHallucinated ? "badge-red" : "badge-green"}`}>
      <strong>{isHallucinated ? "⚠ Hallucination Detected" : "✓ Grounded"}</strong>
      {hallucination.detail && <p>{hallucination.detail}</p>}
    </div>
  );
}

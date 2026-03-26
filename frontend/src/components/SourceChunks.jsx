function SimilarityBar({ similarity }) {
  const percent = Math.max(0, Math.min(100, Math.round((similarity || 0) * 100)));
  return (
    <div className="similarity-block">
      <div className="similarity-label">{percent}% match</div>
      <div className="bar-bg">
        <div className="bar-fill" style={{ width: `${percent}%` }} />
      </div>
    </div>
  );
}

export default function SourceChunks({ chunks }) {
  if (!chunks?.length) return null;

  return (
    <section className="panel source-panel">
      <div className="section-heading">
        <p className="section-kicker">Evidence</p>
        <h2>Retrieved source chunks</h2>
        <p className="section-description">
          Supporting passages ranked by semantic similarity for the current answer.
        </p>
      </div>
      <div className="chunk-list">
        {chunks.map((chunk, idx) => (
          <article className="chunk-card" key={`${chunk.source}-${chunk.page_number}-${idx}`}>
            <div className="chunk-card-header">
              <span className="chunk-index">Passage {idx + 1}</span>
              <span className="chunk-source">{chunk.source}</span>
            </div>
            <p className="chunk-content">{chunk.content}</p>
            <div className="chunk-meta">
              <span>Chapter {chunk.chapter ?? "N/A"}</span>
              <span>Page {chunk.page_number ?? "N/A"}</span>
            </div>
            <SimilarityBar similarity={chunk.similarity} />
          </article>
        ))}
      </div>
    </section>
  );
}

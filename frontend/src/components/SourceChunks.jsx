function SimilarityBar({ similarity }) {
  const percent = Math.max(0, Math.min(100, Math.round((similarity || 0) * 100)));
  return (
    <div>
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
    <section className="panel">
      <h2>Retrieved Source Chunks</h2>
      <div className="chunk-list">
        {chunks.map((chunk, idx) => (
          <article className="chunk-card" key={`${chunk.source}-${chunk.page_number}-${idx}`}>
            <p>{chunk.content}</p>
            <div className="chunk-meta">
              <span>Source: {chunk.source}</span>
              <span>Chapter: {chunk.chapter}</span>
              <span>Page: {chunk.page_number}</span>
            </div>
            <SimilarityBar similarity={chunk.similarity} />
          </article>
        ))}
      </div>
    </section>
  );
}

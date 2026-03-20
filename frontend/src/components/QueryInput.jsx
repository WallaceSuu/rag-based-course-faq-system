export default function QueryInput({ question, setQuestion, onSubmit, loading }) {
  return (
    <form className="query-form" onSubmit={onSubmit}>
      <input
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        placeholder="Ask a question about the course materials..."
        disabled={loading}
      />
      <button type="submit" disabled={loading || !question.trim()}>
        {loading ? "Thinking..." : "Ask"}
      </button>
    </form>
  );
}

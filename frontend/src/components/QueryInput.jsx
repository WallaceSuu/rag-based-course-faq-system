export default function QueryInput({ question, setQuestion, onSubmit, loading }) {
  return (
    <form className="query-form" onSubmit={onSubmit}>
      <label className="query-label" htmlFor="course-question-input">
        Ask a question
      </label>
      <div className="query-form-row">
        <input
          id="course-question-input"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask about a lecture concept, slide claim, or reading passage..."
          disabled={loading}
        />
        <button type="submit" disabled={loading || !question.trim()}>
          {loading ? "Thinking..." : "Ask"}
        </button>
      </div>
      <p className="query-helper">
        Try specific prompts like “summarize chapter 3,” “compare two concepts,” or
        “what evidence supports this claim?”
      </p>
    </form>
  );
}

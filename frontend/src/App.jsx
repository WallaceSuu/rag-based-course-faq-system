import { useEffect, useState } from "react";
import AnswerCard from "./components/AnswerCard";
import QueryInput from "./components/QueryInput";
import SourceChunks from "./components/SourceChunks";

const API_BASE = "http://localhost:8000";

export default function App() {
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const [logs, setLogs] = useState([]);
  const [activeTab, setActiveTab] = useState("qa");
  const [ingestLoading, setIngestLoading] = useState(false);
  const [ingestMessage, setIngestMessage] = useState("");
  const [ingestError, setIngestError] = useState("");
  const hasResult = Boolean(result?.answer);
  const resultChunkCount = result?.chunks?.length ?? 0;
  const modeLabel = activeTab === "qa" ? "Interrogate the corpus" : "Inspect the audit trail";

  async function fetchLogs() {
    const res = await fetch(`${API_BASE}/logs`);
    if (!res.ok) throw new Error("Failed to fetch logs");
    const data = await res.json();
    setLogs(data);
  }

  useEffect(() => {
    fetchLogs().catch(() => {});
  }, []);

  async function handleIngest() {
    setIngestError("");
    setIngestMessage("");
    setIngestLoading(true);
    try {
      const res = await fetch(`${API_BASE}/ingest`, { method: "POST" });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(
          typeof data.detail === "string"
            ? data.detail
            : data.detail?.[0]?.msg || "Ingest failed"
        );
      }
      const data = await res.json();
      setIngestMessage(
        `Done: ${data.files_processed ?? 0} file(s) processed, ${data.chunks_stored ?? 0} chunk(s) stored.`
      );
    } catch (err) {
      setIngestError(err.message || "Ingest failed");
    } finally {
      setIngestLoading(false);
    }
  }

  async function onSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const res = await fetch(`${API_BASE}/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Query failed");
      }

      const data = await res.json();
      setResult(data);
      await fetchLogs();
    } catch (err) {
      setError(err.message || "Unknown error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="app">
      <section className="hero-shell">
        <header className="hero">
          <div className="hero-copy">
            <p className="eyebrow">Course intelligence console</p>
            <h1>Ask your course material like it remembers everything.</h1>
            <p className="hero-subtitle">
              Index lecture files, interrogate concepts, inspect supporting passages, and
              track grounding quality in one immersive workspace.
            </p>
          </div>

          <div className="hero-aside" aria-label="Workspace summary">
            <div className="hero-stat">
              <span className="hero-stat-label">Mode</span>
              <strong>{modeLabel}</strong>
            </div>
            <div className="hero-stat">
              <span className="hero-stat-label">Logged queries</span>
              <strong>{logs.length}</strong>
            </div>
            <div className="hero-stat">
              <span className="hero-stat-label">Current evidence set</span>
              <strong>{resultChunkCount}</strong>
            </div>
          </div>
        </header>

        <div className="tabs" role="tablist" aria-label="Workspace sections">
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === "qa"}
            className={activeTab === "qa" ? "tab active" : "tab"}
            onClick={() => setActiveTab("qa")}
          >
            <span className="tab-label">Query</span>
            <span className="tab-caption">Ask and inspect evidence</span>
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === "logs"}
            className={activeTab === "logs" ? "tab active" : "tab"}
            onClick={() => setActiveTab("logs")}
          >
            <span className="tab-label">Logs</span>
            <span className="tab-caption">Review prior runs</span>
          </button>
        </div>
      </section>

      {activeTab === "qa" && (
        <section className="qa-layout">
          <section className="panel query-panel">
            <div className="panel-header">
              <div className="panel-header-text">
                <p className="section-kicker">Workspace</p>
                <h2>Interrogate the indexed course material</h2>
                <p className="ingest-hint">
                  Pull documents from the server <code>slides/</code> directory, then ask focused
                  questions and inspect the exact passages used to answer them.
                </p>
              </div>
              <div className="query-panel-actions">
                <div className="query-panel-note">
                  PDF, PPTX, and DOCX files are indexed once and skipped on repeat runs.
                </div>
                <button
                  type="button"
                  className="btn-ingest"
                  onClick={handleIngest}
                  disabled={ingestLoading}
                  aria-label="Ingest course files from the slides folder"
                >
                  {ingestLoading ? "Ingesting..." : "Ingest slides"}
                </button>
              </div>
            </div>
            <div className="status-stack" aria-live="polite">
              {ingestLoading && <div className="spinner">Indexing documents...</div>}
              {ingestError && <p className="error">{ingestError}</p>}
              {ingestMessage && <p className="ingest-success">{ingestMessage}</p>}
            </div>

            <QueryInput
              question={question}
              setQuestion={setQuestion}
              onSubmit={onSubmit}
              loading={loading}
            />
            <div className="status-stack" aria-live="polite">
              {loading && <div className="spinner">Synthesizing answer...</div>}
              {error && <p className="error">{error}</p>}
            </div>
          </section>

          <div className={hasResult ? "results-layout has-result" : "results-layout"}>
            <AnswerCard answer={result?.answer} hallucination={result?.hallucination} />
            <SourceChunks chunks={result?.chunks || []} />
          </div>
        </section>
      )}

      {activeTab === "logs" && (
        <section className="panel logs-panel">
          <div className="panel-header logs-header">
            <div className="panel-header-text">
              <p className="section-kicker">Audit trail</p>
              <h2>Review previous question runs</h2>
              <p className="ingest-hint">
                Inspect timestamps, prompt history, and hallucination outcomes from prior queries.
              </p>
            </div>
            <button className="refresh" onClick={fetchLogs}>
              Refresh logs
            </button>
          </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Created At</th>
                  <th>Question</th>
                  <th>Hallucination</th>
                  <th>Detail</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((log) => (
                  <tr key={log.id}>
                    <td>{new Date(log.created_at).toLocaleString()}</td>
                    <td>{log.question}</td>
                    <td>
                      <span
                        className={
                          log.hallucination_flag ? "log-flag log-flag-alert" : "log-flag log-flag-safe"
                        }
                      >
                        {log.hallucination_flag ? "Flagged" : "Clear"}
                      </span>
                    </td>
                    <td>{log.hallucination_detail}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </main>
  );
}

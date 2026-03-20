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

  async function fetchLogs() {
    const res = await fetch(`${API_BASE}/logs`);
    if (!res.ok) throw new Error("Failed to fetch logs");
    const data = await res.json();
    setLogs(data);
  }

  useEffect(() => {
    fetchLogs().catch(() => {});
  }, []);

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
      <h1>RAG-Based Course Q&A Dashboard</h1>
      <div className="tabs">
        <button
          className={activeTab === "qa" ? "tab active" : "tab"}
          onClick={() => setActiveTab("qa")}
        >
          Query
        </button>
        <button
          className={activeTab === "logs" ? "tab active" : "tab"}
          onClick={() => setActiveTab("logs")}
        >
          Logs
        </button>
      </div>

      {activeTab === "qa" && (
        <>
          <section className="panel">
            <h2>Query Panel</h2>
            <QueryInput
              question={question}
              setQuestion={setQuestion}
              onSubmit={onSubmit}
              loading={loading}
            />
            {loading && <div className="spinner">Loading...</div>}
            {error && <p className="error">{error}</p>}
          </section>

          <AnswerCard answer={result?.answer} hallucination={result?.hallucination} />
          <SourceChunks chunks={result?.chunks || []} />
        </>
      )}

      {activeTab === "logs" && (
        <section className="panel">
          <h2>Logs Panel</h2>
          <button className="refresh" onClick={fetchLogs}>
            Refresh Logs
          </button>
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
                    <td>{log.hallucination_flag ? "Yes" : "No"}</td>
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

import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import Markdown from "react-markdown";
import "./style.css";

type Citation = {
  id: number;
  title: string;
  url: string;
  passage: string;
  score: number;
};
type Answer = {
  mode: string;
  label: string;
  answer: string;
  citations: Citation[];
  trace_id: string;
};
type Config = {
  live_ready: boolean;
  access_token_required: boolean;
  model: string;
  max_upload_bytes: number;
  max_pdf_pages: number;
};
type Usage = {
  scope: string;
  started_at: string;
  tavily: {
    month: string;
    credits_reserved: number;
    configured_monthly_credits: number;
  };
  groq: {
    day: string;
    minute: string;
    requests_today: number;
    requests_this_minute: number;
    tokens_today: number;
    tokens_this_minute: number;
    configured_rpd: number;
    configured_rpm: number;
    configured_tpd: number;
    configured_tpm: number;
    last_provider_headers: Record<string, string>;
  };
};

function App() {
  const [mode, setMode] = useState<"demo" | "live">("demo");
  const [tab, setTab] = useState("sample");
  const [document, setDocument] = useState("");
  const [title, setTitle] = useState("Why cities plant trees");
  const [draft, setDraft] = useState("");
  const [url, setUrl] = useState("");
  const [pdfUrl, setPdfUrl] = useState("");
  const [original, setOriginal] = useState(false);
  const [selection, setSelection] = useState("");
  const [question, setQuestion] = useState("");
  const [questions, setQuestions] = useState<string[]>([]);
  const [answer, setAnswer] = useState<Answer | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [config, setConfig] = useState<Config | null>(null);
  const [usage, setUsage] = useState<Usage | null>(null);
  const [token, setToken] = useState("");
  const reader = useRef<HTMLElement>(null);

  async function api(path: string, init?: RequestInit) {
    const r = await fetch("/api" + path, {
      ...init,
      headers: {
        ...(init?.body instanceof FormData
          ? {}
          : { "Content-Type": "application/json" }),
        ...(token ? { "X-Live-Token": token } : {}),
        ...init?.headers,
      },
    });
    const data = await r.json();
    if (!r.ok)
      throw new Error(
        typeof data.detail === "string"
          ? data.detail
          : "Request failed. Check the input and try again.",
      );
    return data;
  }
  async function refreshUsage() {
    try {
      setUsage(await api("/usage"));
    } catch {
      /* Non-critical status panel. */
    }
  }
  async function sample() {
    const data = await api("/sample");
    replaceDocument(data.text, "Why cities plant trees");
    setQuestions(data.questions);
    setTab("sample");
  }
  useEffect(() => {
    Promise.all([
      sample(),
      api("/config").then(setConfig),
      refreshUsage(),
    ]).catch((e) => setError(e.message));
  }, []);
  useEffect(
    () => () => {
      if (pdfUrl) URL.revokeObjectURL(pdfUrl);
    },
    [pdfUrl],
  );

  function replaceDocument(text: string, name: string) {
    setDocument(text);
    setTitle(name);
    setSelection("");
    setAnswer(null);
    setError("");
    setQuestion("");
    setPdfUrl("");
    setOriginal(false);
  }
  async function loadText() {
    setBusy(true);
    setError("");
    try {
      const data = await api("/document/text", {
        method: "POST",
        body: JSON.stringify({ text: draft }),
      });
      replaceDocument(data.text, "Your text");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function loadUrl() {
    setBusy(true);
    setError("");
    try {
      const data = await api("/document/url", {
        method: "POST",
        body: JSON.stringify({ url }),
      });
      replaceDocument(data.text, new URL(url).hostname);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function loadPdf(file?: File) {
    if (!file) return;
    if (file.size > (config?.max_upload_bytes ?? 5000000)) {
      setError("PDF must be 5 MB or smaller (or the configured server limit).");
      return;
    }
    if ((await file.slice(0, 5).text()) !== "%PDF-") {
      setError("Choose a valid PDF file.");
      return;
    }
    replaceDocument("", file.name);
    setPdfUrl(
      URL.createObjectURL(new Blob([file], { type: "application/pdf" })),
    );
    setBusy(true);
    try {
      const data = new FormData();
      data.append("file", file);
      const result = await api("/document/pdf", { method: "POST", body: data });
      setDocument(result.text);
    } catch (e) {
      setError((e as Error).message);
      setOriginal(true);
    } finally {
      setBusy(false);
    }
  }
  function captureSelection() {
    const selected = window.getSelection();
    if (
      selected &&
      reader.current?.contains(selected.anchorNode) &&
      reader.current.contains(selected.focusNode)
    ) {
      const text = selected.toString().trim();
      if (text) setSelection(text.slice(0, 2000));
    }
  }
  async function ask(value = question) {
    if (!value.trim()) return;
    setQuestion(value);
    setBusy(true);
    setError("");
    setAnswer(null);
    try {
      setAnswer(
        await api("/ask", {
          method: "POST",
          body: JSON.stringify({
            mode,
            question: value,
            passage: selection,
            document,
          }),
        }),
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
      await refreshUsage();
    }
  }
  function changeMode(next: "demo" | "live") {
    setMode(next);
    setAnswer(null);
    setError("");
  }
  return (
    <div className="app">
      <header className="top">
        <a className="brand" href="/" aria-label="Passage Scout home">
          <span className="mark">↗</span> Passage Scout
        </a>
        <span className="eyebrow">A FIELD GUIDE TO BETTER QUESTIONS</span>
        <a
          href="https://github.com/flyoungiv/passage-scout"
          target="_blank"
          rel="noreferrer"
        >
          Source ↗
        </a>
      </header>
      <section className="intro">
        <div>
          <p className="eyebrow">READ CLOSER. LOOK FURTHER.</p>
          <h1>
            A passage is just
            <br />
            the beginning.
          </h1>
          <p className="subhead">
            Bring one document. Highlight an idea.
            <br />
            Follow your question to the evidence.
          </p>
        </div>
        <div className="mode-card">
          <span className="eyebrow">YOUR EXPLORATION MODE</span>
          <div className="switch" role="group" aria-label="Response mode">
            <button
              disabled={busy}
              aria-pressed={mode === "demo"}
              onClick={() => changeMode("demo")}
            >
              Demo responses
            </button>
            <button
              disabled={busy}
              aria-pressed={mode === "live"}
              onClick={() => changeMode("live")}
            >
              Live RAG
            </button>
          </div>
          <p>
            {mode === "demo"
              ? "Prepared sample answers. No search or model calls."
              : "Real web search → extraction → ranking → generation."}
          </p>
          <span className="status">
            <i className={mode === "live" ? "live" : ""} />
            {mode === "demo"
              ? "Demo is on · no keys needed"
              : config?.live_ready
                ? "Live providers configured"
                : "Live needs Tavily + Groq keys"}
          </span>
        </div>
      </section>
      <section className="workspace">
        <div className="document-pane">
          <div className="pane-top">
            <span className="step">01</span>
            <h2>Your document</h2>
            <span className="muted">One source at a time</span>
          </div>
          <div className="tabs" role="group" aria-label="Document source">
            {[
              ["sample", "Try the sample"],
              ["text", "Paste text"],
              ["url", "Article URL"],
              ["pdf", "Upload PDF"],
            ].map(([key, label]) => (
              <button
                key={key}
                disabled={busy}
                aria-pressed={tab === key}
                onClick={() => {
                  setTab(key);
                  setError("");
                  if (key === "sample")
                    sample().catch((e) => setError(e.message));
                }}
              >
                {label}
              </button>
            ))}
          </div>
          {tab === "text" && (
            <div className="input-box">
              <label htmlFor="text">Plain text or Markdown</label>
              <textarea
                id="text"
                rows={5}
                value={draft}
                maxLength={100000}
                onChange={(e) => setDraft(e.target.value)}
                placeholder="Paste the text you want to explore…"
              />
              <button
                className="primary"
                disabled={busy || !draft.trim()}
                onClick={loadText}
              >
                Open in reader
              </button>
            </div>
          )}
          {tab === "url" && (
            <form
              className="input-box"
              onSubmit={(e) => {
                e.preventDefault();
                loadUrl();
              }}
            >
              <label htmlFor="url">Public article URL</label>
              <input
                id="url"
                type="url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://example.com/article"
                required
              />
              <p className="small">
                Fetching an article contacts that website, even in Demo. No
                login pages.
              </p>
              <button className="primary" disabled={busy}>
                Fetch article
              </button>
            </form>
          )}
          {tab === "pdf" && (
            <div className="input-box">
              <label htmlFor="pdf">Selectable-text PDF</label>
              <input
                id="pdf"
                type="file"
                accept="application/pdf,.pdf"
                disabled={busy}
                onChange={(e) => loadPdf(e.target.files?.[0])}
              />
              <p className="small">
                Up to {(config?.max_upload_bytes ?? 5000000) / 1000000} MB ·{" "}
                {config?.max_pdf_pages ?? 30} pages · No OCR
              </p>
            </div>
          )}
          <div className="reader-heading">
            <div>
              <span className="eyebrow">
                {original ? "ORIGINAL PDF" : "FORMATTED READER"}
              </span>
              <h3>{title}</h3>
            </div>
            {pdfUrl && (
              <button
                onClick={() => {
                  setOriginal(!original);
                  setSelection("");
                }}
              >
                {original ? "Formatted text" : "Original PDF"} ↗
              </button>
            )}
          </div>
          {original && pdfUrl ? (
            <div>
              <p className="small pdf-note">
                Original PDF fallback. Passage capture is unavailable here; type
                your question alongside it.
              </p>
              <iframe
                title="Original PDF"
                src={pdfUrl}

                className="pdf-view"
              />
              <a href={pdfUrl} target="_blank" rel="noreferrer">
                Open original PDF in a new tab ↗
              </a>
            </div>
          ) : (
            <article
              ref={reader}
              className="reader"
              onMouseUp={captureSelection}
              onKeyUp={captureSelection}
              onTouchEnd={captureSelection}
            >
              <Markdown
                skipHtml
                allowedElements={[
                  "h1",
                  "h2",
                  "h3",
                  "h4",
                  "p",
                  "strong",
                  "em",
                  "ul",
                  "ol",
                  "li",
                  "blockquote",
                  "code",
                  "pre",
                  "hr",
                  "br",
                ]}
                unwrapDisallowed
              >
                {document || "Your document will appear here."}
              </Markdown>
            </article>
          )}
          <div className="reader-foot">
            {original
              ? "Ask about the document using the question box."
              : "Select text in the reader to focus your question."}
            <span>{document.length.toLocaleString()} characters</span>
          </div>
        </div>
        <aside className="question-pane">
          <div className="pane-top">
            <span className="step">02</span>
            <h2>Follow an idea</h2>
          </div>
          <div className="question-body">
            <span className="badge">
              {mode === "demo" ? "DEMO RESPONSES" : "LIVE RAG"}
            </span>
            <div className="selection">
              <div className="selection-head">
                <label htmlFor="passage">Selected passage</label>
                {selection && (
                  <button onClick={() => setSelection("")}>Clear</button>
                )}
              </div>
              <textarea
                id="passage"
                rows={3}
                value={selection}
                maxLength={2000}
                onChange={(e) => setSelection(e.target.value)}
                placeholder={
                  original
                    ? "Optionally paste a passage from the PDF…"
                    : "Highlight a passage, or paste one here…"
                }
              />
              <span className="small">{selection.length}/2,000 characters</span>
            </div>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                ask();
              }}
            >
              <label htmlFor="question">What are you curious about?</label>
              <textarea
                id="question"
                rows={3}
                maxLength={600}
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder="Ask a question about this idea…"
              />
              <button
                className="primary ask"
                disabled={busy || !question.trim()}
              >
                {busy
                  ? "Working…"
                  : mode === "demo"
                    ? "Explore demo answer ↗"
                    : "Search & answer ↗"}
              </button>
            </form>
            {mode === "live" && (
              <p className="small">
                Your question and selected passage go to Tavily and Groq. The
                full document stays out of provider requests.
              </p>
            )}
            {mode === "demo" && tab === "sample" && (
              <div className="prepared">
                <p className="eyebrow">START WITH A PREPARED QUESTION</p>
                {questions.map((q) => (
                  <button key={q} disabled={busy} onClick={() => ask(q)}>
                    {q}
                    <span>↗</span>
                  </button>
                ))}
              </div>
            )}
            {error && (
              <div role="alert" className="error">
                {error}
                {mode === "live" && (
                  <button onClick={() => changeMode("demo")}>
                    Switch to Demo
                  </button>
                )}
              </div>
            )}
            <div aria-live="polite">
              {answer && (
                <section className="answer">
                  <span className="badge">{answer.label}</span>
                  <h3>A little more context</h3>
                  <p className="answer-text">
                    {answer.answer.split(/(\[\d+\])/g).map((part, index) => {
                      const id = Number(part.slice(1, -1));
                      return /^\[\d+\]$/.test(part) &&
                        answer.citations.some((c) => c.id === id) ? (
                        <a key={index} href={"#evidence-" + id}>
                          {part}
                        </a>
                      ) : (
                        part
                      );
                    })}
                  </p>
                  {answer.citations.length > 0 && (
                    <>
                      <h4>Follow the evidence</h4>
                      {answer.citations.map((c) => (
                        <details key={c.id} id={"evidence-" + c.id}>
                          <summary>
                            [{c.id}] {c.title}
                          </summary>
                          <p>{c.passage}</p>
                          <a href={c.url} target="_blank" rel="noreferrer">
                            Open source ↗
                          </a>
                        </details>
                      ))}
                    </>
                  )}
                  <p className="trace">
                    Trace <code>{answer.trace_id}</code>
                  </p>
                </section>
              )}
            </div>
            {!answer && !busy && (
              <div className="empty">
                <span>↗</span>
                <p>
                  Good questions lead somewhere.
                  <br />
                  Your answer and evidence appear here.
                </p>
              </div>
            )}
          </div>
        </aside>
      </section>
      <section className="bottom">
        <details className="usage">
          <summary>
            Usage & observability <span>App-tracked estimates</span>
          </summary>
          {usage && (
            <>
              <p>
                {usage.scope} Configured limits are examples, not provider
                guarantees.
              </p>
              <div className="usage-grid">
                <div>
                  <h4>Tavily · month {usage.tavily.month}</h4>
                  <p>
                    {usage.tavily.credits_reserved} /{" "}
                    {usage.tavily.configured_monthly_credits} credits reserved
                  </p>
                  <small>
                    Conservative 2-credit reservation per attempted live
                    request: basic search + up to 5 basic extractions. Not an
                    account balance.
                  </small>
                </div>
                <div>
                  <h4>Groq · UTC day {usage.groq.day}</h4>
                  <p>
                    {usage.groq.tokens_today.toLocaleString()} /{" "}
                    {usage.groq.configured_tpd.toLocaleString()} tokens
                  </p>
                  <p>
                    {usage.groq.requests_today} / {usage.groq.configured_rpd}{" "}
                    requests
                  </p>
                  <small>
                    Provider-reported tokens when available; conservative
                    reservation otherwise.
                  </small>
                </div>
                <div>
                  <h4>Groq · minute {usage.groq.minute.slice(-5)} UTC</h4>
                  <p>
                    {usage.groq.tokens_this_minute} /{" "}
                    {usage.groq.configured_tpm} tokens
                  </p>
                  <p>
                    {usage.groq.requests_this_minute} /{" "}
                    {usage.groq.configured_rpm} requests
                  </p>
                  <small>
                    App uses UTC clock windows; provider rolling windows may
                    differ.
                  </small>
                </div>
              </div>
              <h4>Latest provider rate headers</h4>
              <p className="small">
                Request headers refer to requests/day; token headers to
                tokens/minute. This is a last-response snapshot, not a current
                balance.
              </p>
              <pre>
                {Object.keys(usage.groq.last_provider_headers).length
                  ? JSON.stringify(usage.groq.last_provider_headers, null, 2)
                  : "No live provider response yet."}
              </pre>
              <button onClick={refreshUsage}>Refresh usage</button>
              <p className="small">
                Counting since {usage.started_at}. Stage spans, latency, errors,
                token counts and retrieval counts use OpenTelemetry. Logs carry
                trace IDs without document text.
              </p>
            </>
          )}
        </details>
        <details>
          <summary>Server access</summary>
          <p className="small">
            For a server configured with an access token. Held in this tab’s
            memory only.
          </p>
          <label htmlFor="token">Access token</label>
          <input
            id="token"
            type="password"
            autoComplete="off"
            value={token}
            onChange={(e) => setToken(e.target.value)}
          />
        </details>
      </section>
      <footer>
        <span>Passage Scout</span>
        <p>
          Evidence is a starting point. Open the sources and check the claims.
        </p>
        <span>Built to learn, made to explore.</span>
      </footer>
    </div>
  );
}

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);

import { useState, useRef } from "react";

const DEFAULT_ENDPOINT = "http://localhost:8000/generate";

export default function App() {
  const [endpoint, setEndpoint] = useState(DEFAULT_ENDPOINT);
  const [prompt, setPrompt] = useState("");
  const [output, setOutput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [ttft, setTtft] = useState(null);
  const [error, setError] = useState(null);
  const outputRef = useRef(null);

  async function handleSend() {
    if (!prompt.trim() || streaming) return;

    setOutput("");
    setError(null);
    setTtft(null);
    setStreaming(true);

    const startTime = performance.now();
    let firstTokenAt = null;

    try {
      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt }),
      });
      setPrompt("");

      if (!res.ok || !res.body) {
        throw new Error(`Request failed: ${res.status}`);
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // SSE events are separated by a blank line
        const events = buffer.split("\n\n");
        buffer = events.pop();

        for (const evt of events) {
          const line = evt.trim();
          if (!line.startsWith("data:")) continue;
          const content = line.slice(5).trim();

          if (content === "[DONE]" || content === "[Done]") continue;

          if (firstTokenAt === null) {
            firstTokenAt = performance.now();
            setTtft(Math.round(firstTokenAt - startTime));
          }

          setOutput((prev) => {
            const next = prev + " " + content;
            requestAnimationFrame(() => {
              if (outputRef.current) {
                outputRef.current.scrollTop = outputRef.current.scrollHeight;
              }
            });
            return next;
          });
        }
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setStreaming(false);
    }
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  return (
    <div className="page">
      <div className="header">
        <input
          className="endpoint-input"
          value={endpoint}
          onChange={(e) => setEndpoint(e.target.value)}
          spellCheck={false}
        />
        {ttft !== null && <span className="ttft">TTFT {ttft}ms</span>}
      </div>

      <div className="output" ref={outputRef}>
        {error && <div className="error">{error}</div>}
        {!error && output && (
          <div className="message">
            {output}
            {streaming && <span className="cursor" />}
          </div>
        )}
        {!error && !output && !streaming && (
          <div className="placeholder">Response will stream here</div>
        )}
      </div>

      <div className="composer">
        <textarea
          rows={2}
          placeholder="Ask a doubt..."
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          onKeyDown={handleKeyDown}
        />
        <button onClick={handleSend} disabled={streaming || !prompt.trim()}>
          {streaming ? "Streaming..." : "Send"}
        </button>
      </div>
    </div>
  );
}

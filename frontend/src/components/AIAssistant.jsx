import { useState, useRef, useEffect } from "react";
import { toast } from "react-hot-toast";
import {
  Bot, Send, X, Shield, Lightbulb, AlertTriangle,
  Sparkles, ChevronUp, MessageSquare,
} from "lucide-react";
import { aiService } from "../services/api/aiService";

export default function AIAssistant() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [aiAvailable, setAiAvailable] = useState(null);
  const [showInsights, setShowInsights] = useState(false);
  const [insights, setInsights] = useState(null);
  const [insightsLoading, setInsightsLoading] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    let cancelled = false;
    aiService.getStatus()
      .then((res) => { if (!cancelled) setAiAvailable(res.available === true); })
      .catch(() => { if (!cancelled) setAiAvailable(false); });
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function handleSend() {
    const text = input.trim();
    if (!text || loading) return;
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setLoading(true);

    try {
      const res = await aiService.getSecurityTips();
      const reply = res?.response || res?.message || "Am analizat configuratia. Verifica recomandarile din sectiunea de mai sus.";
      setMessages((prev) => [...prev, { role: "assistant", content: reply }]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `Eroare: ${err.message || "Eroare de comunicare"}`, error: true },
      ]);
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  async function loadInsights() {
    setInsightsLoading(true);
    setShowInsights(true);
    try {
      const res = await aiService.getSecurityTips();
      setInsights(res);
    } catch (err) {
      toast.error(err.message || "Nu s-au putut incarca recomandarile.");
    } finally {
      setInsightsLoading(false);
    }
  }

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="ai-fab"
        aria-label="Deschide asistentul AI"
        title="Asistent AI"
      >
        <Bot size={22} strokeWidth={2} aria-hidden="true" />
      </button>
    );
  }

  return (
    <div className="ai-window" role="dialog" aria-label="Asistent AI">
      <div className="ai-header">
        <div style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
          <Bot size={18} strokeWidth={2} aria-hidden="true" />
          <span style={{ fontWeight: 600 }}>Asistent AI</span>
          {aiAvailable === true && (
            <span className="badge-soft">Activ</span>
          )}
          {aiAvailable === false && (
            <span className="badge-warning">Indisponibil</span>
          )}
        </div>
        <div className="ai-header-actions">
          <button onClick={loadInsights} aria-label="Recomandari" title="Recomandari">
            <Lightbulb size={16} strokeWidth={2} aria-hidden="true" />
          </button>
          <button onClick={() => setIsOpen(false)} aria-label="Inchide" title="Inchide">
            <X size={16} strokeWidth={2} aria-hidden="true" />
          </button>
        </div>
      </div>

      {aiAvailable === false && (
        <div className="ai-banner">
          <AlertTriangle size={14} strokeWidth={2} aria-hidden="true" />
          <span>AI indisponibil. Verifica cheia API Groq in configuratie.</span>
        </div>
      )}

      {showInsights && (
        <div className="ai-insights">
          <div className="ai-insights-header">
            <h4>
              <Sparkles size={14} strokeWidth={2} aria-hidden="true" />
              Recomandari
            </h4>
            <button
              type="button"
              className="ghost-button"
              style={{ padding: "0.3rem 0.5rem", fontSize: "0.75rem" }}
              onClick={() => setShowInsights(false)}
              aria-label="Inchide recomandari"
            >
              <ChevronUp size={14} strokeWidth={2} aria-hidden="true" />
            </button>
          </div>

          {insightsLoading ? (
            <div className="hint" style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
              <span className="anim-spin" aria-hidden="true">
                <Shield size={14} strokeWidth={2} />
              </span>
              Se analizeaza...
            </div>
          ) : insights?.available === false ? (
            <p className="hint">{insights.message || "AI indisponibil."}</p>
          ) : insights ? (
            <div style={{ maxHeight: "12rem", overflowY: "auto" }}>
              {insights.response ? (
                <p style={{ fontSize: "0.85rem", whiteSpace: "pre-wrap", margin: 0 }}>{insights.response}</p>
              ) : insights.summary ? (
                <p style={{ fontSize: "0.85rem", margin: 0 }}>{insights.summary}</p>
              ) : (
                <p className="hint">Nu sunt recomandari momentan.</p>
              )}
            </div>
          ) : null}
        </div>
      )}

      <div className="ai-messages">
        {messages.length === 0 && !loading && (
          <div className="ai-empty">
            <MessageSquare size={28} strokeWidth={2} aria-hidden="true" style={{ opacity: 0.4, margin: "0 auto" }} />
            <p style={{ fontSize: "0.85rem" }}>Intreaba-ma despre securitatea site-urilor tale</p>
            <div className="ai-suggestions">
              {["Ce vulnerabilitati am?", "Cum imbunatatesc securitatea?", "Recomandari rapide"].map((q) => (
                <button
                  key={q}
                  type="button"
                  onClick={() => setInput(q)}
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`ai-bubble ${msg.error ? "ai-bubble-error" : msg.role === "user" ? "ai-bubble-user" : "ai-bubble-assistant"}`}>
            <p style={{ margin: 0, whiteSpace: "pre-wrap" }}>{msg.content}</p>
          </div>
        ))}

        {loading && (
          <div className="ai-bubble ai-bubble-assistant" style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
            <span className="anim-spin" aria-hidden="true">
              <Shield size={14} strokeWidth={2} />
            </span>
            <span style={{ fontSize: "0.85rem" }}>Analizez...</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <div>
        <div className="ai-input-row">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Scrie un mesaj..."
            rows={1}
            disabled={loading}
          />
          <button
            type="button"
            onClick={handleSend}
            disabled={loading || !input.trim()}
            aria-label="Trimite mesajul"
          >
            <Send size={16} strokeWidth={2} aria-hidden="true" />
          </button>
        </div>
        <p className="ai-input-hint">Enter pentru trimitere, Shift+Enter pentru linie noua</p>
      </div>
    </div>
  );
}
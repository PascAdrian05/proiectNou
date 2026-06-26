import { useState, useRef, useEffect } from "react";
import { toast } from "react-hot-toast";
import {
  Bot, Send, X, Loader2, Shield, Lightbulb, AlertTriangle,
  Sparkles, ChevronUp, MessageSquare
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
        className="fixed bottom-6 right-6 z-40 w-14 h-14 rounded-full bg-primary text-primary-content shadow-lg hover:shadow-xl hover:scale-105 transition-all flex items-center justify-center"
        title="Asistent AI"
      >
        <Bot className="w-6 h-6" />
      </button>
    );
  }

  return (
    <div className="fixed bottom-6 right-6 z-40 w-80 sm:w-96 shadow-2xl rounded-2xl bg-base-100 border border-base-300 overflow-hidden flex flex-col max-h-[600px]">
      <div className="bg-primary text-primary-content p-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Bot className="w-5 h-5" />
          <span className="font-semibold">Asistent AI</span>
          {aiAvailable === true && <span className="badge badge-sm badge-ghost text-primary-content/80">Activ</span>}
          {aiAvailable === false && <span className="badge badge-sm badge-warning text-xs">Indisponibil</span>}
        </div>
        <div className="flex items-center gap-1">
          <button onClick={loadInsights} className="btn btn-ghost btn-xs btn-square text-primary-content hover:bg-primary/80" title="Recomandari">
            <Lightbulb className="w-4 h-4" />
          </button>
          <button onClick={() => setIsOpen(false)} className="btn btn-ghost btn-xs btn-square text-primary-content hover:bg-primary/80">
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {aiAvailable === false && (
        <div className="bg-warning/10 text-warning px-4 py-2 text-xs flex items-center gap-2 border-b border-warning/20">
          <AlertTriangle className="w-3 h-3 shrink-0" />
          <span>AI indisponibil. Verifica cheia API Groq in configuratie.</span>
        </div>
      )}

      {showInsights && (
        <div className="border-b border-base-300 bg-base-200/50">
          <div className="px-4 py-3">
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-sm font-semibold flex items-center gap-1">
                <Sparkles className="w-4 h-4 text-warning" />
                Recomandari
              </h4>
              <button onClick={() => setShowInsights(false)} className="btn btn-ghost btn-xs btn-square">
                <ChevronUp className="w-4 h-4" />
              </button>
            </div>

            {insightsLoading ? (
              <div className="flex items-center gap-2 text-sm text-base-content/60 py-2">
                <Loader2 className="w-4 h-4 animate-spin" />
                Se analizeaza...
              </div>
            ) : insights?.available === false ? (
              <p className="text-sm text-base-content/60 py-1">{insights.message || "AI indisponibil."}</p>
            ) : insights ? (
              <div className="space-y-2 max-h-48 overflow-y-auto">
                {insights.response ? (
                  <p className="text-sm whitespace-pre-wrap leading-relaxed">{insights.response}</p>
                ) : insights.summary ? (
                  <p className="text-sm">{insights.summary}</p>
                ) : (
                  <p className="text-sm text-base-content/60">Nu sunt recomandari momentan.</p>
                )}
              </div>
            ) : null}
          </div>
        </div>
      )}

      <div className="flex-1 overflow-y-auto p-4 space-y-3 min-h-0" style={{ maxHeight: "320px" }}>
        {messages.length === 0 && !loading && (
          <div className="text-center py-8">
            <MessageSquare className="w-8 h-8 text-base-content/20 mx-auto mb-2" />
            <p className="text-sm text-base-content/40">
              Intreaba-ma despre securitatea site-urilor tale
            </p>
            <div className="flex flex-wrap gap-2 justify-center mt-3">
              {["Ce vulnerabilitati am?", "Cum imbunatatesc securitatea?", "Recomandari rapide"].map((q) => (
                <button
                  key={q}
                  onClick={() => setInput(q)}
                  className="btn btn-ghost btn-xs bg-base-200 hover:bg-base-300"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            <div className={`max-w-[85%] rounded-2xl px-4 py-2 text-sm ${
              msg.role === "user"
                ? "bg-primary text-primary-content rounded-br-lg"
                : msg.error
                  ? "bg-error/10 text-error border border-error/20 rounded-bl-lg"
                  : "bg-base-200 text-base-content rounded-bl-lg"
            }`}>
              <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="max-w-[85%] rounded-2xl rounded-bl-lg px-4 py-3 bg-base-200">
              <div className="flex items-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin text-primary" />
                <span className="text-sm text-base-content/60">Analizez...</span>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <div className="border-t border-base-300 p-3 bg-base-200/50">
        <div className="flex gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Scrie un mesaj..."
            rows={1}
            className="textarea textarea-bordered textarea-sm flex-1 resize-none min-h-[36px] max-h-[80px]"
            disabled={loading}
          />
          <button
            onClick={handleSend}
            disabled={loading || !input.trim()}
            className="btn btn-primary btn-sm btn-square"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
          </button>
        </div>
        <p className="text-[10px] text-base-content/30 mt-1 text-center">
          Enter pentru trimitere, Shift+Enter pentru linie noua
        </p>
      </div>
    </div>
  );
}

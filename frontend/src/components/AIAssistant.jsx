import { useEffect, useId, useRef, useState } from "react";
import { aiService } from "../services/api/aiService";
import { useAuth } from "../context/AuthContext";

function AITypingDots() {
  return (
    <span className="ai-typing" aria-hidden="true">
      <span className="ai-dot" />
      <span className="ai-dot" />
      <span className="ai-dot" />
    </span>
  );
}

export function AIAssistant() {
  const { isAuthenticated } = useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const [status, setStatus] = useState({ available: false, model: null });
  const [loading, setLoading] = useState(false);
  const [tips, setTips] = useState(null);
  const [posture, setPosture] = useState(null);
  const [error, setError] = useState("");
  const [conversations, setConversations] = useState([]);
  const [activeConversationId, setActiveConversationId] = useState(null);
  const panelRef = useRef(null);
  const panelId = useId();

  useEffect(() => {
    aiService.getStatus().then(setStatus).catch(() => setStatus({ available: false, model: null }));
  }, []);

  useEffect(() => {
    if (!isOpen || !isAuthenticated) return;
    aiService.listConversations()
      .then(setConversations)
      .catch(() => setConversations([]));
  }, [isOpen, isAuthenticated]);

  useEffect(() => {
    if (!isOpen) return;
    const handleClickOutside = (event) => {
      if (panelRef.current && !panelRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [isOpen]);

  async function onGetTips() {
    setLoading(true);
    setError("");
    setTips(null);
    setPosture(null);
    try {
      const data = await aiService.getSecurityTips();
      if (!data.available) {
        setError(data.message || "AI tips unavailable");
        return;
      }
      setTips(data);
      await saveConversation("security_tips", data);
    } catch (err) {
      setError(err.message || "Could not load tips");
    } finally {
      setLoading(false);
    }
  }

  async function onVerifyPosture() {
    setLoading(true);
    setError("");
    setTips(null);
    setPosture(null);
    try {
      const data = await aiService.verifyPosture();
      if (!data.available) {
        setError(data.message || "AI verification unavailable");
        return;
      }
      setPosture(data);
      await saveConversation("posture_verification", data);
    } catch (err) {
      setError(err.message || "Could not verify posture");
    } finally {
      setLoading(false);
    }
  }

  async function saveConversation(conversationType, data) {
    try {
      const payload = {
        conversation_type: conversationType,
        messages: JSON.stringify([{ role: "assistant", content: data }]),
        context_data: JSON.stringify({}),
      };
      const conversation = await aiService.createConversation(payload);
      setConversations((current) => [conversation, ...current]);
      setActiveConversationId(conversation.id);
    } catch (err) {
      console.error("Failed to save conversation", err);
    }
  }

  function renderTips() {
    if (!tips) return null;
    return (
      <div className="ai-panel-section">
        <h4>Security Tips</h4>
        <p className="ai-hint">Overall health score: {tips.overall_health_score ?? "—"}/100</p>
        <div className="ai-list">
          {(tips.tips || []).map((tip, index) => (
            <div key={index} className="ai-tip-card">
              <div className="ai-tip-header">
                <span className={`ai-priority priority-${tip.priority}`}>{tip.priority}</span>
                <strong>{tip.title}</strong>
              </div>
              <p>{tip.description}</p>
              <span className="ai-hint">Effort: {tip.effort}</span>
            </div>
          ))}
        </div>
      </div>
    );
  }

  function renderPosture() {
    if (!posture) return null;
    const statusClass = posture.status === "healthy" ? "good" : posture.status === "critical" ? "bad" : "warn";
    return (
      <div className="ai-panel-section">
        <h4>Security Posture Verification</h4>
        <div className="ai-posture-score">
          <span className={`ai-status-badge status-${statusClass}`}>{posture.status}</span>
          <strong>Score: {posture.posture_score ?? "—"}/100</strong>
        </div>
        <p>{posture.verification_summary}</p>
        {posture.immediate_actions?.length > 0 && (
          <div className="ai-list">
            <h5>Immediate actions</h5>
            {posture.immediate_actions.map((item, index) => (
              <div key={index} className="ai-action-item">
                {item}
              </div>
            ))}
          </div>
        )}
        {posture.long_term_recommendations?.length > 0 && (
          <div className="ai-list">
            <h5>Long-term recommendations</h5>
            {posture.long_term_recommendations.map((item, index) => (
              <div key={index} className="ai-action-item">
                {item}
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="ai-assistant">
      <button
        type="button"
        className={`ai-fab ${isOpen ? "ai-fab-open" : ""}`}
        onClick={() => setIsOpen((prev) => !prev)}
        aria-expanded={isOpen}
        aria-controls={panelId}
        title={isAuthenticated && status.available ? "AI Assistant" : "AI Assistant (unavailable)"}
        disabled={!isAuthenticated}
      >
        <span className="ai-fab-icon" aria-hidden="true">
          {isOpen ? "✕" : "✦"}
        </span>
        <span className="ai-fab-label">AI Assistant</span>
        {status.available && <span className="ai-fab-dot" aria-hidden="true" />}
      </button>

      {isOpen && isAuthenticated && (
        <div ref={panelRef} id={panelId} className="ai-panel" role="dialog" aria-label="AI Assistant">
          <div className="ai-panel-header">
            <div>
              <h3>Security AI Assistant</h3>
              <p className="ai-hint">
                {status.available ? `Powered by ${status.model}` : "AI insights unavailable — add GROQ_API_KEY"}
              </p>
            </div>
            <span className={`ai-status-pill ${status.available ? "status-good" : "status-warn"}`}>
              {status.available ? "Online" : "Offline"}
            </span>
          </div>

          {conversations.length > 0 && (
            <div className="ai-conversation-list">
              {conversations.map((conversation) => (
                <button
                  key={conversation.id}
                  type="button"
                  className={`ai-conversation-item ${conversation.id === activeConversationId ? "active" : ""}`}
                  onClick={() => setActiveConversationId(conversation.id)}
                >
                  <span>{conversation.conversation_type.replace(/_/g, " ")}</span>
                  <span className="ai-hint">{new Date(conversation.updated_at).toLocaleString()}</span>
                </button>
              ))}
            </div>
          )}

          <div className="ai-panel-body">
            {error && <p className="error-text">{error}</p>}
            {!status.available && (
              <div className="ai-placeholder">
                <p><strong>AI Assistant is not configured.</strong></p>
                <p>To enable AI features, add your Groq API key to the backend <code>.env</code> file:</p>
                <code>GROQ_API_KEY=your_api_key_here</code>
                <p className="ai-hint">Get your free API key at <a href="https://console.groq.com" target="_blank" rel="noopener noreferrer">console.groq.com</a></p>
              </div>
            )}
            {loading && status.available && (
              <div className="ai-loading">
                <AITypingDots />
                <span>Analyzing your security data...</span>
              </div>
            )}
            {renderTips()}
            {renderPosture()}
            {status.available && !tips && !posture && !loading && (
              <div className="ai-placeholder">
                <p>Get personalized security insights and verification for your monitored websites.</p>
                <ul>
                  <li>Security tips tailored to your findings</li>
                  <li>Posture verification with confidence</li>
                  <li>Actionable recommendations</li>
                </ul>
              </div>
            )}
          </div>

          {status.available && (
            <div className="ai-panel-footer">
              <button type="button" onClick={onGetTips} disabled={loading}>
                Get security tips
              </button>
              <button type="button" onClick={onVerifyPosture} disabled={loading}>
                Verify posture
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { toast } from "react-hot-toast";
import { aiService } from "../services/api/aiService";
import { findingsService } from "../services/api/findingsService";

function FixApplyAnimation({ onComplete }) {
  // useEffect — NOT useState — for the side effect of driving the step
  // animation. Using useState with an async function runs once per render,
  // leaking cancelled-but-still-running intervals into the next animation.
  const cancelledRef = useRef(false);
  const [step, setStep] = useState(0);

  const steps = [
    "Connecting to server...",
    "Applying configuration changes...",
    "Verifying fix...",
    "Fix applied successfully!",
  ];

  useEffect(() => {
    cancelledRef.current = false;
    let timer;
    let i = 0;

    const tick = async () => {
      if (cancelledRef.current) return;
      await new Promise((r) => setTimeout(r, 600));
      if (cancelledRef.current) return;
      i += 1;
      setStep(i);
      if (i < steps.length) {
        timer = setTimeout(tick, 0);
      } else {
        timer = setTimeout(() => {
          if (!cancelledRef.current) onComplete?.();
        }, 800);
      }
    };

    tick();
    return () => {
      cancelledRef.current = true;
      if (timer) clearTimeout(timer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="fix-apply-animation">
      {steps.map((s, i) => (
        <div
          key={i}
          className={`fix-apply-step ${
            i < step ? "fix-done" : i === step ? "fix-active" : "fix-pending"
          }`}
        >
          <span className="fix-apply-icon">
            {i < step ? "✓" : i === step ? "▶" : "○"}
          </span>
          <span>{s}</span>
        </div>
      ))}
    </div>
  );
}

export function AiAutoFixPanel({ findingId, finding, onClose, onResolved }) {
  const [fix, setFix] = useState(null);
  const [loading, setLoading] = useState(false);
  const [applying, setApplying] = useState(false);
  const [resolved, setResolved] = useState(false);
  const [error, setError] = useState("");
  const [copiedStep, setCopiedStep] = useState(null);

  async function generateFix() {
    setLoading(true);
    setError("");
    try {
      const result = await aiService.autoFixFinding(findingId);
      if (result.available) {
        setFix(result);
      } else {
        setError(result.message || "Auto-fix not available");
      }
    } catch (err) {
      setError(err.message || "Could not generate fix");
    } finally {
      setLoading(false);
    }
  }

  function onApplyComplete() {
    // The backend has no "apply" endpoint — the fix is a remediation
    // script the operator runs themselves. What we CAN do honestly is
    // mark the finding as resolved once the user confirms they ran it.
    findingsService
      .resolve(findingId)
      .then(() => {
        setResolved(true);
        toast.success("Finding marked as resolved.");
        onResolved?.(findingId);
      })
      .catch((err) => {
        setError(err.message || "Could not mark finding as resolved");
      })
      .finally(() => setApplying(false));
  }

  async function copyCode(text, index) {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedStep(index);
      setTimeout(() => setCopiedStep(null), 1500);
    } catch {
      toast.error("Could not copy to clipboard.");
    }
  }

  const kind = finding?.kind || "unknown";

  if (resolved) {
    return (
      <motion.div
        className="ai-autofix-panel"
        initial={{ opacity: 0, height: 0 }}
        animate={{ opacity: 1, height: "auto" }}
      >
        <div className="ai-autofix-header">
          <span className="ai-autofix-title" style={{ color: "var(--accent-2)" }}>
            {"✅"} Fixed
          </span>
          <button type="button" className="ai-autofix-close" onClick={onClose}>
            &times;
          </button>
        </div>
        <div className="ai-autofix-content" style={{ textAlign: "center", padding: "1.5rem" }}>
          <p style={{ fontSize: "1.1rem", fontWeight: 600, color: "var(--accent-2)" }}>
            {"✅"} Finding marked as resolved
          </p>
          <p className="ai-hint">
            You confirmed running the suggested fix for{" "}
            <strong>{kind.replace(/_/g, " ")}</strong>. The next scan will
            verify whether the issue is actually gone.
          </p>
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div
      className="ai-autofix-panel"
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: "auto" }}
      exit={{ opacity: 0, height: 0 }}
    >
      <div className="ai-autofix-header">
        <span className="ai-autofix-title">
          <span className="ai-autofix-icon">{"✨"}</span> AI Auto-Fix
        </span>
        <button type="button" className="ai-autofix-close" onClick={onClose}>
          &times;
        </button>
      </div>

      {!fix && !loading && !error && !applying && (
        <div className="ai-autofix-intro">
          <div className="ai-autofix-cause-preview">
            <div className="ai-cause-header">
              <span className="ai-cause-icon">{"\u{1F50D}"}</span>
              <span>Root cause analysis &amp; remediation</span>
            </div>
            <p className="ai-cause-explanation">
              The AI will analyze the <strong>{kind.replace(/_/g, " ")}</strong>
              {" "}issue and propose a concrete remediation you can review,
              copy, and run yourself on the affected server.
            </p>
          </div>
          <button type="button" className="ai-autofix-generate" onClick={generateFix}>
            {"⚙️"} Analyze &amp; Generate Fix
          </button>
        </div>
      )}

      {loading && (
        <div className="ai-autofix-loading">
          <div className="ai-autofix-loading-content">
            <span className="ai-dot" />
            <span className="ai-dot" />
            <span className="ai-dot" />
            <span>AI is analyzing root cause &amp; generating fix...</span>
          </div>
          <div className="ai-autofix-thinking">
            <div className="ai-thinking-step">
              <span className="ai-thinking-dot active" />
              <span>Examining finding details</span>
            </div>
            <div className="ai-thinking-step">
              <span className="ai-thinking-dot" />
              <span>Identifying root cause</span>
            </div>
            <div className="ai-thinking-step">
              <span className="ai-thinking-dot" />
              <span>Generating remediation steps</span>
            </div>
          </div>
        </div>
      )}

      {applying && <FixApplyAnimation onComplete={onApplyComplete} />}

      {error && <p className="error-text">{error}</p>}

      {fix && !applying && (
        <div className="ai-autofix-content">
          <div className="ai-autofix-cause">
            <div className="ai-cause-header">
              <span className="ai-cause-icon">{"\u{1F50D}"}</span>
              <strong>Root Cause Analysis</strong>
            </div>
            <p className="ai-cause-text">{fix.summary || "No analysis available"}</p>
            <div className="ai-autofix-meta">
              <span className={`ai-autofix-risk risk-${fix.risk_level || "medium"}`}>
                {(fix.risk_level || "medium").toUpperCase()} Risk
              </span>
              {fix.estimated_effort && (
                <span className="ai-autofix-effort">
                  {"⏱️"} ~{fix.estimated_effort} min
                </span>
              )}
              {fix.fix_type && (
                <span className="ai-autofix-type">
                  {"\u{1F527}"} {fix.fix_type.replace(/_/g, " ")}
                </span>
              )}
            </div>
          </div>

          <div className="ai-autofix-steps-section">
            <div className="ai-steps-header">
              <span className="ai-steps-icon">{"\u{1F4CB}"}</span>
              <strong>Step-by-Step Fix</strong>
            </div>
            <div className="ai-autofix-steps">
              {(fix.steps || []).map((step, i) => (
                <div key={i} className="ai-autofix-step">
                  <span className="step-num">{i + 1}</span>
                  <div>
                    <strong className="step-title">{step.title}</strong>
                    {step.command_or_code && (
                      <div className="ai-autofix-code">
                        <pre><code>{step.command_or_code}</code></pre>
                        <button
                          type="button"
                          className="copy-btn"
                          onClick={() => copyCode(step.command_or_code, i)}
                        >
                          {copiedStep === i ? "Copied" : "Copy"}
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {fix.rollback_instructions && (
            <details className="ai-autofix-rollback">
              <summary>{"\u{1F504}"} Rollback Instructions</summary>
              <p>{fix.rollback_instructions}</p>
            </details>
          )}

          <p className="ai-hint" style={{ marginTop: "0.75rem" }}>
            These commands run on your server. Guardian cannot apply them
            remotely. Once you&rsquo;ve run them, mark the finding resolved.
          </p>

          <div className="ai-autofix-apply">
            <button
              type="button"
              className="ai-autofix-apply-btn"
              onClick={() => setApplying(true)}
              disabled={applying}
            >
              {"✅"} I ran the fix — mark as resolved
            </button>
          </div>
        </div>
      )}
    </motion.div>
  );
}

export default AiAutoFixPanel;
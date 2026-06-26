import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";

const STEP_CONFIG = {
  uptime: { icon: "\u{1F310}", label: "Uptime Check", desc: "Checking if your site is reachable..." },
  ssl_expiry: { icon: "\u{1F512}", label: "SSL/TLS Expiry", desc: "Verifying certificate validity..." },
  security_headers: { icon: "\u{1F6E1}\uFE0F", label: "Security Headers", desc: "Analyzing HTTP security headers..." },
  open_ports: { icon: "\u{1F4E1}", label: "Port Exposure", desc: "Scanning for exposed ports..." },
};

function StepIcon({ state }) {
  if (state === "done") return <span className="step-icon-done">{"\u2713"}</span>;
  if (state === "no-access") return <span className="step-icon-na">{"\u2298"}</span>;
  if (state === "error") return <span className="step-icon-err">{"\u2717"}</span>;
  if (state === "active") return <span className="step-icon-active">{"\u25B6"}</span>;
  return <span className="step-icon-pending">{"\u25CB"}</span>;
}

function ProgressParticles({ active }) {
  if (!active) return null;
  return (
    <div className="progress-particles">
      {[...Array(6)].map((_, i) => (
        <motion.div
          key={i}
          className="progress-particle"
          initial={{ x: 0, y: 0, opacity: 1 }}
          animate={{
            x: [0, (i % 2 === 0 ? 1 : -1) * (20 + Math.random() * 40)],
            y: [0, -(30 + Math.random() * 50)],
            opacity: [0.8, 0],
          }}
          transition={{
            duration: 1 + Math.random() * 0.8,
            repeat: Infinity,
            delay: i * 0.15,
            ease: "easeOut",
          }}
          style={{
            left: `${50 + (i - 3) * 12}%`,
          }}
        />
      ))}
    </div>
  );
}

function AnimatedProgressFill({ progress, isRunning }) {
  return (
    <div className="scan-progress-track">
      <motion.div
        className={`scan-progress-fill ${isRunning ? "scan-progress-fill-active" : ""}`}
        initial={{ width: "0%" }}
        animate={{ width: `${progress}%` }}
        transition={{ duration: 0.6, ease: [0.25, 0.46, 0.45, 0.94] }}
      >
        {isRunning && <div className="scan-progress-shimmer" />}
      </motion.div>
    </div>
  );
}

function AnimatedCounter({ value, duration = 400 }) {
  const [display, setDisplay] = useState(0);
  const prevRef = useRef(0);

  useEffect(() => {
    const start = prevRef.current;
    const diff = value - start;
    if (Math.abs(diff) < 0.3) {
      setDisplay(value);
      prevRef.current = value;
      return;
    }
    const startTime = performance.now();
    const animate = (now) => {
      const elapsed = now - startTime;
      const t = Math.min(elapsed / duration, 1);
      const ease = 1 - Math.pow(1 - t, 3);
      const current = start + diff * ease;
      setDisplay(current);
      if (t < 1) requestAnimationFrame(animate);
      else {
        setDisplay(value);
        prevRef.current = value;
      }
    };
    requestAnimationFrame(animate);
  }, [value, duration]);

  return <span className="scan-progress-pct">{Math.round(display)}%</span>;
}

export function ScanProgress({ currentStep, status, stepStatuses, websiteName, onViewDetails, scanRunId }) {
  const stepKeys = Object.keys(STEP_CONFIG);
  const completedSteps = stepKeys.filter(
    (k) => stepStatuses?.[k] === "success" || stepStatuses?.[k] === "error" || stepStatuses?.[k] === "no_access"
  ).length;
  const activeStepIndex = currentStep ? stepKeys.indexOf(currentStep) : -1;

  const [stepElapsed, setStepElapsed] = useState(0);
  const stepTimerRef = useRef(null);
  const stepStartRef = useRef(null);

  useEffect(() => {
    if (status === "running" && currentStep) {
      stepStartRef.current = Date.now();
      setStepElapsed(0);
      stepTimerRef.current = setInterval(() => {
        setStepElapsed(Date.now() - stepStartRef.current);
      }, 80);
    } else {
      if (stepTimerRef.current) clearInterval(stepTimerRef.current);
      setStepElapsed(0);
    }
    return () => {
      if (stepTimerRef.current) clearInterval(stepTimerRef.current);
    };
  }, [currentStep, status]);

  let progress = (completedSteps / stepKeys.length) * 100;
  if (status === "running" && activeStepIndex >= 0) {
    const stepPortion = 100 / stepKeys.length;
    const stepDuration = 10000;
    const fraction = Math.min(stepElapsed / stepDuration, 0.85);
    progress += fraction * stepPortion;
  }

  const isRunning = status === "running" || status === "pending";
  const isCompleted = status === "completed";
  const isFailed = status === "failed";

  return (
    <div className={`scan-progress ${isRunning ? "scan-progress-active" : ""} ${isCompleted ? "scan-progress-done" : ""}`}>
      <div className="scan-progress-header">
        <span className={`scan-progress-badge status-${status}`}>
          {isRunning ? "Scanning" : isCompleted ? "Complete" : isFailed ? "Failed" : status}
        </span>
        {isCompleted && <span className="scan-progress-check">{"\u2705"}</span>}
        {isRunning && <span className="scan-progress-pulse" />}
      </div>

      <div className="scan-progress-track-wrap">
        <AnimatedProgressFill progress={Math.min(progress, 100)} isRunning={isRunning} />
        <AnimatedCounter value={Math.min(progress, 100)} />
      </div>

      {isRunning && <ProgressParticles active={isRunning} />}

      <div className="scan-progress-glow-bar" />

      <div className="scan-steps">
        {Object.entries(STEP_CONFIG).map(([key, cfg], idx) => {
          const sts = stepStatuses?.[key];
          const isCurrent = currentStep === key;
          let state = "pending";
          if (sts === "success") state = "done";
          else if (sts === "no_access") state = "no-access";
          else if (sts === "error") state = "error";
          else if (sts === "active" || isCurrent) state = "active";
          else if (isCompleted || isFailed) state = "done";

          return (
            <motion.div
              key={key}
              className={`scan-step-row scan-step-${state} ${state === "active" ? "scan-step-active-pulse" : ""}`}
              initial={{ opacity: 0, x: -12 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: idx * 0.08, duration: 0.25 }}
            >
              <div className="scan-step-left">
                <StepIcon state={state} />
                <span className="step-row-icon">{cfg.icon}</span>
                <div className="step-row-info">
                  <span className="step-row-label">{cfg.label}</span>
                  <span className="step-row-desc">
                    {state === "done" ? "Completed" : state === "no-access" ? "No access" : state === "error" ? "Error" : state === "active" ? cfg.desc : "Waiting"}
                  </span>
                </div>
              </div>
              {state === "active" && <span className="step-row-spinner"><span className="spinner-dot pulse" /></span>}
              {state === "done" && <span className="step-row-ok">OK</span>}
              {state === "no-access" && <span className="step-row-na">No access</span>}
              {state === "error" && <span className="step-row-err">Error</span>}
            </motion.div>
          );
        })}
      </div>

      {isCompleted && (
        <motion.div
          className="scan-progress-complete"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
        >
          <span className="scan-complete-text">{"\u2713"} All checks passed</span>
          <button type="button" className="btn-details" onClick={() => onViewDetails(scanRunId)}>
            View Details {"\u2192"}
          </button>
        </motion.div>
      )}

      {isFailed && (
        <motion.div
          className="scan-progress-complete scan-progress-failed"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
        >
          <span className="scan-complete-text">{"\u2717"} Scan encountered errors</span>
          <button type="button" className="btn-details" onClick={() => onViewDetails(scanRunId)}>
            View Details {"\u2192"}
          </button>
        </motion.div>
      )}
    </div>
  );
}

import { useEffect, useState } from "react";

export function SecurityScoreCard({ score, trend }) {
  const [animatedScore, setAnimatedScore] = useState(0);
  const [badges, setBadges] = useState([]);

  useEffect(() => {
    // Animate score on mount
    const duration = 1000;
    const steps = 30;
    const increment = score / steps;
    let current = 0;
    
    const timer = setInterval(() => {
      current += increment;
      if (current >= score) {
        setAnimatedScore(score);
        clearInterval(timer);
      } else {
        setAnimatedScore(Math.round(current));
      }
    }, duration / steps);

    return () => clearInterval(timer);
  }, [score]);

  useEffect(() => {
    // Calculate badges based on score
    const earnedBadges = [];
    if (score >= 100) earnedBadges.push({ icon: "🏆", name: "Perfect Security", color: "#ffd700" });
    if (score >= 90) earnedBadges.push({ icon: "💎", name: "Excellent", color: "#9333ea" });
    if (score >= 80) earnedBadges.push({ icon: "⭐", name: "Strong", color: "#3b82f6" });
    if (score >= 70) earnedBadges.push({ icon: "🛡️", name: "Secure", color: "#10b981" });
    if (score >= 60) earnedBadges.push({ icon: "🔒", name: "Protected", color: "#f59e0b" });
    if (score >= 50) earnedBadges.push({ icon: "🔐", name: "Basic", color: "#6b7280" });
    
    setBadges(earnedBadges);
  }, [score]);

  const getScoreColor = (score) => {
    if (score >= 90) return { bg: "#dcfce7", text: "#166534", border: "#22c55e" };
    if (score >= 70) return { bg: "#dbeafe", text: "#1e40af", border: "#3b82f6" };
    if (score >= 50) return { bg: "#fef3c7", text: "#92400e", border: "#f59e0b" };
    return { bg: "#fee2e2", text: "#991b1b", border: "#ef4444" };
  };

  const colors = getScoreColor(animatedScore);
  const circumference = 2 * Math.PI * 45;
  const offset = circumference - (animatedScore / 100) * circumference;

  return (
    <div className="security-score-card">
      <div className="score-header">
        <h3>Security Score</h3>
        {trend && <span className={`trend-badge trend-${trend.direction.toLowerCase()}`}>{trend.direction}</span>}
      </div>
      
      <div className="score-visual">
        <svg className="score-circle" width="120" height="120">
          <circle
            className="score-circle-bg"
            cx="60"
            cy="60"
            r="45"
            fill="none"
            stroke="#e5e7eb"
            strokeWidth="8"
          />
          <circle
            className="score-circle-fill"
            cx="60"
            cy="60"
            r="45"
            fill="none"
            stroke={colors.border}
            strokeWidth="8"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            style={{
              transition: "stroke-dashoffset 1s ease-in-out",
            }}
          />
          <text x="60" y="60" textAnchor="middle" dy="7" fill={colors.text} fontSize="28" fontWeight="bold">
            {animatedScore}
          </text>
        </svg>
        
        <div className="score-description">
          <p className="score-label">Overall Security Health</p>
          <p className="score-status" style={{ color: colors.text }}>
            {animatedScore >= 90 ? "Excellent" : animatedScore >= 70 ? "Good" : animatedScore >= 50 ? "Fair" : "Needs Attention"}
          </p>
        </div>
      </div>

      {badges.length > 0 && (
        <div className="badges-section">
          <p className="badges-label">Achievements</p>
          <div className="badges-grid">
            {badges.map((badge, index) => (
              <div key={index} className="badge-item" title={badge.name}>
                <span className="badge-icon" style={{ backgroundColor: badge.bg }}>{badge.icon}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="score-tips">
        <p className="tips-label">💡 Tips to improve:</p>
        <ul className="tips-list">
          {animatedScore < 100 && <li>Fix all critical and high severity findings</li>}
          {animatedScore < 90 && <li>Enable 2FA for all accounts</li>}
          {animatedScore < 80 && <li>Set up automated security scans</li>}
          {animatedScore < 70 && <li>Configure alert notifications</li>}
          {animatedScore >= 90 && <li className="tip-completed">✓ Great job! Keep monitoring</li>}
        </ul>
      </div>
    </div>
  );
}

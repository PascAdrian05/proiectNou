import { useState } from "react";

export function QuickFixes({ findings }) {
  const [expandedFix, setExpandedFix] = useState(null);

  const getQuickFixes = () => {
    const fixes = [];
    
    findings.forEach(finding => {
      const kind = finding.kind?.toLowerCase() || "";
      const title = finding.title?.toLowerCase() || "";
      
      // SSL Certificate issues
      if (kind.includes("ssl") || title.includes("ssl") || title.includes("certificate")) {
        fixes.push({
          id: finding.id,
          title: "Fix SSL Certificate",
          description: "Automatically renew or configure SSL certificate",
          icon: "🔒",
          difficulty: "easy",
          steps: [
            "Check SSL certificate expiration date",
            "Enable auto-renewal in your hosting provider",
            "Use Let's Encrypt for free SSL certificates",
            "Update your web server configuration"
          ],
          codeSnippet: `# Enable SSL with Let's Encrypt
sudo certbot --nginx -d yourdomain.com
# Enable auto-renewal
sudo certbot renew --dry-run`
        });
      }
      
      // Security headers
      if (kind.includes("header") || title.includes("header")) {
        fixes.push({
          id: finding.id + "-headers",
          title: "Add Security Headers",
          description: "Add essential security headers to your web server",
          icon: "🛡️",
          difficulty: "easy",
          steps: [
            "Add Content-Security-Policy header",
            "Add X-Frame-Options header",
            "Add X-Content-Type-Options header",
            "Add Strict-Transport-Security header"
          ],
          codeSnippet: `# Add to nginx configuration
add_header Content-Security-Policy "default-src 'self'";
add_header X-Frame-Options "SAMEORIGIN";
add_header X-Content-Type-Options "nosniff";
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";`
        });
      }
      
      // HTTPS issues
      if (title.includes("https") || title.includes("http") || kind.includes("https")) {
        fixes.push({
          id: finding.id + "-https",
          title: "Enable HTTPS",
          description: "Force HTTPS redirect for all traffic",
          icon: "🔐",
          difficulty: "medium",
          steps: [
            "Install SSL certificate",
            "Configure web server for HTTPS",
            "Set up HTTP to HTTPS redirect",
            "Update all internal links to use HTTPS"
          ],
          codeSnippet: `# Force HTTPS redirect in nginx
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}`
        });
      }
      
      // Missing security features
      if (title.includes("missing") || title.includes("not configured")) {
        fixes.push({
          id: finding.id + "-missing",
          title: "Configure Security Feature",
          description: "Enable missing security configuration",
          icon: "⚙️",
          difficulty: "medium",
          steps: [
            "Identify the missing security feature",
            "Review documentation for proper configuration",
            "Apply the configuration changes",
            "Test the security feature"
          ],
          codeSnippet: `# Example: Enable rate limiting
# In nginx configuration
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;

location /api/ {
    limit_req zone=api burst=20 nodelay;
}`
        });
      }
    });
    
    return fixes.slice(0, 5); // Limit to top 5 fixes
  };

  const quickFixes = getQuickFixes();

  if (quickFixes.length === 0) {
    return null;
  }

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
  };

  return (
    <div className="quick-fixes-section">
      <h3>🔧 Quick Fixes Available</h3>
      <p className="hint">Automated solutions for common security issues</p>
      
      <div className="quick-fixes-list">
        {quickFixes.map((fix, index) => (
          <div key={index} className="quick-fix-item">
            <div 
              className="quick-fix-header" 
              onClick={() => setExpandedFix(expandedFix === index ? null : index)}
            >
              <div className="quick-fix-info">
                <span className="quick-fix-icon">{fix.icon}</span>
                <div>
                  <h4>{fix.title}</h4>
                  <p className="quick-fix-description">{fix.description}</p>
                </div>
              </div>
              <div className="quick-fix-meta">
                <span className={`difficulty-badge difficulty-${fix.difficulty}`}>
                  {fix.difficulty}
                </span>
                <button className="expand-btn">
                  {expandedFix === index ? "▼" : "▶"}
                </button>
              </div>
            </div>
            
            {expandedFix === index && (
              <div className="quick-fix-details">
                <div className="quick-fix-steps">
                  <h5>Steps to fix:</h5>
                  <ol>
                    {fix.steps.map((step, stepIndex) => (
                      <li key={stepIndex}>{step}</li>
                    ))}
                  </ol>
                </div>
                
                {fix.codeSnippet && (
                  <div className="quick-fix-code">
                    <div className="code-header">
                      <span>Code snippet</span>
                      <button 
                        className="copy-btn"
                        onClick={() => copyToClipboard(fix.codeSnippet)}
                      >
                        Copy
                      </button>
                    </div>
                    <pre><code>{fix.codeSnippet}</code></pre>
                  </div>
                )}
                
                <div className="quick-fix-actions">
                  <button className="primary-btn" onClick={() => {
                    // In a real implementation, this would trigger the fix
                    alert(`This would automatically apply the fix for: ${fix.title}`);
                  }}>
                    Apply Fix
                  </button>
                  <button className="secondary-btn" onClick={() => setExpandedFix(null)}>
                    Close
                  </button>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

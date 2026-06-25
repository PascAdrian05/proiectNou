export function SecurityPage() {
  return (
    <section className="page-card">
      <div className="list-header">
        <div>
          <h2>Security & Trust</h2>
          <p className="hint">Your security is our top priority. Learn how we protect your data.</p>
        </div>
      </div>

      <div className="security-content">
        <article className="security-section">
          <h3>🔒 Data Security</h3>
          <p>We implement industry-standard security measures to protect your information:</p>
          <ul>
            <li><strong>Encryption:</strong> All data is encrypted at rest using AES-256 encryption</li>
            <li><strong>Secure Transmission:</strong> TLS 1.3 for all data in transit</li>
            <li><strong>Database Security:</strong> PostgreSQL 16 with regular security updates</li>
            <li><strong>Password Hashing:</strong> Bcrypt with salt for secure password storage</li>
            <li><strong>Two-Factor Authentication:</strong> Optional TOTP-based 2FA for enhanced account security</li>
          </ul>
        </article>

        <article className="security-section">
          <h3>👤 Account Security</h3>
          <p>Protect your account with these security features:</p>
          <ul>
            <li><strong>Rate Limiting:</strong> Protection against brute-force attacks</li>
            <li><strong>Account Lockout:</strong> Automatic temporary lock after failed login attempts</li>
            <li><strong>Session Management:</strong> Secure token-based authentication with refresh tokens</li>
            <li><strong>Audit Logging:</strong> All critical actions are logged for security monitoring</li>
            <li><strong>IP Tracking:</strong> Login attempts are tracked for suspicious activity detection</li>
          </ul>
        </article>

        <article className="security-section">
          <h3>🤖 AI Privacy</h3>
          <p>Our AI assistant is designed with privacy in mind:</p>
          <ul>
            <li><strong>Data Usage:</strong> Only anonymized security findings are shared with AI</li>
            <li><strong>No Personal Data:</strong> Your personal information is never sent to AI services</li>
            <li><strong>Secure API:</strong> All AI communications use encrypted connections</li>
            <li><strong>Conversation Storage:</strong> AI conversations are stored securely in our database</li>
            <li><strong>Transparent:</strong> You can review and delete your AI conversations at any time</li>
          </ul>
        </article>

        <article className="security-section">
          <h3>📋 Privacy Policy</h3>
          <h4>Data Collection</h4>
          <p>We collect only the data necessary to provide our service:</p>
          <ul>
            <li><strong>Account Information:</strong> Email, name (for tenant identification)</li>
            <li><strong>Website Data:</strong> Domains you monitor and their security scan results</li>
            <li><strong>Usage Data:</strong> Scan history, alerts, and security findings</li>
            <li><strong>Technical Data:</strong> IP address, browser type (for security purposes)</li>
          </ul>

          <h4>Data Usage</h4>
          <p>Your data is used to:</p>
          <ul>
            <li>Provide security monitoring and scanning services</li>
            <li>Generate security reports and insights</li>
            <li>Send security alerts and notifications</li>
            <li>Improve our service quality and security</li>
            <li>Prevent fraud and abuse</li>
          </ul>

          <h4>Data Retention</h4>
          <ul>
            <li><strong>Scan Results:</strong> Retained for 90 days (free tier), 1 year (paid tiers)</li>
            <li><strong>Account Data:</strong> Retained until account deletion</li>
            <li><strong>Audit Logs:</strong> Retained for 1 year for security purposes</li>
            <li><strong>AI Conversations:</strong> Retained until you delete them</li>
          </ul>

          <h4>Your Rights</h4>
          <ul>
            <li><strong>Access:</strong> Request a copy of your data</li>
            <li><strong>Deletion:</strong> Request deletion of your account and data</li>
            <li><strong>Export:</strong> Export your security reports and findings</li>
            <li><strong>Opt-out:</strong> Disable AI features at any time</li>
          </ul>
        </article>

        <article className="security-section">
          <h3>🛡️ Incident Response</h3>
          <p>In the unlikely event of a security incident:</p>
          <ul>
            <li><strong>Immediate Notification:</strong> Affected users will be notified within 72 hours</li>
            <li><strong>Transparent Communication:</strong> We will provide clear information about what happened</li>
            <li><strong>Rapid Remediation:</strong> Our team will work quickly to address and fix the issue</li>
            <li><strong>Post-Mortem:</strong> We will conduct a thorough review and implement improvements</li>
            <li><strong>Regulatory Compliance:</strong> We will comply with all applicable data breach notification laws</li>
          </ul>
        </article>

        <article className="security-section">
          <h3>🏢 Compliance & Certifications</h3>
          <p>We are committed to maintaining high security standards:</p>
          <ul>
            <li><strong>GDPR Ready:</strong> Our privacy practices align with GDPR requirements</li>
            <li><strong>Security Best Practices:</strong> We follow OWASP security guidelines</li>
            <li><strong>Regular Updates:</strong> All dependencies are regularly updated for security patches</li>
            <li><strong>Penetration Testing:</strong> Regular security assessments (roadmap item)</li>
            <li><strong>Third-Party Audits:</strong> Planned for future certification</li>
          </ul>
        </article>

        <article className="security-section">
          <h3>📞 Contact & Questions</h3>
          <p>Have security questions or concerns?</p>
          <ul>
            <li><strong>Security Issues:</strong> Report security vulnerabilities responsibly</li>
            <li><strong>Privacy Questions:</strong> Contact us about data privacy matters</li>
            <li><strong>General Inquiries:</strong> Reach out for any other questions</li>
          </ul>
          <p className="hint">We take all security reports seriously and will respond promptly.</p>
        </article>

        <article className="security-section highlight">
          <h3>✅ Your Security Checklist</h3>
          <p>Follow these best practices to keep your account secure:</p>
          <ul>
            <li>✓ Enable Two-Factor Authentication (2FA)</li>
            <li>✓ Use a strong, unique password</li>
            <li>✓ Review your audit logs regularly</li>
            <li>✓ Keep your browser and software updated</li>
            <li>✓ Be cautious of phishing attempts</li>
            <li>✓ Report suspicious activity immediately</li>
            <li>✓ Use secure networks (avoid public Wi-Fi for sensitive tasks)</li>
          </ul>
        </article>
      </div>
    </section>
  );
}

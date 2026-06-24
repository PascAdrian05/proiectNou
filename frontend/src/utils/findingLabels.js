const HEADER_LABELS = {
  "strict-transport-security": "Strict-Transport-Security (HSTS)",
  "content-security-policy": "Content-Security-Policy (CSP)",
  "x-frame-options": "X-Frame-Options",
  "x-content-type-options": "X-Content-Type-Options",
  "referrer-policy": "Referrer-Policy",
};

export function parseFindingDetails(finding) {
  if (!finding?.details_json) {
    return {};
  }
  try {
    return JSON.parse(finding.details_json);
  } catch {
    return {};
  }
}

export function getHumanTitle(finding) {
  const kind = String(finding?.kind || "").toLowerCase();
  const details = parseFindingDetails(finding);

  if (kind === "uptime") {
    if (!details.reachable) {
      return "Website is unreachable";
    }
    return "Website availability issue";
  }

  if (kind === "ssl_expiry") {
    if (!details.valid) {
      return "SSL certificate is invalid or missing";
    }
    const days = details.days_left ?? 0;
    if (days <= 7) {
      return `SSL certificate expires in ${days} day${days === 1 ? "" : "s"}`;
    }
    return `SSL certificate expires in ${days} days`;
  }

  if (kind === "security_headers") {
    const count = details.missing?.length ?? 0;
    return count === 1 ? "1 security header is missing" : `${count} security headers are missing`;
  }

  if (kind === "open_ports") {
    const ports = details.open_ports || [];
    if (ports.length === 1) {
      return `Port ${ports[0]} is publicly exposed`;
    }
    return `${ports.length} sensitive ports are publicly exposed`;
  }

  return finding?.title || "Security issue detected";
}

export function getHumanSummary(finding) {
  const kind = String(finding?.kind || "").toLowerCase();
  const details = parseFindingDetails(finding);

  if (kind === "uptime") {
    if (!details.reachable) {
      return details.error
        ? `We could not connect to your site: ${details.error}`
        : "Your website did not respond to our health check.";
    }
    return `Site responded with HTTP ${details.status_code} in ${details.latency_ms}ms.`;
  }

  if (kind === "ssl_expiry") {
    if (!details.valid) {
      return details.error || "The TLS certificate could not be validated.";
    }
    return `Certificate expires on ${new Date(details.expires_at).toLocaleDateString()}. Renew before visitors see browser warnings.`;
  }

  if (kind === "security_headers") {
    const missing = (details.missing || []).map((header) => HEADER_LABELS[header] || header);
    return missing.length
      ? `Missing headers: ${missing.join(", ")}. These protect against clickjacking, XSS, and downgrade attacks.`
      : "Some recommended security headers are not configured.";
  }

  if (kind === "open_ports") {
    const ports = details.open_ports || [];
    return ports.length
      ? `Ports ${ports.join(", ")} accept connections from the internet. Database and admin ports should not be public.`
      : "Unexpected open ports were detected.";
  }

  return "Review this finding and apply the recommended fix.";
}

export function getRemediationSteps(finding) {
  const kind = String(finding?.kind || "").toLowerCase();
  const details = parseFindingDetails(finding);

  if (kind === "uptime") {
    return [
      "Check if the site is online in your browser.",
      "Verify DNS records and hosting status with your provider.",
      "Review server logs, firewall rules, and recent deployments.",
      "Run a new scan after the site is back online.",
    ];
  }

  if (kind === "ssl_expiry") {
    const days = details.days_left ?? 0;
    if (days <= 7) {
      return [
        "Log in to your hosting or CDN panel (Cloudflare, cPanel, etc.).",
        "Renew or re-issue the TLS certificate immediately.",
        "Verify the full certificate chain is installed.",
        "Run a new scan to confirm the fix.",
      ];
    }
    return [
      "Schedule certificate renewal with your hosting provider.",
      "Enable auto-renewal if your provider supports it (Let's Encrypt, Cloudflare).",
      "Set a calendar reminder 14 days before expiry.",
    ];
  }

  if (kind === "security_headers") {
    return [
      "Add the missing headers in your reverse proxy (nginx, Apache, Cloudflare).",
      "Start with HSTS and X-Frame-Options — highest impact, lowest effort.",
      "Test in staging before applying to production.",
      "Run a new scan to verify headers are present.",
    ];
  }

  if (kind === "open_ports") {
    return [
      "Identify which service is listening on the exposed port.",
      "Close the port in your cloud firewall / security group.",
      "If access is needed, restrict it to your office IP via VPN.",
      "Run a new scan to confirm the port is no longer public.",
    ];
  }

  return [
    "Review the technical details of this finding.",
    "Apply the recommended hardening change.",
    "Run a new scan to confirm the issue is resolved.",
  ];
}

export function enrichFinding(finding) {
  return {
    ...finding,
    humanTitle: getHumanTitle(finding),
    humanSummary: getHumanSummary(finding),
    remediationSteps: getRemediationSteps(finding),
  };
}

export function parseDomainInput(raw) {
  const trimmed = String(raw || "").trim();
  if (!trimmed) {
    return null;
  }

  const withProtocol = trimmed.includes("://") ? trimmed : `https://${trimmed}`;
  try {
    const url = new URL(withProtocol);
    const domain = url.hostname.replace(/^www\./, "");
    return {
      domain,
      url: `${url.protocol}//${url.hostname}`,
    };
  } catch {
    return null;
  }
}

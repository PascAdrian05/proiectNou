function toCsvRow(columns) {
  return columns
    .map((value) => `"${String(value ?? "").replaceAll('"', '""')}"`)
    .join(",");
}

function downloadTextFile(fileName, mimeType, content) {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = fileName;
  anchor.click();
  URL.revokeObjectURL(url);
}

export function exportReportCsv({ insights, topIssues, alerts }) {
  const rows = [
    toCsvRow(["Section", "Website", "Metric", "Value", "Notes"]),
    ...insights.map((entry) =>
      toCsvRow(["Website Score", entry.website.domain, "Security Score", entry.score, entry.healthLabel])
    ),
    ...topIssues.map((issue) =>
      toCsvRow(["Top Issue", issue.website_id, issue.title, issue.severity, issue.remediationSteps?.[0] || ""])
    ),
    ...alerts.map((alert) =>
      toCsvRow(["Alert", alert.websiteDomain, alert.channel, alert.status, `${alert.findingTitle} | ${alert.relativeTime}`])
    ),
  ];

  downloadTextFile("security-report.csv", "text/csv;charset=utf-8", rows.join("\n"));
}
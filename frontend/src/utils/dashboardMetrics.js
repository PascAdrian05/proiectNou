import { enrichFinding, getHumanTitle } from "./findingLabels";

const severityWeights = {
  critical: 30,
  high: 20,
  medium: 10,
  low: 4,
  info: 1,
};
function getSeverityWeight(severity) {
  return severityWeights[String(severity || "").toLowerCase()] || 6;
}

function parseDate(value) {
  if (!value) {
    return null;
  }
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

export function buildWebsiteInsights(websites, findings, scans) {
  const safeWebsites = Array.isArray(websites) ? websites : [];
  const safeFindings = Array.isArray(findings) ? findings : [];
  const safeScans = Array.isArray(scans) ? scans : [];

  const scanMap = new Map(
    safeScans
      .filter((scan) => scan && typeof scan === 'object' && typeof scan.website_id !== 'undefined')
      .map((scan) => [String(scan.website_id), scan])
  );

  return safeWebsites.map((website) => {
    const websiteId = String(website.id);
    const relatedFindings = safeFindings.filter(
      (finding) =>
        finding &&
        typeof finding === 'object' &&
        typeof finding.website_id !== 'undefined' &&
        String(finding.website_id) === websiteId
    );
    const penalty = relatedFindings.reduce(
      (total, finding) => total + getSeverityWeight(finding.severity),
      0
    );
    const score = Math.max(0, Math.min(100, 100 - penalty));
    const scan = scanMap.get(websiteId) || null;

    return {
      website,
      findings: relatedFindings,
      score,
      healthLabel:
        score >= 85
          ? "Healthy"
          : score >= 65
          ? "Needs attention"
          : "At risk",
      lastScanStatus: scan?.status || website.status || "unknown",
    };
  });
}

export function getTopIssues(findings, limit = 5) {
  const safeFindings = Array.isArray(findings) ? findings : [];
  return [...safeFindings]
    .sort((left, right) => getSeverityWeight(right.severity) - getSeverityWeight(left.severity))
    .slice(0, limit)
    .map((finding) => enrichFinding(finding));
}

export function buildSevenDayTrend(findings) {
  const today = new Date();
  const safeFindings = Array.isArray(findings) ? findings : [];
  const days = Array.from({ length: 7 }, (_, index) => {
    const day = new Date(today);
    day.setHours(0, 0, 0, 0);
    day.setDate(today.getDate() - (6 - index));
    return {
      key: day.toISOString().slice(0, 10),
      label: day.toLocaleDateString("en-GB", { day: "2-digit", month: "short" }),
      count: 0,
    };
  });

  const indexMap = new Map(days.map((day) => [day.key, day]));
  safeFindings.forEach((finding) => {
    const date = parseDate(finding.last_seen_at) || parseDate(finding.first_seen_at);
    if (!date) {
      return;
    }
    const key = date.toISOString().slice(0, 10);
    const entry = indexMap.get(key);
    if (entry) {
      entry.count += 1;
    }
  });

  const firstHalf = days.slice(0, 3).reduce((total, day) => total + day.count, 0);
  const secondHalf = days.slice(3).reduce((total, day) => total + day.count, 0);

  return {
    points: days,
    direction: secondHalf <= firstHalf ? "Improving" : "Worsening",
  };
}

export function buildAlertFeed(alerts, findings, websites, limit = 5) {
  const safeFindings = Array.isArray(findings) ? findings : [];
  const safeWebsites = Array.isArray(websites) ? websites : [];
  const findingMap = new Map(safeFindings.map((finding) => [String(finding.id), finding]));
  const websiteMap = new Map(safeWebsites.map((website) => [String(website.id), website]));
  const safeAlerts = Array.isArray(alerts) ? alerts : [];

  return [...safeAlerts]
    .sort((left, right) => new Date(right.created_at).getTime() - new Date(left.created_at).getTime())
    .slice(0, limit)
    .map((alert) => {
      const finding = findingMap.get(String(alert.finding_id));
      const website = finding ? websiteMap.get(String(finding.website_id)) : null;
      return {
        ...alert,
        websiteDomain: website?.domain || "Unknown website",
        findingTitle: finding ? getHumanTitle(finding) : "Unknown issue",
        relativeTime: formatRelativeTime(alert.sent_at || alert.created_at),
      };
    });
}

export function formatRelativeTime(value) {
  const date = parseDate(value);
  if (!date) {
    return "unknown";
  }
  const deltaMinutes = Math.max(1, Math.round((Date.now() - date.getTime()) / 60000));
  if (deltaMinutes < 60) {
    return `${deltaMinutes} min ago`;
  }
  const deltaHours = Math.round(deltaMinutes / 60);
  if (deltaHours < 24) {
    return `${deltaHours} h ago`;
  }
  const deltaDays = Math.round(deltaHours / 24);
  return `${deltaDays} d ago`;
}
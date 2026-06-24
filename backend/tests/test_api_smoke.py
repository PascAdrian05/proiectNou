import random
import time
from typing import Any

import requests


BASE_URL = "http://localhost:8000/api/v1"


def _register_user() -> dict[str, Any]:
    email = f"pytest_{random.randint(1000, 999999)}@example.com"
    register_response = requests.post(
        f"{BASE_URL}/auth/register",
        json={
            "tenant_name": "Pytest Tenant",
            "email": email,
            "password": "StrongPass123!",
        },
        timeout=15,
    )
    register_response.raise_for_status()
    data = register_response.json()
    data["email"] = email
    return data


def test_health() -> None:
    response = requests.get(f"{BASE_URL}/health", timeout=10)
    response.raise_for_status()
    assert response.json()["status"] == "ok"


def test_auth_register_login_refresh() -> None:
    register_json = _register_user()
    email = register_json.get("email") or "unknown@example.com"
    assert register_json.get("access_token")
    assert register_json.get("refresh_token")

    register_headers = {"Authorization": f"Bearer {register_json['access_token']}"}
    presence_response = requests.get(f"{BASE_URL}/presence/online", headers=register_headers, timeout=15)
    presence_response.raise_for_status()
    assert presence_response.json().get("online_users", 0) >= 1

    login_response = requests.post(
        f"{BASE_URL}/auth/login",
        data={"username": email, "password": "StrongPass123!"},
        timeout=15,
    )
    login_response.raise_for_status()
    login_json = login_response.json()
    assert login_json.get("access_token")
    assert login_json.get("refresh_token")

    refresh_response = requests.post(
        f"{BASE_URL}/auth/refresh",
        json={"refresh_token": login_json["refresh_token"]},
        timeout=15,
    )
    refresh_response.raise_for_status()
    refresh_json = refresh_response.json()
    assert refresh_json.get("access_token")
    assert refresh_json.get("refresh_token")
    assert refresh_json["refresh_token"] != login_json["refresh_token"]

    revoked_response = requests.post(
        f"{BASE_URL}/auth/refresh",
        json={"refresh_token": login_json["refresh_token"]},
        timeout=15,
    )
    assert revoked_response.status_code == 401

    logout_response = requests.post(
        f"{BASE_URL}/auth/logout",
        json={"refresh_token": refresh_json["refresh_token"]},
        timeout=15,
    )
    logout_response.raise_for_status()
    assert logout_response.json().get("status") == "logged_out"

    presence_after_logout = requests.get(f"{BASE_URL}/presence/online", headers=register_headers, timeout=15)
    presence_after_logout.raise_for_status()
    assert presence_after_logout.json().get("online_users", 0) == 0


def test_monitoring_flow_websites_scans_findings_alerts() -> None:
    register_json = _register_user()
    headers = {"Authorization": f"Bearer {register_json['access_token']}"}

    tenant_settings = requests.patch(
        f"{BASE_URL}/tenant/settings",
        json={"alert_email": "alerts@example.com"},
        headers=headers,
        timeout=15,
    )
    tenant_settings.raise_for_status()

    website_response = requests.post(
        f"{BASE_URL}/websites",
        json={"domain": "example.com", "url": "https://example.com", "scan_frequency_minutes": 60},
        headers=headers,
        timeout=15,
    )
    website_response.raise_for_status()
    website_id = website_response.json()["id"]

    enqueue_response = requests.post(
        f"{BASE_URL}/scans/enqueue",
        json={"website_id": website_id},
        headers=headers,
        timeout=15,
    )
    enqueue_response.raise_for_status()
    assert enqueue_response.json().get("task_id")

    time.sleep(8)

    runs_response = requests.get(f"{BASE_URL}/scans/runs", headers=headers, timeout=15)
    runs_response.raise_for_status()
    runs = runs_response.json()
    assert isinstance(runs, list)
    assert len(runs) >= 1

    findings_response = requests.get(f"{BASE_URL}/findings", headers=headers, timeout=15)
    findings_response.raise_for_status()
    findings = findings_response.json()
    assert isinstance(findings, list)

    alerts_response = requests.get(f"{BASE_URL}/alerts", headers=headers, timeout=15)
    alerts_response.raise_for_status()
    alerts = alerts_response.json()
    assert isinstance(alerts, list)

    if alerts:
        delete_alert_response = requests.delete(f"{BASE_URL}/alerts/{alerts[0]['id']}", headers=headers, timeout=15)
        delete_alert_response.raise_for_status()
        assert delete_alert_response.json().get("status") == "deleted"

    if findings:
        delete_finding_response = requests.delete(f"{BASE_URL}/findings/{findings[0]['id']}", headers=headers, timeout=15)
        delete_finding_response.raise_for_status()
        assert delete_finding_response.json().get("status") == "deleted"

    delete_response = requests.delete(f"{BASE_URL}/websites/{website_id}", headers=headers, timeout=15)
    delete_response.raise_for_status()
    assert delete_response.json().get("status") == "deleted"

    websites_response = requests.get(f"{BASE_URL}/websites", headers=headers, timeout=15)
    websites_response.raise_for_status()
    assert all(item["id"] != website_id for item in websites_response.json())


def test_behavior_risk_scoring_and_events() -> None:
    register_json = _register_user()
    headers = {"Authorization": f"Bearer {register_json['access_token']}"}

    score_before = requests.get(f"{BASE_URL}/behavior/score", headers=headers, timeout=15)
    score_before.raise_for_status()
    assert score_before.json().get("risk_score", -1) == 0

    events_response = requests.post(
        f"{BASE_URL}/behavior/events",
        json={
            "events": [
                {"type": "click", "path": "/dashboard"},
                {"type": "click", "path": "/dashboard"},
                {"type": "click", "path": "/dashboard"},
                {"type": "click", "path": "/dashboard"},
                {"type": "click", "path": "/dashboard"},
                {"type": "keydown", "path": "/dashboard"},
                {"type": "keydown", "path": "/dashboard"},
                {"type": "route_change", "path": "/websites"},
                {"type": "route_change", "path": "/scans"},
                {"type": "submit", "path": "/login"},
            ]
        },
        headers=headers,
        timeout=15,
    )
    events_response.raise_for_status()
    assert events_response.json().get("stored_events") == 10

    score_after = requests.get(f"{BASE_URL}/behavior/score", headers=headers, timeout=15)
    score_after.raise_for_status()
    body = score_after.json()
    assert body.get("risk_score", 0) >= 5
    assert body.get("event_count", 0) >= 10


def test_shareable_report_link() -> None:
    register_json = _register_user()
    headers = {"Authorization": f"Bearer {register_json['access_token']}"}

    website_response = requests.post(
        f"{BASE_URL}/websites",
        json={"domain": "example.com", "url": "https://example.com", "scan_frequency_minutes": 60},
        headers=headers,
        timeout=15,
    )
    website_response.raise_for_status()

    share_response = requests.post(f"{BASE_URL}/reports/share", headers=headers, timeout=15)
    share_response.raise_for_status()
    share_data = share_response.json()
    assert share_data.get("share_token")
    assert share_data.get("share_url")

    public_response = requests.get(f"{BASE_URL}/reports/public/{share_data['share_token']}", timeout=15)
    public_response.raise_for_status()
    report_data = public_response.json()
    assert "security_score" in report_data
    assert isinstance(report_data.get("websites"), list)


def test_billing_checkout_without_stripe_config() -> None:
    register_json = _register_user()
    headers = {"Authorization": f"Bearer {register_json['access_token']}"}

    response = requests.post(
        f"{BASE_URL}/billing/stripe/checkout-session",
        json={"plan": "basic"},
        headers=headers,
        timeout=15,
    )
    assert response.status_code == 500


def test_billing_portal_without_stripe_config() -> None:
    register_json = _register_user()
    headers = {"Authorization": f"Bearer {register_json['access_token']}"}

    response = requests.post(
        f"{BASE_URL}/billing/stripe/portal",
        headers=headers,
        timeout=15,
    )
    assert response.status_code == 500


def test_stripe_webhook_without_secret() -> None:
    response = requests.post(f"{BASE_URL}/billing/stripe/webhook", data="{}", timeout=15)
    assert response.status_code == 500

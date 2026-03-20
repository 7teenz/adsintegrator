from tests.helpers import (
    auth_header_for_user,
    create_user,
    seed_audit_data,
    seed_audit_run_with_findings,
    seed_connected_account,
)


def test_run_audit_and_get_latest(client, db_session):
    user = create_user(db_session, "audit@example.com")
    account = seed_connected_account(db_session, user)
    seed_audit_data(db_session, account)
    headers = auth_header_for_user(user.id)

    run_resp = client.post("/api/audit/run", headers=headers)
    assert run_resp.status_code == 201, run_resp.text
    payload = run_resp.json()
    assert payload["id"]
    assert "health_score" in payload

    latest = client.get("/api/audit/latest", headers=headers)
    assert latest.status_code == 200
    assert latest.json()["id"] == payload["id"]


def test_free_vs_premium_findings_limit(client, db_session):
    user = create_user(db_session, "limits@example.com")
    account = seed_connected_account(db_session, user)
    seed_audit_run_with_findings(db_session, user.id, account.id, count=5)
    headers = auth_header_for_user(user.id)

    free_findings = client.get("/api/audit/latest/findings", headers=headers)
    assert free_findings.status_code == 200
    assert len(free_findings.json()) == 3

    switch = client.post("/api/billing/dev/plan", json={"plan_tier": "premium"}, headers=headers)
    assert switch.status_code == 200

    premium_findings = client.get("/api/audit/latest/findings", headers=headers)
    assert premium_findings.status_code == 200
    assert len(premium_findings.json()) == 5


def test_imported_history_can_run_audit_and_generate_ai_summary(client, db_session):
    user = create_user(db_session, "import-audit@example.com")
    headers = auth_header_for_user(user.id)

    csv_content = (
        "Date,Campaign name,Campaign ID,Ad set name,Ad set ID,Ad name,Ad ID,Amount spent,Impressions,Reach,Clicks,CTR,Purchase conversion value,Purchases,Delivery,Objective\n"
        "2026-03-01,Imported Campaign,cmp_1,Imported Set,adset_1,Creative A,ad_1,150,10000,7000,150,1.5,120,2,active,conversions\n"
        "2026-03-02,Imported Campaign,cmp_1,Imported Set,adset_1,Creative A,ad_1,160,10000,7000,140,1.4,110,1,active,conversions\n"
        "2026-03-03,Imported Campaign,cmp_1,Imported Set,adset_1,Creative A,ad_1,155,9500,6900,120,1.26,90,1,active,conversions\n"
    )

    upload = client.post(
        "/api/sync/import-report",
        headers=headers,
        files={"file": ("history.csv", csv_content, "text/csv")},
        data={"replace_existing": "true"},
    )
    assert upload.status_code == 200, upload.text

    run_resp = client.post("/api/audit/run", headers=headers)
    assert run_resp.status_code == 201, run_resp.text
    payload = run_resp.json()
    assert payload["id"]
    assert payload["health_score"] >= 0

    dashboard = client.get("/api/audit/dashboard", headers=headers)
    assert dashboard.status_code == 200, dashboard.text
    dashboard_payload = dashboard.json()
    assert dashboard_payload["kpis"]["spend"] > 0
    assert dashboard_payload["audit"]["id"] == payload["id"]

    summary = client.get("/api/audit/latest/ai-summary", headers=headers)
    assert summary.status_code == 200, summary.text
    summary_payload = summary.json()
    assert summary_payload["short_executive_summary"]

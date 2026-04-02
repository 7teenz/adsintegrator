from io import BytesIO

from openpyxl import Workbook

from tests.helpers import auth_header_for_user, create_user


def test_csv_import_populates_sync_summary(client, db_session):
    user = create_user(db_session, "csv@example.com")
    headers = auth_header_for_user(user.id)

    csv_content = (
        "Date,Campaign name,Campaign ID,Ad set name,Ad set ID,Ad name,Ad ID,Amount spent,Impressions,Reach,Clicks,CTR,Purchase conversion value,Purchases\n"
        "2026-03-01,Brand Campaign,cmp_1,Prospecting Set,adset_1,Creative A,ad_1,120.5,10000,7000,320,3.2,250,8\n"
        "2026-03-02,Brand Campaign,cmp_1,Prospecting Set,adset_1,Creative A,ad_1,90.0,8000,6000,240,3.0,180,6\n"
    )

    upload = client.post(
        "/api/sync/import-report",
        headers=headers,
        files={"file": ("history.csv", csv_content, "text/csv")},
        data={"replace_existing": "true"},
    )
    assert upload.status_code == 200, upload.text
    payload = upload.json()
    assert payload["campaigns"] >= 1
    assert payload["insight_rows"] >= 2

    summary = client.get("/api/sync/summary", headers=headers)
    assert summary.status_code == 200
    summary_payload = summary.json()
    assert summary_payload["campaigns"] >= 1
    assert summary_payload["campaign_insight_rows"] >= 2


def test_csv_import_supports_russian_ads_manager_headers(client, db_session):
    user = create_user(db_session, "csv-ru@example.com")
    headers = auth_header_for_user(user.id)

    csv_content = (
        "\"Название кампании\",\"Название группы объявлений\",\"Статус показа\",\"Уровень показа\",Охват,Показы,Частота,\"Сумма затрат (USD)\",Начало,Конец,\"Дата начала отчетности\",\"Дата окончания отчетности\"\n"
        ",,,,1104832,2588438,2.34283402,289.61,,,2025-10-01,2025-10-31\n"
        "IG_FB_Awareness_Infinbank,IG_FB_Awareness_Infinbank,completed,adset,882555,1274858,1.44450827,149.88,2025-10-14,2025-10-31,2025-10-01,2025-10-31\n"
    )

    upload = client.post(
        "/api/sync/import-report",
        headers=headers,
        files={"file": ("ru-history.csv", csv_content.encode("utf-8"), "text/csv")},
        data={"replace_existing": "true"},
    )
    assert upload.status_code == 200, upload.text
    payload = upload.json()
    assert payload["campaigns"] >= 1
    assert payload["insight_rows"] >= 1


def test_xlsx_import_populates_sync_summary(client, db_session):
    user = create_user(db_session, "xlsx@example.com")
    headers = auth_header_for_user(user.id)

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Report"
    sheet.append(
        [
            "Date",
            "Campaign name",
            "Campaign ID",
            "Ad set name",
            "Ad set ID",
            "Ad name",
            "Ad ID",
            "Amount spent",
            "Impressions",
            "Reach",
            "Clicks",
            "Purchase conversion value",
            "Purchases",
        ]
    )
    sheet.append(["2026-03-01", "Growth Campaign", "cmp_x", "Scale Set", "adset_x", "Creative X", "ad_x", 140.0, 12000, 9000, 360, 420, 10])
    sheet.append(["2026-03-02", "Growth Campaign", "cmp_x", "Scale Set", "adset_x", "Creative X", "ad_x", 110.0, 9500, 7300, 280, 350, 8])

    content = BytesIO()
    workbook.save(content)
    content.seek(0)

    upload = client.post(
        "/api/sync/import-report",
        headers=headers,
        files={"file": ("history.xlsx", content.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        data={"replace_existing": "true"},
    )
    assert upload.status_code == 200, upload.text
    payload = upload.json()
    assert payload["campaigns"] >= 1
    assert payload["insight_rows"] >= 2

    summary = client.get("/api/sync/summary", headers=headers)
    assert summary.status_code == 200
    summary_payload = summary.json()
    assert summary_payload["campaigns"] >= 1
    assert summary_payload["campaign_insight_rows"] >= 2

from app.services.entitlements import EntitlementService
from tests.helpers import create_user


def test_entitlements_default_free(db_session):
    user = create_user(db_session, "free@example.com")
    ent = EntitlementService.get_entitlements(db_session, user.id)
    assert ent.plan_tier == "free"
    assert ent.max_findings == 3
    assert ent.show_advanced_charts is False


def test_entitlements_upgrade_to_premium(db_session):
    user = create_user(db_session, "premium@example.com")
    EntitlementService.set_plan_tier_local(db_session, user.id, "premium")
    ent = EntitlementService.get_entitlements(db_session, user.id)
    assert ent.plan_tier == "premium"
    assert ent.max_findings >= 100
    assert ent.show_advanced_charts is True

from datetime import UTC, datetime
from uuid import uuid4

from scope_guard.domain.auth.domain import User


def test_new_pending_identity_has_no_product_access():
    user = User(uuid4(), "pending@example.test", "private", email_verification_required=True)
    assert user.public()["workspaceAccess"] == "email_confirmation_required"
    assert "private" not in str(user.public())
    assert "session_version" not in user.public()


def test_legacy_exemption_and_confirmed_identity_have_access():
    assert User(uuid4(), "legacy@example.test", "private").public()["workspaceAccess"] == "allowed"
    confirmed = User(
        uuid4(),
        "ok@example.test",
        "private",
        email_verification_required=True,
        email_verified_at=datetime.now(UTC),
    )
    assert confirmed.public()["workspaceAccess"] == "allowed"

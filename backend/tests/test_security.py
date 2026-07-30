import uuid

from app.core.security import create_access_token, decode_access_token, hash_password, verify_password


def test_password_hash_round_trip() -> None:
    hashed = hash_password("A-strong-test-password-123")
    assert hashed != "A-strong-test-password-123"
    assert verify_password("A-strong-test-password-123", hashed)
    assert not verify_password("wrong-password", hashed)


def test_access_token_contains_tenant_scope() -> None:
    user_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    token = create_access_token(user_id=user_id, tenant_id=tenant_id, role="researcher")
    payload = decode_access_token(token)
    assert payload["sub"] == str(user_id)
    assert payload["tenant_id"] == str(tenant_id)
    assert payload["role"] == "researcher"

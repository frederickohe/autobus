"""Webhook signing used by partner integrations."""
from core.embed.service.embed_service import hash_api_key, sign_webhook_body


def test_sign_webhook_body_is_stable():
    body = b'{"type":"order.created"}'
    first = sign_webhook_body("secret", body)
    second = sign_webhook_body("secret", body)
    assert first == second
    assert first.startswith("sha256=")
    assert sign_webhook_body("other", body) != first


def test_api_key_hash_does_not_echo_the_key():
    raw = "ab_live_example"
    digest = hash_api_key(raw)
    assert raw not in digest
    assert len(digest) == 64

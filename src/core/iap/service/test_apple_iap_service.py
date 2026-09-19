from unittest.mock import MagicMock, patch

from core.iap.service.apple_iap_service import AppleIapService


def _payload(**overrides):
    data = {
        "bundleId": "com.autobus.app",
        "productId": "autobus.credits.20.v4",
        "transactionId": "2000001235501146",
        "originalTransactionId": "2000001235501146",
        "environment": "Sandbox",
        "type": "Consumable",
        "price": 4990,
    }
    data.update(overrides)
    return data


@patch("core.iap.service.apple_iap_service.decode_signed_data")
def test_rejects_sandbox_when_not_allowed(decode):
    decode.return_value = _payload()
    service = AppleIapService(MagicMock())
    service.credits = MagicMock()
    with patch.dict("os.environ", {"DEBUG": "false", "APPLE_IAP_ALLOW_SANDBOX": "false"}):
        result = service.apply_signed_transaction("user-1", "a.b.c")
    assert result["success"] is False
    assert "sandbox" in result["message"].lower()
    service.credits.grant_pack.assert_not_called()


@patch("core.iap.service.apple_iap_service.decode_signed_data")
def test_rejects_zero_price_production_transaction(decode):
    decode.return_value = _payload(environment="Production", price=0)
    service = AppleIapService(MagicMock())
    service.credits = MagicMock()
    with patch.dict("os.environ", {"DEBUG": "false", "APPLE_IAP_ALLOW_SANDBOX": "false"}):
        result = service.apply_signed_transaction("user-1", "a.b.c")
    assert result["success"] is False
    assert "price" in result["message"].lower()
    service.credits.grant_pack.assert_not_called()


@patch("core.iap.service.apple_iap_service.decode_signed_data")
def test_grants_paid_production_consumable(decode):
    decode.return_value = _payload(environment="Production")
    service = AppleIapService(MagicMock())
    service.credits = MagicMock()
    service.credits.grant_pack.return_value = {
        "success": True,
        "message": "20 credits added",
        "credits_granted": 20,
        "pack_id": "starter",
    }
    with patch.dict("os.environ", {"DEBUG": "false", "APPLE_IAP_ALLOW_SANDBOX": "false"}):
        result = service.apply_signed_transaction("user-1", "a.b.c")
    assert result["success"] is True
    service.credits.grant_pack.assert_called_once()

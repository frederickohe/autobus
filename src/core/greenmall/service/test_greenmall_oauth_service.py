"""Unit tests for GreenMall first-party linking helpers."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from core.greenmall.service.greenmall_oauth_service import (
    GreenMallOAuthService,
    GreenMallOAuthState,
    extract_api_key,
    extract_store_id,
    extract_store_name,
    greenmall_authorize_url,
    greenmall_callback_url,
)


class GreenMallCallbackUrlTest(unittest.TestCase):
    def test_uses_explicit_callback_url(self):
        with patch.dict(
            "os.environ",
            {"GREENMALL_CALLBACK_URL": "https://api.useautobus.com/api/v1/greenmall/callback"},
            clear=False,
        ):
            self.assertEqual(
                greenmall_callback_url(),
                "https://api.useautobus.com/api/v1/greenmall/callback",
            )

    def test_builds_callback_from_public_api(self):
        with patch.dict(
            "os.environ",
            {
                "AUTOBUS_PUBLIC_API_URL": "https://api.useautobus.com",
                "GREENMALL_CALLBACK_URL": "",
            },
            clear=False,
        ):
            self.assertEqual(
                greenmall_callback_url(),
                "https://api.useautobus.com/api/v1/greenmall/callback",
            )

    def test_builds_authorize_url_from_api_base(self):
        with patch.dict(
            "os.environ",
            {
                "GREENMALL_API_URL": "https://greenmall.example.com",
                "GREENMALL_AUTHORIZE_URL": "",
                "GREENMALL_AUTHORIZE_PATH": "/integrations/autobus/authorize",
            },
            clear=False,
        ):
            self.assertEqual(
                greenmall_authorize_url(),
                "https://greenmall.example.com/integrations/autobus/authorize",
            )


class GreenMallPayloadExtractTest(unittest.TestCase):
    def test_extracts_camel_case_aliases(self):
        payload = {
            "apiKey": "gm_live_abc",
            "storeId": "store-9",
            "storeName": "Osu Mart",
        }
        self.assertEqual(extract_api_key(payload), "gm_live_abc")
        self.assertEqual(extract_store_id(payload), "store-9")
        self.assertEqual(extract_store_name(payload), "Osu Mart")


class GreenMallOAuthStateTest(unittest.TestCase):
    def setUp(self):
        GreenMallOAuthState.clear_memory()

    def tearDown(self):
        GreenMallOAuthState.clear_memory()

    def test_create_peek_and_consume(self):
        with patch(
            "core.greenmall.service.greenmall_oauth_service._redis",
            return_value=None,
        ):
            state = GreenMallOAuthState.create("user-1")
            self.assertTrue(state.startswith("gm."))
            self.assertEqual(GreenMallOAuthState.peek(state), {"user_id": "user-1"})
            self.assertEqual(GreenMallOAuthState.consume(state), {"user_id": "user-1"})
            self.assertIsNone(GreenMallOAuthState.peek(state))
            self.assertIsNone(GreenMallOAuthState.consume(state))

    def test_result_round_trip(self):
        with patch(
            "core.greenmall.service.greenmall_oauth_service._redis",
            return_value=None,
        ):
            GreenMallOAuthState.store_result("gm.test", {"status": "linked", "account_id": "a1"})
            self.assertEqual(
                GreenMallOAuthState.read_result("gm.test"),
                {"status": "linked", "account_id": "a1"},
            )


class GreenMallCallbackSecretTest(unittest.TestCase):
    def test_rejects_wrong_secret(self):
        svc = GreenMallOAuthService()
        with patch.dict(
            "os.environ",
            {"GREENMALL_CALLBACK_SECRET": "correct-secret", "DEBUG": "false"},
            clear=False,
        ):
            with self.assertRaises(PermissionError):
                svc.verify_callback_secret("wrong")

    def test_accepts_matching_secret(self):
        svc = GreenMallOAuthService()
        with patch.dict(
            "os.environ",
            {"GREENMALL_CALLBACK_SECRET": "correct-secret", "DEBUG": "false"},
            clear=False,
        ):
            svc.verify_callback_secret("correct-secret")


if __name__ == "__main__":
    unittest.main()

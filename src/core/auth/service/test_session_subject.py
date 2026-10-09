import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

from fastapi import HTTPException

from core.auth.dependencies import resolve_user_from_jwt
from core.auth.service.authservice import AuthService


class SessionSubjectTest(unittest.TestCase):
    def test_signup_keeps_a_real_email(self):
        self.assertEqual(
            AuthService.resolve_signup_email("  Owner@Example.com ", "0538802058"),
            "Owner@Example.com",
        )

    def test_blank_email_uses_phone_identity(self):
        self.assertEqual(
            AuthService.resolve_signup_email("", "0538802058"),
            "0538802058@phone.useautobus.com",
        )
        self.assertEqual(
            AuthService.resolve_signup_email(None, "+233 53 880 2058"),
            "233538802058@phone.useautobus.com",
        )

    def test_blank_email_and_phone_is_rejected(self):
        with self.assertRaises(HTTPException) as raised:
            AuthService.resolve_signup_email("   ", "123")
        self.assertEqual(raised.exception.status_code, 400)

    def test_invalid_email_is_rejected(self):
        with self.assertRaises(HTTPException):
            AuthService.resolve_signup_email("not-an-email", "0538802058")

    def test_session_subject_never_blank(self):
        self.assertEqual(
            AuthService.session_subject(SimpleNamespace(email="a@b.co", id="u1")),
            "a@b.co",
        )
        self.assertEqual(
            AuthService.session_subject(SimpleNamespace(email="", id="u1")),
            "u1",
        )
        self.assertEqual(
            AuthService.session_subject(SimpleNamespace(email=None, id="u1")),
            "u1",
        )

    def test_blank_token_subject_uses_manager_claim(self):
        user = SimpleNamespace(id="7CJL4yPkLSZtEdegvPZc", email="")
        db = MagicMock()
        email_query = MagicMock()
        email_query.first.return_value = None
        id_query = MagicMock()
        id_query.first.return_value = user
        db.query.return_value.filter.side_effect = [email_query, id_query]

        authjwt = MagicMock()
        authjwt.get_jwt_subject.return_value = ""
        authjwt.get_raw_jwt.return_value = {"sub": "", "mgr": user.id, "type": "access"}

        resolved = resolve_user_from_jwt(authjwt, db)
        self.assertIs(resolved, user)


if __name__ == "__main__":
    unittest.main()

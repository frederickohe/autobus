import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

from fastapi import HTTPException

from core.auth.service.account_deletion_service import (
    BILLING_NOTE,
    META_NOTE,
    SUBSCRIPTION_NOTE,
    AccountDeletionService,
    deletion_notes,
    is_deleted_user,
    tombstone_user,
)
from core.user.model.User import UserStatus


class AccountDeletionHelpersTest(unittest.TestCase):
    def test_tombstone_wipes_pii_and_marks_deleted(self):
        user = SimpleNamespace(
            id="abc123",
            email="owner@example.com",
            fullname="Ama Owner",
            phone="0244000000",
            hashed_password="old-hash",
            ghana_card="GHA-123",
            profile_picture_url="https://cdn/x.jpg",
            nationality="Ghana",
            date_of_birth="1990-01-01",
            gender="FEMALE",
            address="Accra",
            location="Accra",
            company="Ama Shop",
            current_branch="Osu",
            staff_id="S1",
            occupation="Retail",
            organization_workplace="Ama Shop",
            skills=["sales"],
            experiences=["owner"],
            facebook_url="https://fb.com/x",
            whatsapp_number="0244000000",
            linkedin_url="https://li.com/x",
            twitter_url="https://x.com/x",
            instagram_url="https://ig.com/x",
            agents={"sales": {"status": "active"}},
            onboarding_profile={"q": "a"},
            managed_by_user_id="mgr1",
            enabled=True,
            status=UserStatus.ACTIVE,
            updated_at=None,
        )

        tombstone_user(user)

        self.assertEqual(user.email, "deleted.abc123@deleted.invalid")
        self.assertEqual(user.fullname, "deleted.abc123")
        self.assertIsNone(user.phone)
        self.assertIsNone(user.ghana_card)
        self.assertIsNone(user.company)
        self.assertIsNone(user.managed_by_user_id)
        self.assertEqual(user.agents, {})
        self.assertFalse(user.enabled)
        self.assertEqual(user.status, UserStatus.DELETED)
        self.assertNotEqual(user.hashed_password, "old-hash")
        self.assertTrue(is_deleted_user(user))

    def test_notes_include_subscription_warning_only_when_paid(self):
        unpaid = deletion_notes(has_paid_subscription=False)
        self.assertIn(META_NOTE, unpaid)
        self.assertIn(BILLING_NOTE, unpaid)
        self.assertNotIn(SUBSCRIPTION_NOTE, unpaid)

        paid = deletion_notes(has_paid_subscription=True)
        self.assertIn(SUBSCRIPTION_NOTE, paid)

    def test_wrong_password_is_rejected(self):
        db = MagicMock()
        service = AccountDeletionService(db)
        service.auth_service.verify_password = MagicMock(return_value=False)
        manager = SimpleNamespace(hashed_password="hash", status=UserStatus.ACTIVE)

        with self.assertRaises(HTTPException) as ctx:
            service._verify_login_password(manager, "0000")
        self.assertEqual(ctx.exception.status_code, 403)

    def test_already_deleted_login_is_rejected(self):
        db = MagicMock()
        service = AccountDeletionService(db)
        service.auth_service.verify_password = MagicMock(return_value=True)
        manager = SimpleNamespace(hashed_password="hash", status=UserStatus.DELETED)

        with self.assertRaises(HTTPException) as ctx:
            service._verify_login_password(manager, "1234")
        self.assertEqual(ctx.exception.status_code, 410)


if __name__ == "__main__":
    unittest.main()

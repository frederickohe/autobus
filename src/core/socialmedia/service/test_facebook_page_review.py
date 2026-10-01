"""Unit tests for Facebook Page activity parsing. No Graph calls."""

from __future__ import annotations

import unittest

from core.socialmedia.service.facebook_page_review import (
    engagement_count,
    parse_business_pages,
    parse_posts,
    picture_url,
    redact_secrets,
    tokens_for_row,
)


class FacebookPageReviewParseTest(unittest.TestCase):
    def test_user_token_stays_on_refresh_after_page_is_saved(self):
        user, page = tokens_for_row("page-token", "user-token", False)
        self.assertEqual(user, "user-token")
        self.assertEqual(page, "page-token")

    def test_between_steps_token_is_the_user(self):
        user, page = tokens_for_row("user-token", "user-token", True)
        self.assertEqual(user, "user-token")
        self.assertEqual(page, "")

    def test_same_token_after_connect_cannot_list_businesses(self):
        user, page = tokens_for_row("page-token", "page-token", False)
        self.assertEqual(user, "")
        self.assertEqual(page, "page-token")

    def test_picture_and_counts(self):
        self.assertEqual(picture_url({"picture": {"data": {"url": "https://cdn/p.jpg"}}}), "https://cdn/p.jpg")
        node = {
            "reactions": {"summary": {"total_count": 12}},
            "comments": {"summary": {"total_count": "3"}},
        }
        self.assertEqual(engagement_count(node, "reactions"), 12)
        self.assertEqual(engagement_count(node, "comments"), 3)

    def test_connected_page_is_marked_once(self):
        pages = parse_business_pages(
            [{"id": "1", "name": "Shop"}, {"id": "1", "name": "Shop again"}, {"id": "2", "name": "Other"}],
            relationship="Owned by this business",
            connected_page_id="1",
        )
        self.assertEqual(len(pages), 2)
        self.assertTrue(pages[0]["connected"])
        self.assertFalse(pages[1]["connected"])

    def test_posts_drop_rows_without_an_id(self):
        posts = parse_posts(
            [
                {"message": "no id"},
                {
                    "id": "p1",
                    "message": "Hello",
                    "created_time": "2026-09-01T00:00:00+0000",
                    "permalink_url": "https://facebook.com/p1",
                    "reactions": {"summary": {"total_count": 4}},
                    "comments": {"summary": {"total_count": 1}},
                },
            ]
        )
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0]["reactions"], 4)
        self.assertEqual(posts[0]["comments"], 1)

    def test_redact_strips_access_tokens(self):
        text = "failed access_token=EAABsecret&fields=id"
        self.assertNotIn("EAABsecret", redact_secrets(text))

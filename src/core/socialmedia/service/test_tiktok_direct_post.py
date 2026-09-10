"""Unit tests for TikTok Direct Post creator_info normalization."""

from __future__ import annotations

import unittest

from core.socialmedia.service.tiktok_direct_post import (
    CONSENT_BRANDED,
    CONSENT_MUSIC,
    extract_publish_ids,
    normalize_creator_info,
    normalize_publish_status,
    tiktok_consent_text,
)


class NormalizeCreatorInfoTest(unittest.TestCase):
    def test_tiktok_ok_payload(self):
        info = normalize_creator_info(
            {
                "data": {
                    "creator_nickname": "Shop TV",
                    "creator_username": "shoptv",
                    "creator_avatar_url": "https://example.com/a.png",
                    "privacy_level_options": [
                        "SELF_ONLY",
                        "MUTUAL_FOLLOW_FRIENDS",
                        "FOLLOWER_OF_CREATOR",
                    ],
                    "comment_disabled": False,
                    "duet_disabled": True,
                    "stitch_disabled": False,
                    "max_video_post_duration_sec": 180,
                },
                "error": {"code": "ok", "message": ""},
            }
        )
        self.assertTrue(info["can_post"])
        self.assertEqual(info["creator_nickname"], "Shop TV")
        self.assertEqual(info["privacy_level_options"][0], "SELF_ONLY")
        self.assertTrue(info["duet_disabled"])
        self.assertEqual(info["max_video_post_duration_sec"], 180)
        self.assertEqual(info["privacy_level_labels"]["SELF_ONLY"], "Only me")

    def test_too_many_posts_blocks_publish(self):
        info = normalize_creator_info(
            {
                "data": {},
                "error": {
                    "code": "spam_risk_too_many_posts",
                    "message": "cap",
                },
            }
        )
        self.assertFalse(info["can_post"])
        self.assertIn("Try again later", info["cannot_post_reason"])

    def test_can_post_false(self):
        info = normalize_creator_info({"can_post": False, "nickname": "A"})
        self.assertFalse(info["can_post"])
        self.assertEqual(info["creator_nickname"], "A")

    def test_fallback_name(self):
        info = normalize_creator_info({}, fallback_name="Linked TikTok")
        self.assertEqual(info["creator_nickname"], "Linked TikTok")


class ConsentAndStatusTest(unittest.TestCase):
    def test_consent_switches_for_branded(self):
        self.assertEqual(tiktok_consent_text(branded_content=False), CONSENT_MUSIC)
        self.assertEqual(tiktok_consent_text(branded_content=True), CONSENT_BRANDED)

    def test_publish_complete(self):
        status = normalize_publish_status(
            {"data": {"status": "PUBLISH_COMPLETE", "publicaly_available_post_id": ["1"]}}
        )
        self.assertTrue(status["complete"])
        self.assertFalse(status["processing"])
        self.assertEqual(status["public_post_ids"], ["1"])

    def test_extract_publish_id(self):
        ids = extract_publish_ids(
            {"posts": [{"settings": {}, "publish_id": "v_pub_url~v2.123"}]}
        )
        self.assertEqual(ids, ["v_pub_url~v2.123"])


if __name__ == "__main__":
    unittest.main()

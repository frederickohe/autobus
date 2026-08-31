"""Unit tests for Postiz OAuth URL rewrites."""

from __future__ import annotations

import unittest
from urllib.parse import parse_qs, urlsplit

from core.socialmedia.service.postiz_api_service import apply_tiktok_oauth_scopes


class ApplyTiktokOauthScopesTest(unittest.TestCase):
    def test_strips_video_list_and_video_create(self):
        url = (
            "https://www.tiktok.com/v2/auth/authorize/"
            "?client_key=abc"
            "&scope=video.list%2Cuser.info.basic%2Cvideo.publish"
            "%2Cvideo.upload%2Cuser.info.profile%2Cuser.info.stats%2Cvideo.create"
            "&response_type=code"
        )
        rewritten = apply_tiktok_oauth_scopes(url, slug="tiktok")
        scopes = parse_qs(urlsplit(rewritten).query)["scope"][0].split(",")
        self.assertEqual(
            scopes,
            [
                "user.info.basic",
                "video.publish",
                "video.upload",
                "user.info.profile",
                "user.info.stats",
            ],
        )

    def test_ignores_non_tiktok_slug(self):
        url = "https://www.tiktok.com/v2/auth/authorize/?scope=video.list,user.info.basic"
        self.assertEqual(apply_tiktok_oauth_scopes(url, slug="facebook"), url)

    def test_ignores_non_tiktok_host(self):
        url = "https://example.com/oauth?scope=video.list,user.info.basic"
        self.assertEqual(apply_tiktok_oauth_scopes(url, slug="tiktok"), url)


if __name__ == "__main__":
    unittest.main()

"""Unit tests for Veo completed-operation parsing."""

from __future__ import annotations

import unittest

from core.media.service.veo_operation import extract_video_from_operation, missing_video_error


class VeoOperationParseTest(unittest.TestCase):
    def test_extracts_nested_https_uri(self):
        result = extract_video_from_operation(
            {
                "done": True,
                "response": {
                    "generateVideoResponse": {
                        "generatedSamples": [
                            {"video": {"uri": "https://generativelanguage.googleapis.com/v1beta/files/abc"}}
                        ]
                    }
                },
            }
        )
        self.assertTrue(result.has_media)
        self.assertIn("files/abc", result.uri or "")

    def test_extracts_relative_files_uri(self):
        result = extract_video_from_operation(
            {
                "response": {
                    "generatedSamples": [{"video": {"uri": "files/xyz123"}}]
                }
            }
        )
        self.assertEqual(result.uri, "files/xyz123")

    def test_extracts_inline_bytes(self):
        payload = "A" * 120
        result = extract_video_from_operation(
            {"response": {"generatedSamples": [{"video": {"bytesBase64Encoded": payload}}]}}
        )
        self.assertEqual(result.base64, payload)
        self.assertTrue(result.has_media)

    def test_rai_reason_without_media(self):
        result = extract_video_from_operation(
            {
                "done": True,
                "response": {
                    "generateVideoResponse": {
                        "raiMediaFilteredReasons": ["Sensitive content"]
                    }
                },
            }
        )
        self.assertFalse(result.has_media)
        self.assertIn("Sensitive content", missing_video_error(result))


if __name__ == "__main__":
    unittest.main()

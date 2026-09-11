"""Unit tests for optional generation reference media."""

from __future__ import annotations

import base64
import unittest

from core.media.service.media_reference import (
    build_image_generate_payload,
    build_veo_instance,
    clean_base64,
    infer_mime,
    is_video_mime,
)


class MediaReferenceHelpersTest(unittest.TestCase):
    def test_clean_base64_strips_data_url(self):
        mime, raw = clean_base64("data:image/png;base64,abc123")
        self.assertEqual(mime, "image/png")
        self.assertEqual(raw, "abc123")

    def test_infer_mime_from_url(self):
        self.assertEqual(infer_mime("https://cdn.example/ref.jpg"), "image/jpeg")
        self.assertEqual(infer_mime("clip.mp4"), "video/mp4")
        self.assertTrue(is_video_mime("video/quicktime"))

    def test_image_payload_includes_inline_reference(self):
        payload = build_image_generate_payload(
            "Make a flyer",
            reference_base64="data:image/jpeg;base64,QUJD",
            reference_mime_type="image/jpeg",
        )
        parts = payload["contents"][0]["parts"]
        self.assertEqual(parts[0]["text"], "Make a flyer")
        self.assertEqual(parts[1]["inlineData"]["mimeType"], "image/jpeg")
        self.assertEqual(parts[1]["inlineData"]["data"], "QUJD")

    def test_image_payload_without_reference_is_text_only(self):
        payload = build_image_generate_payload("Just text")
        self.assertEqual(len(payload["contents"][0]["parts"]), 1)

    def test_veo_instance_uses_image_for_photo_reference(self):
        instance = build_veo_instance(
            "Animate this",
            reference_base64=base64.b64encode(b"img").decode(),
            reference_mime_type="image/png",
        )
        self.assertIn("image", instance)
        self.assertNotIn("video", instance)
        self.assertEqual(instance["image"]["mimeType"], "image/png")

    def test_veo_instance_uses_video_for_clip_reference(self):
        instance = build_veo_instance(
            "Continue this scene",
            reference_base64=base64.b64encode(b"vid").decode(),
            reference_mime_type="video/mp4",
        )
        self.assertIn("video", instance)
        self.assertNotIn("image", instance)


if __name__ == "__main__":
    unittest.main()

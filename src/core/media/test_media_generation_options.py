import unittest

from core.agent.dto.media_generation_request import MediaGenerationRequest
from core.media.service.media_generation_options import (
    apply_kind_brief,
    image_generation_config,
    media_kind_for,
    normalize_duration,
    normalize_image_aspect,
    normalize_resolution,
    normalize_video_aspect,
    veo_parameters,
)


class MediaGenerationOptionsTest(unittest.TestCase):
    def test_aspect_and_duration_normalization(self):
        self.assertEqual(normalize_image_aspect("16:9"), "16:9")
        self.assertEqual(normalize_image_aspect("square"), None)
        self.assertEqual(normalize_video_aspect("3:4"), "9:16")
        self.assertEqual(normalize_duration(10), 8)
        self.assertEqual(normalize_duration(6), 6)
        self.assertEqual(normalize_resolution("360p"), "720p")
        self.assertEqual(normalize_resolution("720p"), "720p")

    def test_kind_mapping(self):
        self.assertEqual(media_kind_for("character", "image"), "image")
        self.assertEqual(media_kind_for("scene", "video"), "video")
        self.assertIn("character reference", apply_kind_brief("A baker", "character").lower())

    def test_image_config_includes_aspect(self):
        config = image_generation_config("9:16")
        self.assertEqual(config["responseModalities"], ["TEXT", "IMAGE"])
        self.assertEqual(config["imageConfig"]["aspectRatio"], "9:16")

    def test_veo_parameters(self):
        params = veo_parameters(aspect_ratio="9:16", duration_seconds=10, resolution="720p")
        self.assertEqual(params["aspectRatio"], "9:16")
        self.assertEqual(params["durationSeconds"], 8)
        self.assertEqual(params["resolution"], "720p")


class MediaGenerationRequestTest(unittest.TestCase):
    def test_legacy_and_list_references(self):
        req = MediaGenerationRequest(
            prompt="A shopfront at dusk",
            reference_url="https://example.com/ref.jpg",
            references=[{"base64": "abcd", "mime_type": "image/png"}],
            aspect_ratio="16:9",
            kind="character",
        )
        refs = req.resolved_references()
        self.assertEqual(len(refs), 2)
        self.assertEqual(refs[0].url, "https://example.com/ref.jpg")
        self.assertEqual(refs[1].base64, "abcd")
        self.assertEqual(req.kind, "character")


if __name__ == "__main__":
    unittest.main()

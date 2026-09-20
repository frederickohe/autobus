import unittest
from datetime import datetime, timezone
from types import SimpleNamespace

from core.media.dto.automedia_dto import AutomediaAssetDto, AutomediaClipDto
from core.media.service.automedia_library import _clips_payload, _ms, asset_to_dto


class AutomediaLibraryHelpersTest(unittest.TestCase):
    def test_clips_payload_drops_incomplete_rows(self):
        clips = _clips_payload(
            [
                {"id": "c1", "url": "https://cdn.example/a.mp4", "prompt": "walk", "duration_sec": 6},
                {"id": "", "url": "https://cdn.example/b.mp4"},
                {"url": "https://cdn.example/c.mp4"},
                "skip",
            ]
        )
        self.assertEqual(len(clips), 1)
        self.assertEqual(clips[0]["id"], "c1")
        self.assertEqual(clips[0]["duration_sec"], 6)

    def test_asset_to_dto_maps_character(self):
        now = datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc)
        row = SimpleNamespace(
            id="asset-1",
            campaign_id="camp-1",
            user_id="user-1",
            kind="character",
            url="https://cdn.example/face.png",
            prompt="A baker in a green apron",
            name="Ama",
            favorite=True,
            source="generated",
            aspect="1:1",
            duration_sec=None,
            resolution=None,
            clips=[],
            created_at=now,
            updated_at=now,
        )
        dto = asset_to_dto(row)
        self.assertEqual(dto.kind, "character")
        self.assertEqual(dto.name, "Ama")
        self.assertTrue(dto.favorite)
        self.assertEqual(dto.created_at, _ms(now))

    def test_asset_dto_accepts_scene_clips(self):
        dto = AutomediaAssetDto(
            id="scene-1",
            campaign_id="camp-1",
            kind="scene",
            url="https://cdn.example/scene.mp4",
            prompt="Man holding banknote in studio",
            clips=[AutomediaClipDto(id="clip-1", url="https://cdn.example/scene.mp4", duration_sec=10)],
        )
        self.assertEqual(dto.clips[0].duration_sec, 10)


if __name__ == "__main__":
    unittest.main()

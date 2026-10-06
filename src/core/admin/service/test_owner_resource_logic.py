import unittest
from datetime import datetime, timezone
from types import SimpleNamespace

from core.admin.service.owner_resource_logic import (
    news_search_query,
    parse_news_rss,
    rank_for_industry,
    youtube_id_from,
)


class OwnerResourceLogicTest(unittest.TestCase):
    def test_youtube_ids(self):
        self.assertEqual(youtube_id_from("ferhOYx1NMo"), "ferhOYx1NMo")
        self.assertEqual(
            youtube_id_from("https://www.youtube.com/watch?v=u4ZoJKF_VuA"),
            "u4ZoJKF_VuA",
        )
        self.assertEqual(youtube_id_from("https://youtu.be/bNpx7gpSqbY"), "bNpx7gpSqbY")
        self.assertEqual(
            youtube_id_from("https://www.youtube.com/shorts/CBYhVcO4WgI"),
            "CBYhVcO4WgI",
        )
        self.assertIsNone(youtube_id_from("https://example.com/not-a-video"))

    def test_rank_puts_niche_ahead_of_general(self):
        published = datetime(2026, 1, 1, tzinfo=timezone.utc)
        bakery = SimpleNamespace(industry="Food & Beverage", sort_order=0, published_at=published, title="bakery")
        general = SimpleNamespace(industry=None, sort_order=0, published_at=published, title="general")
        retail = SimpleNamespace(industry="Retail & E-commerce", sort_order=0, published_at=published, title="shop")
        ranked = rank_for_industry([general, retail, bakery], "Food & Beverage")
        self.assertEqual([row.title for row in ranked], ["bakery", "general"])

    def test_news_query_and_rss_parse(self):
        self.assertIn("bakery", news_search_query("Food & Beverage"))
        xml = """<?xml version="1.0"?>
        <rss><channel>
          <item>
            <title>Cocoa prices rise - BBC</title>
            <link>https://news.example/cocoa</link>
            <pubDate>Tue, 06 Oct 2026 08:00:00 GMT</pubDate>
            <source>BBC</source>
          </item>
        </channel></rss>"""
        items = parse_news_rss(xml, industry="Agriculture & Farming")
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["title"], "Cocoa prices rise")
        self.assertEqual(items[0]["source_name"], "BBC")
        self.assertTrue(items[0]["id"].startswith("live_"))


if __name__ == "__main__":
    unittest.main()

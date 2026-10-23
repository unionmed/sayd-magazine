#!/usr/bin/env python3
"""Fast safety checks for stable, traceable social links."""
import unittest
from sayd_campaign_url import make_link

class CampaignLinkTests(unittest.TestCase):
    def test_arabic_and_existing_utm_are_not_reused(self):
        url = make_link(
            "https://sayd-magazine.com/posts/%D8%B4%D9%85%D8%A7%D9%84/",
            "facebook", "sayd_growth_20261023", "north_story")
        self.assertIn("/posts/%D8%B4%D9%85%D8%A7%D9%84/", url)
        self.assertIn("utm_source=facebook&utm_medium=organic_social", url)
        self.assertIn("utm_campaign=sayd_growth_20261023&utm_content=north_story", url)
    def test_index_html_is_not_a_second_landing_page(self):
        url = make_link("https://sayd-magazine.com/en/posts/birds/index.html",
                        "youtube", "sayd_growth_20261023", "birds_reel")
        self.assertIn("/en/posts/birds/?", url)
        self.assertNotIn("index.html", url)
    def test_forbid_external_site_or_tracking_query_or_extra_path(self):
        for source in (
            "https://example.com/posts/one/",
            "http://sayd-magazine.com/posts/one/",
            "https://sayd-magazine.com/posts/one/?fbclid=abc",
            "https://sayd-magazine.com/category/hunting/",
            "https://sayd-magazine.com/posts/one/two/",
        ):
            with self.subTest(source=source), self.assertRaises(ValueError):
                make_link(source, "facebook", "sayd_growth_20261023", "birds")
    def test_require_stable_campaign_and_content(self):
        with self.assertRaises(ValueError):
            make_link("https://sayd-magazine.com/posts/one/", "facebook", "bad campaign", "item")

if __name__ == "__main__":
    unittest.main()

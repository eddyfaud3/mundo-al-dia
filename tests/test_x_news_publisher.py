import unittest
from scripts.x_news_publisher import corroborated_items, title_overlap


class CorroborationTests(unittest.TestCase):
    def item(self, source, title):
        return {
            "source": source,
            "title": title,
            "published": "2026-11-18T12:00:00+00:00",
        }

    def test_same_story_across_two_outlets_is_kept(self):
        items = [
            self.item("DW Español", "Gobierno de México anuncia nuevas medidas económicas"),
            self.item("France 24 Español", "México anuncia nuevas medidas económicas del gobierno"),
        ]
        result = corroborated_items(items)
        self.assertEqual(len(result), 2)
        self.assertEqual(set(result[0]["corroborating_sources"]), {"DW Español", "France 24 Español"})

    def test_unrelated_headlines_are_rejected(self):
        items = [
            self.item("DW Español", "Gobierno anuncia nuevas medidas económicas"),
            self.item("BBC News Mundo", "Un terremoto sacude una región del Pacífico"),
        ]
        self.assertEqual(corroborated_items(items), [])

    def test_same_source_does_not_corroborate_itself(self):
        items = [
            self.item("DW Español", "Gobierno anuncia nuevas medidas económicas"),
            self.item("DW Español", "Gobierno presenta medidas económicas nuevas"),
        ]
        self.assertEqual(corroborated_items(items), [])

    def test_overlap_is_bounded(self):
        self.assertGreaterEqual(
            title_overlap("México anuncia nuevas medidas económicas",
                          "Gobierno de México anuncia medidas económicas nuevas"),
            0.30,
        )


if __name__ == "__main__":
    unittest.main()

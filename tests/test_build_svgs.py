import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import build_svgs as b  # noqa: E402

SNAKE = '<svg viewBox="-16 -32 880 192" width="880" height="192" xmlns="http://www.w3.org/2000/svg"><rect class="c c0" x="0" y="0"/></svg>'

STATS = b.Stats(
    contributions=2821, commits=2700, pull_requests=12, private=2500, current_streak=5, longest_streak=40,
    best_day=90, last_active="2026-10-05", public_repos=1, stars=0, followers=5, since=2021, fetched="2026-10-05",
)


def d(day: int) -> str:
    return f"2026-10-{day:02d}"


class Streaks(unittest.TestCase):
    def test_counts_back_from_today(self):
        days = [(d(1), 1), (d(2), 0), (d(3), 2), (d(4), 1), (d(5), 3)]
        self.assertEqual(b.streaks(days, d(5)), (3, 3))

    def test_empty_today_does_not_break_current(self):
        days = [(d(3), 2), (d(4), 1), (d(5), 0)]
        self.assertEqual(b.streaks(days, d(5)), (2, 2))

    def test_empty_yesterday_breaks_current(self):
        days = [(d(2), 4), (d(3), 0), (d(4), 0), (d(5), 0)]
        self.assertEqual(b.streaks(days, d(5)), (0, 1))

    def test_future_days_ignored(self):
        days = [(d(4), 1), (d(5), 1), (d(6), 0), (d(7), 0)]
        self.assertEqual(b.streaks(days, d(5)), (2, 2))

    def test_longest_is_independent_of_current(self):
        days = [(d(1), 1), (d(2), 1), (d(3), 1), (d(4), 0), (d(5), 1)]
        self.assertEqual(b.streaks(days, d(5)), (1, 3))


class Compose(unittest.TestCase):
    def test_live_render_is_valid_xml_with_values_and_snake(self):
        svg = b.compose(STATS, SNAKE)
        ET.fromstring(svg)
        self.assertIn("2,821", svg)
        self.assertIn("synced 2026-10-05", svg)
        self.assertIn('class="c c0"', svg)
        self.assertNotIn("offline", svg)

    def test_offline_render_says_so(self):
        svg = b.compose(None, None)
        ET.fromstring(svg)
        self.assertIn("○ offline", svg)
        self.assertIn("offline (local build)", svg)

    def test_snake_without_viewbox_fails_loud(self):
        with self.assertRaises(ValueError):
            b.compose(STATS, "<svg><rect/></svg>")


if __name__ == "__main__":
    unittest.main()

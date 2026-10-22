import importlib.util
import os
import sys
import unittest


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


@unittest.skipUnless(importlib.util.find_spec("ttkbootstrap"), "ttkbootstrap is not installed")
class TestThemeAllowlist(unittest.TestCase):
    def test_allowlist_matches_the_installed_ttkbootstrap_themes(self):
        from ttkbootstrap.themes.standard import STANDARD_THEMES

        import ui

        self.assertEqual(set(ui.THEMES), set(STANDARD_THEMES))


if __name__ == "__main__":
    unittest.main()

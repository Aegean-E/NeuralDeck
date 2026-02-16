import unittest
from unittest.mock import MagicMock, patch
import sys
import os
import threading

# Add parent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock 'aqt' and 'anki' modules before importing anki_addon
sys.modules['aqt'] = MagicMock()
sys.modules['aqt.utils'] = MagicMock()
sys.modules['anki'] = MagicMock()
sys.modules['anki.notes'] = MagicMock()
sys.modules['anki.hooks'] = MagicMock()

# Setup mw mock
mw_mock = MagicMock()
mw_mock.addonManager.getConfig.return_value = {}
sys.modules['aqt'].mw = mw_mock

# Mock Note class
class MockNote:
    def __init__(self, col=None, model=None):
        self.col = col
        self.model = model
        self.fields = {}
        self.tags = []
        self.deck_id = None

    def __setitem__(self, key, value):
        self.fields[key] = value

    def __getitem__(self, key):
        return self.fields.get(key)

sys.modules['anki.notes'].Note = MockNote

# Prevent server thread from starting by patching threading.Thread
with patch('threading.Thread'):
    import anki_addon

class TestAnkiAddonLogic(unittest.TestCase):
    def setUp(self):
        self.handler = anki_addon.AnkiBridgeHandler.__new__(anki_addon.AnkiBridgeHandler)

    def test_add_cards_to_anki_legacy_api(self):
        # Setup mocks for legacy API (snake_case)
        col = MagicMock()
        mw_mock.col = col

        col.models.by_name.return_value = None

        # Use a real dict for model structure to persist appends
        model_data = {'flds': [], 'tmpls': [], 'req': []}
        model = MagicMock()
        model.__getitem__.side_effect = model_data.__getitem__
        model.__setitem__.side_effect = model_data.__setitem__
        model.__contains__.side_effect = model_data.__contains__
        # __delitem__ needed for 'del model['req']'
        model.__delitem__.side_effect = model_data.__delitem__

        col.models.new.return_value = model

        # Legacy methods
        col.models.new_field = MagicMock(return_value={'name': 'Question'})
        col.models.new_template = MagicMock(return_value={'name': 'Card 1'})

        # Ensure camelCase is missing
        del col.models.newField
        del col.models.newTemplate

        col.decks.id.return_value = 1

        # Legacy add_note
        col.add_note = MagicMock()
        del col.addNote

        cards = [{'question': 'q1', 'answer': 'a1'}]

        # Run
        count = self.handler.add_cards_to_anki("TestDeck", cards, "TestModel", [])

        self.assertEqual(count, 1)
        col.models.new_field.assert_called()
        col.add_note.assert_called()

        # Check if fields were added
        self.assertEqual(len(model_data['flds']), 2)

    def test_add_cards_to_anki_modern_api(self):
        # Setup mocks for modern API (camelCase)
        col = MagicMock()
        mw_mock.col = col

        col.models.by_name.return_value = None

        model_data = {'flds': [], 'tmpls': [], 'req': []}
        model = MagicMock()
        model.__getitem__.side_effect = model_data.__getitem__
        model.__setitem__.side_effect = model_data.__setitem__
        model.__contains__.side_effect = model_data.__contains__
        model.__delitem__.side_effect = model_data.__delitem__

        col.models.new.return_value = model

        # Modern methods
        col.models.newField = MagicMock(return_value={'name': 'Question'})
        col.models.newTemplate = MagicMock(return_value={'name': 'Card 1'})

        # Ensure snake_case is missing
        del col.models.new_field
        del col.models.new_template

        col.decks.id.return_value = 1

        # Modern addNote
        col.addNote = MagicMock()
        del col.add_note

        cards = [{'question': 'q1', 'answer': 'a1'}]

        # Run
        count = self.handler.add_cards_to_anki("TestDeck", cards, "TestModel", [])

        self.assertEqual(count, 1)
        col.models.newField.assert_called()
        col.addNote.assert_called()

        self.assertEqual(len(model_data['flds']), 2)

if __name__ == '__main__':
    unittest.main()

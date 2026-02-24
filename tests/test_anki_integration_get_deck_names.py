import unittest
import sys
import os
import json
import urllib.error
from unittest.mock import MagicMock, patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from anki_integration import get_deck_names


class TestGetDeckNames(unittest.TestCase):
    @patch('anki_integration.urllib.request.urlopen')
    def test_get_deck_names_success(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "decks": ["Deck1", "Deck2", "Deck3"]
        }).encode('utf-8')
        mock_urlopen.return_value.__enter__.return_value = mock_response

        decks = get_deck_names()
        self.assertEqual(decks, ["Deck1", "Deck2", "Deck3"])

    @patch('anki_integration.urllib.request.urlopen')
    def test_get_deck_names_empty(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"decks": []}).encode('utf-8')
        mock_urlopen.return_value.__enter__.return_value = mock_response

        decks = get_deck_names()
        self.assertEqual(decks, [])

    @patch('anki_integration.urllib.request.urlopen')
    @patch('builtins.print')
    def test_get_deck_names_with_log_callback(self, mock_print, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"decks": ["TestDeck"]}).encode('utf-8')
        mock_urlopen.return_value.__enter__.return_value = mock_response

        logs = []
        def log_callback(msg):
            logs.append(msg)

        decks = get_deck_names(log_callback=log_callback)
        self.assertEqual(decks, ["TestDeck"])
        self.assertTrue(any("Connecting to Anki" in msg for msg in logs))
        self.assertTrue(any("Found 1 decks" in msg for msg in logs))

    @patch('anki_integration.urllib.request.urlopen')
    @patch('builtins.print')
    def test_get_deck_names_connection_error(self, mock_print, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.URLError("Connection refused")

        logs = []
        def log_callback(msg):
            logs.append(msg)

        decks = get_deck_names(log_callback=log_callback)
        self.assertEqual(decks, [])
        self.assertTrue(any("Failed to connect" in msg for msg in logs))

    @patch('anki_integration.urllib.request.urlopen')
    def test_get_deck_names_http_error(self, mock_urlopen):
        mock_error = urllib.error.HTTPError(
            url="http://localhost:5005/get_decks", code=500, msg="Internal Server Error", hdrs={}, fp=None
        )
        mock_urlopen.side_effect = mock_error

        decks = get_deck_names()
        self.assertEqual(decks, [])

    @patch('anki_integration.urllib.request.urlopen')
    def test_get_deck_names_missing_decks_key(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({}).encode('utf-8')
        mock_urlopen.return_value.__enter__.return_value = mock_response

        decks = get_deck_names()
        self.assertEqual(decks, [])


if __name__ == '__main__':
    unittest.main()

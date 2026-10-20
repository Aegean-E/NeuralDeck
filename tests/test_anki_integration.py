import unittest
import sys
import os
import json
import urllib.error
from unittest.mock import MagicMock, patch

# Add the parent directory to sys.path to allow importing from root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from anki_integration import create_anki_deck, check_anki_connection


def _opener_returning(response):
    opener = MagicMock()
    opener.open.return_value.__enter__.return_value = response
    return opener


class TestAnkiIntegration(unittest.TestCase):
    @patch('anki_integration._get_no_proxy_opener')
    def test_check_anki_connection_success(self, mock_get_opener):
        mock_get_opener.return_value = _opener_returning(MagicMock())
        self.assertTrue(check_anki_connection())

    @patch('anki_integration._get_no_proxy_opener')
    def test_check_anki_connection_failure(self, mock_get_opener):
        mock_get_opener.return_value.open.side_effect = urllib.error.URLError("Connection refused")
        self.assertFalse(check_anki_connection())

    @patch('anki_integration._get_no_proxy_opener')
    def test_create_anki_deck_success(self, mock_get_opener):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"count": 5}).encode('utf-8')
        mock_get_opener.return_value = _opener_returning(mock_response)

        count = create_anki_deck("TestDeck", [("Q1", "A1")])
        self.assertEqual(count, 5)

    @patch('anki_integration._get_no_proxy_opener')
    def test_create_anki_deck_connection_error(self, mock_get_opener):
        mock_get_opener.return_value.open.side_effect = urllib.error.URLError("Connection refused")

        with self.assertRaises(ConnectionError) as cm:
            create_anki_deck("TestDeck", [])
        self.assertIn("Could not connect to Anki", str(cm.exception))

    @patch('anki_integration._get_no_proxy_opener')
    def test_create_anki_deck_http_error(self, mock_get_opener):
        mock_error = urllib.error.HTTPError(
            url="http://localhost:5005", code=500, msg="Internal Server Error", hdrs={}, fp=None
        )
        mock_error.read = MagicMock(return_value=json.dumps({"error": "Failed to add card"}).encode('utf-8'))
        mock_get_opener.return_value.open.side_effect = mock_error

        with self.assertRaises(Exception) as cm:
            create_anki_deck("TestDeck", [("Q", "A")])
        self.assertIn("Anki Sync Failed (500)", str(cm.exception))
        self.assertIn("Failed to add card", str(cm.exception))

    @patch('anki_integration._get_no_proxy_opener')
    def test_create_anki_deck_http_error_malformed(self, mock_get_opener):
        mock_error = urllib.error.HTTPError(
            url="http://localhost:5005", code=400, msg="Bad Request", hdrs={}, fp=None
        )
        mock_error.read = MagicMock(return_value=b"Just plain text error")
        mock_get_opener.return_value.open.side_effect = mock_error

        with self.assertRaises(Exception) as cm:
            create_anki_deck("TestDeck", [("Q", "A")])
        self.assertIn("Anki Sync Failed (400)", str(cm.exception))
        self.assertIn("Just plain text error", str(cm.exception))

if __name__ == '__main__':
    unittest.main()

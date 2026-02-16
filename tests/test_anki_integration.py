import unittest
import sys
import os
import json
import urllib.error
from unittest.mock import MagicMock, patch

# Add the parent directory to sys.path to allow importing from root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from anki_integration import create_anki_deck, check_anki_connection

class TestAnkiIntegration(unittest.TestCase):
    @patch('anki_integration.urllib.request.urlopen')
    def test_check_anki_connection_success(self, mock_urlopen):
        # Mock successful connection
        mock_urlopen.return_value.__enter__.return_value = MagicMock()
        self.assertTrue(check_anki_connection())

    @patch('anki_integration.urllib.request.urlopen')
    def test_check_anki_connection_failure(self, mock_urlopen):
        # Mock failure
        mock_urlopen.side_effect = urllib.error.URLError("Connection refused")
        self.assertFalse(check_anki_connection())

    @patch('anki_integration.urllib.request.urlopen')
    def test_create_anki_deck_success(self, mock_urlopen):
        # Mock successful response
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"count": 5}).encode('utf-8')
        mock_urlopen.return_value.__enter__.return_value = mock_response

        count = create_anki_deck("TestDeck", [("Q1", "A1")])
        self.assertEqual(count, 5)

    @patch('anki_integration.urllib.request.urlopen')
    def test_create_anki_deck_connection_error(self, mock_urlopen):
        # Mock connection error
        mock_urlopen.side_effect = urllib.error.URLError("Connection refused")

        with self.assertRaises(ConnectionError) as cm:
            create_anki_deck("TestDeck", [])
        self.assertIn("Could not connect to Anki", str(cm.exception))

    @patch('anki_integration.urllib.request.urlopen')
    def test_create_anki_deck_http_error(self, mock_urlopen):
        # Mock HTTP Error
        mock_error = urllib.error.HTTPError(
            url="http://localhost:5005", code=500, msg="Internal Server Error", hdrs={}, fp=None
        )
        mock_error.read = MagicMock(return_value=json.dumps({"error": "Failed to add card"}).encode('utf-8'))
        mock_urlopen.side_effect = mock_error

        with self.assertRaises(Exception) as cm:
            create_anki_deck("TestDeck", [("Q", "A")])
        self.assertIn("Anki Server Error (500)", str(cm.exception))
        self.assertIn("Failed to add card", str(cm.exception))

    @patch('anki_integration.urllib.request.urlopen')
    def test_create_anki_deck_http_error_malformed(self, mock_urlopen):
        # Mock HTTP Error with non-JSON body
        mock_error = urllib.error.HTTPError(
            url="http://localhost:5005", code=400, msg="Bad Request", hdrs={}, fp=None
        )
        mock_error.read = MagicMock(return_value=b"Just plain text error")
        mock_urlopen.side_effect = mock_error

        with self.assertRaises(Exception) as cm:
            create_anki_deck("TestDeck", [("Q", "A")])
        self.assertIn("Anki Server Error (400)", str(cm.exception))
        self.assertIn("Just plain text error", str(cm.exception))

if __name__ == '__main__':
    unittest.main()

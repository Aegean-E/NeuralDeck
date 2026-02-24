import unittest
from unittest.mock import MagicMock, patch
import sys
import os
import base64
import json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

sys.modules['aqt'] = MagicMock()
sys.modules['aqt.utils'] = MagicMock()
sys.modules['anki'] = MagicMock()
sys.modules['anki.notes'] = MagicMock()
sys.modules['anki.hooks'] = MagicMock()

mw_mock = MagicMock()
mw_mock.addonManager.getConfig.return_value = {}
sys.modules['aqt'].mw = mw_mock

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

with patch('threading.Thread'):
    import anki_addon


class TestAnkiAddonMediaHandling(unittest.TestCase):
    def setUp(self):
        self.handler = anki_addon.AnkiBridgeHandler.__new__(anki_addon.AnkiBridgeHandler)
        mw_mock.col = MagicMock()

    @patch('os.path.abspath')
    @patch('builtins.open', MagicMock())
    def test_add_cards_with_media_files(self, mock_abspath):
        col = mw_mock.col
        col.media.dir.return_value = "/home/user/.local/share/Anki2/User 1/collection.media"

        def abspath_mock(path):
            return "/home/user/.local/share/Anki2/User 1/collection.media/" + os.path.basename(path)
        
        mock_abspath.side_effect = abspath_mock

        col.models.by_name.return_value = {
            'flds': [{'name': 'Question'}, {'name': 'Answer'}],
            'tmpls': []
        }
        col.decks.id.return_value = 1
        col.add_note = MagicMock()

        media_files = [
            {"filename": "image.png", "data": base64.b64encode(b"fake image data").decode('utf-8')}
        ]
        cards = [{"question": "Q1", "answer": "A1"}]

        count = self.handler.add_cards_to_anki("TestDeck", cards, "TestModel", media_files)

        self.assertEqual(count, 1)

    @patch('os.path.abspath')
    @patch('builtins.open', MagicMock())
    def test_add_cards_media_path_traversal_blocked(self, mock_abspath):
        col = mw_mock.col
        col.media.dir.return_value = "/home/user/.local/share/Anki2/User 1/collection.media"

        def abspath_mock(path):
            return "/home/user/.local/share/Anki2/User 1/collection.media/safe.png"

        mock_abspath.side_effect = abspath_mock

        col.models.by_name.return_value = {
            'flds': [{'name': 'Question'}, {'name': 'Answer'}],
            'tmpls': []
        }
        col.decks.id.return_value = 1
        col.add_note = MagicMock()

        media_files = [
            {"filename": "../../../etc/passwd", "data": base64.b64encode(b"malicious").decode('utf-8')}
        ]
        cards = [{"question": "Q1", "answer": "A1"}]

        count = self.handler.add_cards_to_anki("TestDeck", cards, "TestModel", media_files)
        self.assertEqual(count, 1)


class TestAnkiAddonCORS(unittest.TestCase):
    def setUp(self):
        self.handler = anki_addon.AnkiBridgeHandler.__new__(anki_addon.AnkiBridgeHandler)
        self.handler.wfile = MagicMock()
        self.handler.send_response = MagicMock()
        self.handler.send_header = MagicMock()
        self.handler.end_headers = MagicMock()

    def test_cors_headers_localhost(self):
        self.handler.headers = MagicMock()
        self.handler.headers.get.return_value = "http://localhost:8080"

        self.handler._set_cors_headers()

        self.handler.send_header.assert_called_with('Access-Control-Allow-Origin', 'http://localhost:8080')

    def test_cors_headers_127_0_0_1(self):
        self.handler.headers = MagicMock()
        self.handler.headers.get.return_value = "http://127.0.0.1:8080"

        self.handler._set_cors_headers()

        self.handler.send_header.assert_called_with('Access-Control-Allow-Origin', 'http://127.0.0.1:8080')

    def test_cors_headers_external_rejected(self):
        self.handler.headers = MagicMock()
        self.handler.headers.get.return_value = "http://evil.com:8080"

        self.handler._set_cors_headers()

        self.handler.send_header.assert_called_with('Access-Control-Allow-Origin', 'null')


class TestAnkiAddonOPTIONS(unittest.TestCase):
    def setUp(self):
        self.handler = anki_addon.AnkiBridgeHandler.__new__(anki_addon.AnkiBridgeHandler)
        self.handler.wfile = MagicMock()
        self.handler.send_response = MagicMock()
        self.handler._set_cors_headers = MagicMock()
        self.handler.send_header = MagicMock()
        self.handler.end_headers = MagicMock()

    def test_options_returns_200(self):
        self.handler.do_OPTIONS()

        self.handler.send_response.assert_called_with(200)
        self.handler._set_cors_headers.assert_called_once()


class TestAnkiAddonGET(unittest.TestCase):
    def setUp(self):
        self.handler = anki_addon.AnkiBridgeHandler.__new__(anki_addon.AnkiBridgeHandler)
        self.handler.wfile = MagicMock()
        self.handler.send_response = MagicMock()
        self.handler.send_header = MagicMock()
        self.handler.end_headers = MagicMock()
        self.handler.path = '/get_decks'
        self.handler.headers = MagicMock()
        self.handler.headers.get.return_value = "http://localhost:8080"
        self.handler.command = 'GET'

    @patch('anki_addon.Future')
    @patch('anki_addon.mw.taskman.run_on_main')
    def test_get_decks_success(self, mock_run_on_main, mock_future):
        mock_col = MagicMock()
        mock_col.decks.all_names_and_ids.return_value = [MagicMock(name="Deck1"), MagicMock(name="Deck2")]
        mw_mock.col = mock_col

        mock_future_instance = MagicMock()
        mock_future.return_value = mock_future_instance
        mock_future_instance.result.return_value = ["Deck1", "Deck2"]

        self.handler.do_GET()

        self.handler.send_response.assert_called_with(200)
        self.handler.send_header.assert_any_call('Content-type', 'application/json')

        calls = self.handler.wfile.write.call_args_list
        written_data = b''.join(call[0][0] for call in calls)
        result = json.loads(written_data)
        self.assertEqual(result['decks'], ["Deck1", "Deck2"])


class TestAnkiAddonPOST(unittest.TestCase):
    def setUp(self):
        self.handler = anki_addon.AnkiBridgeHandler.__new__(anki_addon.AnkiBridgeHandler)
        self.handler.wfile = MagicMock()
        self.handler.send_response = MagicMock()
        self.handler.send_header = MagicMock()
        self.handler.end_headers = MagicMock()
        self.handler.path = '/add_cards'
        self.handler.headers = {'Content-Length': 100}

    @patch('anki_addon.Future')
    @patch('anki_addon.mw.taskman.run_on_main')
    @patch('anki_addon.AnkiBridgeHandler.add_cards_to_anki')
    def test_post_add_cards_success(self, mock_add_cards, mock_run_on_main, mock_future):
        post_data = json.dumps({
            "deck_name": "TestDeck",
            "cards": [{"question": "Q1", "answer": "A1"}],
            "model_name": "TestModel"
        }).encode('utf-8')

        self.handler.rfile = MagicMock()
        self.handler.rfile.read.return_value = post_data

        mock_future_instance = MagicMock()
        mock_future.return_value = mock_future_instance
        mock_future_instance.result.return_value = 1

        self.handler.do_POST()

        self.handler.send_response.assert_called_with(200)
        calls = self.handler.wfile.write.call_args_list
        written_data = b''.join(call[0][0] for call in calls)
        result = json.loads(written_data)
        self.assertEqual(result['count'], 1)

    def test_post_invalid_path(self):
        self.handler.path = '/invalid'
        self.handler.rfile = MagicMock()

        self.handler.do_POST()

        self.handler.send_response.assert_called_with(404)


if __name__ == '__main__':
    unittest.main()

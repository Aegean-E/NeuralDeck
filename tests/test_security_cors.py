import unittest
import sys
import os
from unittest.mock import MagicMock, patch
from io import BytesIO

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

# Prevent server thread from starting
with patch('threading.Thread'):
    import anki_addon

class TestSecurityCORS(unittest.TestCase):
    def setUp(self):
        # Create a mock handler without calling __init__
        self.handler = anki_addon.AnkiBridgeHandler.__new__(anki_addon.AnkiBridgeHandler)
        self.handler.send_response = MagicMock()
        self.handler.send_header = MagicMock()
        self.handler.end_headers = MagicMock()
        self.handler.wfile = BytesIO()
        self.handler.headers = {}

    def test_cors_header_allowed_origin(self):
        self.handler.headers = {'Origin': 'http://localhost:3000'}
        self.handler.do_OPTIONS()

        # Check if Access-Control-Allow-Origin is http://localhost:3000
        calls = self.handler.send_header.call_args_list
        cors_call = [c for c in calls if c[0][0] == 'Access-Control-Allow-Origin']
        self.assertTrue(len(cors_call) > 0, "Access-Control-Allow-Origin header not found")
        self.assertEqual(cors_call[0][0][1], 'http://localhost:3000')

    def test_cors_header_blocked_origin(self):
        self.handler.headers = {'Origin': 'http://evil.com'}
        self.handler.do_OPTIONS()

        # Check that Access-Control-Allow-Origin is NOT present
        calls = self.handler.send_header.call_args_list
        cors_call = [c for c in calls if c[0][0] == 'Access-Control-Allow-Origin']
        self.assertEqual(len(cors_call), 0, "Access-Control-Allow-Origin should NOT be present for evil.com")

    def test_cors_header_bypass_attempt(self):
        # Test common CORS bypass attempts
        bypass_origins = [
            'http://localhost.evil.com',
            'http://evil.com/localhost',
            'http://127.0.0.1.evil.com',
            'http://evil.com?origin=localhost'
        ]
        for origin in bypass_origins:
            self.handler.headers = {'Origin': origin}
            self.handler.send_header = MagicMock() # Reset mock for each attempt
            self.handler.do_OPTIONS()

            calls = self.handler.send_header.call_args_list
            cors_call = [c for c in calls if c[0][0] == 'Access-Control-Allow-Origin']
            self.assertEqual(len(cors_call), 0, f"Access-Control-Allow-Origin should NOT be present for bypass attempt: {origin}")

    def test_cors_header_no_origin(self):
        self.handler.headers = {}
        self.handler.do_OPTIONS()

        # Check that Access-Control-Allow-Origin is NOT present
        calls = self.handler.send_header.call_args_list
        cors_call = [c for c in calls if c[0][0] == 'Access-Control-Allow-Origin']
        self.assertEqual(len(cors_call), 0, "Access-Control-Allow-Origin should NOT be present when Origin is missing")

    def test_cors_header_ipv6_allowed(self):
        self.handler.headers = {'Origin': 'http://[::1]:8080'}
        self.handler.do_OPTIONS()

        # Check if Access-Control-Allow-Origin is http://[::1]:8080
        calls = self.handler.send_header.call_args_list
        cors_call = [c for c in calls if c[0][0] == 'Access-Control-Allow-Origin']
        self.assertTrue(len(cors_call) > 0, "Access-Control-Allow-Origin header not found for IPv6")
        self.assertEqual(cors_call[0][0][1], 'http://[::1]:8080')

    def test_cors_header_get_allowed(self):
        self.handler.headers = {'Origin': 'http://127.0.0.1:8080'}
        self.handler.path = '/get_decks'

        # Mock mw.taskman.run_on_main to execute the callback immediately
        def mock_run_on_main(task):
            task()
        mw_mock.taskman.run_on_main = mock_run_on_main
        mw_mock.col.decks.allNames.return_value = ["Deck1"]

        self.handler.do_GET()

        # Check if Access-Control-Allow-Origin is http://127.0.0.1:8080
        calls = self.handler.send_header.call_args_list
        cors_call = [c for c in calls if c[0][0] == 'Access-Control-Allow-Origin']
        self.assertTrue(len(cors_call) > 0, "Access-Control-Allow-Origin header not found")
        self.assertEqual(cors_call[0][0][1], 'http://127.0.0.1:8080')

if __name__ == '__main__':
    unittest.main()

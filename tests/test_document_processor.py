import unittest
import sys
import os
import json
import urllib.error
import socket
import http.client
from unittest.mock import MagicMock, patch

# Add the parent directory to sys.path to allow importing from root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from document_processor import (
    robust_parse_objects,
    filter_and_process_cards,
    extract_text_from_pdf,
    smart_chunk_text,
    call_lm_studio,
    generate_qa_pairs
)

class TestDocumentProcessor(unittest.TestCase):
    # --- Parsing Tests ---
    def test_robust_parse_objects_standard(self):
        text = '[{"question": "Q1", "answer": "A1"}]'
        result = robust_parse_objects(text)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['question'], 'Q1')

    def test_robust_parse_objects_markdown(self):
        text = '```json\n[{"question": "Q2", "answer": "A2"}]\n```'
        result = robust_parse_objects(text)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['question'], 'Q2')

    def test_robust_parse_objects_multiple_objects(self):
        text = '{"question": "Q3", "answer": "A3"}\n{"question": "Q4", "answer": "A4"}'
        result = robust_parse_objects(text)
        self.assertEqual(len(result), 2)

    def test_robust_parse_objects_wrapper(self):
        text = '{"cards": [{"question": "Q1", "answer": "A1"}]}'
        result = robust_parse_objects(text)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['question'], 'Q1')

    def test_robust_parse_objects_nested(self):
        text = '{"data": {"results": [{"question": "Q2", "answer": "A2"}]}}'
        result = robust_parse_objects(text)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['question'], 'Q2')

    def test_robust_parse_objects_with_text(self):
        text = 'Here is the JSON:\n[{"question": "Q_Text", "answer": "A_Text"}]\nHope this helps.'
        result = robust_parse_objects(text)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['question'], 'Q_Text')

    # --- Filter & Process Tests ---
    def test_filter_and_process_cards_basic(self):
        raw_data = [{'question': 'Q1', 'answer': 'A1', 'deck': 'Default'}]
        processed = filter_and_process_cards(raw_data, deck_names=[], smart_deck_match=False, filter_yes_no=True)
        self.assertEqual(len(processed), 1)

    def test_filter_and_process_cards_yes_no(self):
        raw_data = [
            {'question': 'Is this valid?', 'answer': 'Yes'},
            {'question': 'Is this also valid?', 'answer': 'No.'},
            {'question': 'What about this?', 'answer': 'Detailed answer.'}
        ]
        processed = filter_and_process_cards(raw_data, deck_names=[], smart_deck_match=False, filter_yes_no=True)
        self.assertEqual(len(processed), 1)
        self.assertEqual(processed[0]['answer'], 'Detailed answer.')

    def test_filter_and_process_cards_capitalized(self):
        raw_data = [{'Question': 'CapQ', 'Answer': 'CapA'}]
        processed = filter_and_process_cards(raw_data, deck_names=[], smart_deck_match=False, filter_yes_no=True)
        self.assertEqual(len(processed), 1)
        self.assertEqual(processed[0]['question'], 'CapQ')

    # --- Chunking Tests ---
    def test_smart_chunk_text_strict(self):
        text = "A" * 200 + "\n\n" + "B" * 50
        chunks = smart_chunk_text(text, 100)
        for c in chunks:
            self.assertLessEqual(len(c), 100)
        self.assertTrue(len(chunks) >= 3)

    def test_smart_chunk_text_sentences(self):
        s1 = "A" * 60 + ". "
        s2 = "B" * 60 + "."
        text = s1 + s2
        chunks = smart_chunk_text(text, 70)
        self.assertEqual(len(chunks), 2)
        for c in chunks:
            self.assertLessEqual(len(c), 70)

    # --- Extraction Tests (Mocked) ---
    @patch('builtins.open')
    @patch('document_processor.PyPDF2')
    def test_extract_text_empty(self, mock_pypdf2, mock_open):
        mock_reader = MagicMock()
        mock_reader.pages = []
        mock_reader.is_encrypted = False
        mock_pypdf2.PdfReader.return_value = mock_reader

        with self.assertRaises(Exception) as cm:
            extract_text_from_pdf("dummy.pdf")
        self.assertIn("0 pages found", str(cm.exception))

    @patch('builtins.open')
    @patch('document_processor.PyPDF2')
    def test_extract_text_image_only(self, mock_pypdf2, mock_open):
        mock_reader = MagicMock()
        mock_page = MagicMock()
        mock_page.extract_text.return_value = ""
        mock_reader.pages = [mock_page]
        mock_reader.is_encrypted = False
        mock_pypdf2.PdfReader.return_value = mock_reader

        with self.assertRaises(Exception) as cm:
            extract_text_from_pdf("dummy.pdf")
        self.assertIn("No text could be extracted", str(cm.exception))

    @patch('builtins.open')
    @patch('document_processor.PyPDF2')
    def test_extract_text_partial_success(self, mock_pypdf2, mock_open):
        mock_reader = MagicMock()

        page1 = MagicMock()
        page1.extract_text.return_value = "Content P1"

        page2 = MagicMock()
        page2.extract_text.return_value = "" # Scanned

        page3 = MagicMock()
        page3.extract_text.return_value = "Content P3"

        mock_reader.pages = [page1, page2, page3]
        mock_reader.is_encrypted = False
        mock_pypdf2.PdfReader.return_value = mock_reader

        text = extract_text_from_pdf("dummy.pdf")
        self.assertIn("Content P1", text)
        self.assertIn("NO TEXT DETECTED", text)
        self.assertIn("Content P3", text)

    @patch('builtins.open')
    @patch('document_processor.PyPDF2')
    def test_extract_text_success(self, mock_pypdf2, mock_open):
        mock_reader = MagicMock()
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Hello World"
        mock_reader.pages = [mock_page]
        mock_reader.is_encrypted = False
        mock_pypdf2.PdfReader.return_value = mock_reader

        text = extract_text_from_pdf("dummy.pdf")
        self.assertIn("Hello World", text)

    # --- Retry Tests (Mocked) ---
    @patch('document_processor.urllib.request.urlopen')
    @patch('document_processor.time.sleep')
    def test_retry_success(self, mock_sleep, mock_urlopen):
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__iter__.return_value = [b'data: {"choices": [{"delta": {"content": "Hello"}}]}', b'data: [DONE]']
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = None

        mock_urlopen.side_effect = [
            urllib.error.URLError("Fail 1"),
            socket.timeout(),
            mock_response
        ]

        result = call_lm_studio("prompt", "sys")
        self.assertEqual(result, "Hello")
        self.assertEqual(mock_urlopen.call_count, 3)

    @patch('document_processor.urllib.request.urlopen')
    def test_call_lm_studio_malformed_chunk(self, mock_urlopen):
        # Simulation of a stream with one bad chunk in the middle
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__iter__.return_value = [
            b'data: {"choices": [{"delta": {"content": "Part1"}}]}',
            b'data: {BAD JSON}',
            b'data: {"choices": [{"delta": {"content": "Part2"}}]}',
            b'data: [DONE]'
        ]
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = None
        mock_urlopen.return_value = mock_response

        result = call_lm_studio("prompt", "sys")
        # It should skip the bad chunk and stitch Part1 + Part2
        self.assertEqual(result, "Part1Part2")

    @patch('document_processor.urllib.request.urlopen')
    @patch('document_processor.time.sleep')
    def test_retry_failure(self, mock_sleep, mock_urlopen):
        mock_urlopen.side_effect = [
            urllib.error.URLError("Fail 1"),
            urllib.error.URLError("Fail 2"),
            urllib.error.URLError("Fail 3")
        ]

        with self.assertRaises(Exception) as cm:
            call_lm_studio("prompt", "sys")

        self.assertIn("Could not connect", str(cm.exception))
        self.assertEqual(mock_urlopen.call_count, 3)

    @patch('document_processor.as_completed')
    @patch('document_processor.os.cpu_count')
    @patch('document_processor.ThreadPoolExecutor')
    def test_concurrency_limit(self, mock_executor, mock_cpu_count, mock_as_completed):
        mock_cpu_count.return_value = 4
        # Mock executor instance context manager
        mock_executor.return_value.__enter__.return_value = MagicMock()
        mock_executor.return_value.__exit__.return_value = None

        # as_completed returns an empty iterator so the loop finishes immediately
        mock_as_completed.return_value = []

        text = "Dummy text content."
        generate_qa_pairs(text, concurrency=10)

        # Should be clamped to 4
        mock_executor.assert_called_with(max_workers=4)

    @patch('document_processor.smart_chunk_text')
    @patch('document_processor.as_completed')
    @patch('document_processor.ThreadPoolExecutor')
    def test_stop_callback_stops_generation(self, mock_executor, mock_as_completed, mock_chunk):
        mock_executor.return_value.__enter__.return_value = MagicMock()
        mock_executor.return_value.__exit__.return_value = None

        # Force 2 chunks
        mock_chunk.return_value = ["chunk1", "chunk2"]

        # Futures
        f1, f2 = MagicMock(), MagicMock()
        # submit is called twice
        mock_executor.return_value.__enter__.return_value.submit.side_effect = [f1, f2]

        mock_as_completed.return_value = [f1, f2]
        f1.result.return_value = []

        # stop_callback returns False first (allow 1st), then True (stop before 2nd)
        stop_cb = MagicMock(side_effect=[False, True])

        generate_qa_pairs("Dummy text", stop_callback=stop_cb)

        f1.result.assert_called()
        f2.result.assert_not_called()

if __name__ == '__main__':
    unittest.main()

import unittest
import sys
import os
import json
from unittest.mock import MagicMock, patch

# Add the parent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from document_processor import extract_text_from_pdf, generate_qa_pairs
from anki_integration import create_anki_deck

class TestFullPipeline(unittest.TestCase):

    @patch('document_processor.PyPDF2')
    @patch('builtins.open')
    @patch('document_processor.check_llm_server')
    @patch('document_processor.call_lm_studio')
    @patch('anki_integration.urllib.request.urlopen')
    def test_full_pipeline_success(self, mock_anki_urlopen, mock_lm_studio, mock_check_server, mock_open, mock_pypdf2):
        # 1. Setup PDF Extraction Mock
        mock_reader = MagicMock()
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "This is a sample text about Mitochondria. Mitochondria are the powerhouse of the cell."
        mock_reader.pages = [mock_page]
        mock_reader.is_encrypted = False
        mock_pypdf2.PdfReader.return_value = mock_reader

        # 2. Setup LLM Mock
        # The LLM should return a JSON string representing generated cards
        mock_lm_studio.return_value = json.dumps([
            {"question": "What are Mitochondria?", "answer": "The powerhouse of the cell.", "deck": "Biology", "quote": "Mitochondria are the powerhouse of the cell."}
        ])

        # 3. Setup Anki Mock
        mock_anki_response = MagicMock()
        mock_anki_response.read.return_value = json.dumps({"count": 1}).encode('utf-8')
        mock_anki_urlopen.return_value.__enter__.return_value = mock_anki_response

        # --- Execution Phase ---

        # Step A: Extract Text
        text = extract_text_from_pdf("dummy.pdf")
        self.assertIn("Mitochondria", text)

        # Step B: Generate Cards
        qa_pairs = generate_qa_pairs(
            text,
            deck_names=["Biology"],
            target_language="English",
            api_url="http://mock-api",
            log_callback=print # Use print to see logs in test output if needed
        )

        self.assertEqual(len(qa_pairs), 1)
        self.assertEqual(qa_pairs[0]['question'], "What are Mitochondria?")

        # Step C: Sync to Anki
        # Simulate user approving the card
        approved_cards = [qa_pairs[0]]

        # Group by deck (as done in UI)
        deck_name = approved_cards[0]['deck']
        cards_to_sync = [(c['question'], c['answer']) for c in approved_cards]

        count = create_anki_deck(deck_name, cards_to_sync)

        self.assertEqual(count, 1)

    @patch('document_processor.PyPDF2')
    @patch('builtins.open')
    @patch('document_processor.check_llm_server')
    @patch('document_processor.call_lm_studio')
    def test_pipeline_extraction_failure(self, mock_lm_studio, mock_check_server, mock_open, mock_pypdf2):
        # Setup PDF Extraction to fail
        mock_pypdf2.PdfReader.side_effect = Exception("PDF Corrupted")

        with self.assertRaises(Exception) as cm:
            extract_text_from_pdf("corrupt.pdf")

        self.assertIn("Failed to read PDF", str(cm.exception))

    @patch('document_processor.check_llm_server')
    @patch('document_processor.call_lm_studio')
    def test_pipeline_llm_malformed_response(self, mock_lm_studio, mock_check_server):
        # LLM returns garbage
        mock_lm_studio.return_value = "I'm sorry, I can't do that."

        qa_pairs = generate_qa_pairs("Some text", log_callback=lambda x: None)

        # Should return empty list, not crash
        self.assertEqual(qa_pairs, [])

if __name__ == '__main__':
    unittest.main()

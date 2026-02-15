import unittest
import sys
import os
import json

# Add the parent directory to sys.path to allow importing from root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from document_processor import robust_parse_objects, filter_and_process_cards

class TestDocumentProcessor(unittest.TestCase):
    def test_robust_parse_objects_standard(self):
        text = '[{"question": "Q1", "answer": "A1"}]'
        result = robust_parse_objects(text)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['question'], 'Q1')

    def test_robust_parse_objects_markdown(self):
        # This simulates LLM output with markdown
        text = '```json\n[{"question": "Q2", "answer": "A2"}]\n```'
        result = robust_parse_objects(text)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['question'], 'Q2')

    def test_robust_parse_objects_multiple_objects(self):
        # This simulates LLM outputting multiple separate objects
        text = '{"question": "Q3", "answer": "A3"}\n{"question": "Q4", "answer": "A4"}'
        result = robust_parse_objects(text)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['question'], 'Q3')
        self.assertEqual(result[1]['question'], 'Q4')

    def test_filter_and_process_cards_basic(self):
        raw_data = [{'question': 'Q1', 'answer': 'A1', 'deck': 'Default'}]
        processed = filter_and_process_cards(raw_data, deck_names=[], smart_deck_match=False, filter_yes_no=True)
        self.assertEqual(len(processed), 1)
        self.assertEqual(processed[0]['question'], 'Q1')

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
        # This test checks if capitalized keys are handled. Currently they are NOT.
        # This test is expected to fail or return 0 cards until fixed.
        raw_data = [{'Question': 'CapQ', 'Answer': 'CapA'}]
        processed = filter_and_process_cards(raw_data, deck_names=[], smart_deck_match=False, filter_yes_no=True)
        # Assuming we want to support this, we expect 1 card.
        # If not supported yet, this will be 0.
        self.assertEqual(len(processed), 1, "Should handle capitalized keys")
        self.assertEqual(processed[0]['question'], 'CapQ')

if __name__ == '__main__':
    unittest.main()

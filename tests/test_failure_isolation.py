import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import json
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from document_processor import generate_qa_pairs
from pipeline_utils import PipelineStats

class TestFailureIsolation(unittest.TestCase):

    @patch('document_processor.check_llm_server')
    @patch('document_processor.call_lm_studio')
    @patch('document_processor.smart_chunk_text')
    def test_single_chunk_failure(self, mock_chunk, mock_llm, mock_check):
        mock_check.return_value = True
        mock_chunk.return_value = ["Chunk1", "Chunk2", "Chunk3"]

        # P1 succeeds, P2 fails, P3 succeeds
        def side_effect(prompt, *args, **kwargs):
            if "Chunk1" in prompt:
                return '[{"question": "Question Number One Is Here", "answer": "Answer Number One Is Here"}]'
            if "Chunk2" in prompt:
                raise Exception("Simulated LLM Failure")
            if "Chunk3" in prompt:
                return '[{"question": "Question Number Three Is Here", "answer": "Answer Number Three Is Here"}]'
            return '[]'

        mock_llm.side_effect = side_effect

        stats = PipelineStats()
        res = generate_qa_pairs("dummy", pipeline_stats=stats)

        # Should contain Q1 and Q3
        self.assertEqual(len(res), 2)
        self.assertEqual(res[0]['question'], "Question Number One Is Here")
        self.assertEqual(res[1]['question'], "Question Number Three Is Here")

        # Stats should show failure
        self.assertEqual(stats.metrics['processed_chunks'], 2)
        self.assertEqual(stats.metrics['failed_chunks'], 1)

    @patch('document_processor.check_llm_server')
    @patch('document_processor.call_lm_studio')
    @patch('document_processor.smart_chunk_text')
    def test_malformed_json_partial(self, mock_chunk, mock_llm, mock_check):
        mock_check.return_value = True
        mock_chunk.return_value = ["Chunk1"]

        # LLM returns one good card and one bad JSON line
        # But robust_parse_objects handles this.
        # Let's say it returns something that fails robust_parse_objects partially?
        # robust_parse_objects is very robust.
        # If call_lm_studio succeeds but returns garbage, it logs warning and returns nothing (empty list).

        mock_llm.return_value = "This is not JSON."

        stats = PipelineStats()
        res = generate_qa_pairs("dummy", pipeline_stats=stats)

        self.assertEqual(len(res), 0)
        # It's processed but yielded 0 cards. Not a "failed chunk" in terms of exception, but "0 cards".
        # However, generate_qa_pairs calls call_lm_studio inside try-except.
        # If call_lm_studio succeeds, it's processed.
        self.assertEqual(stats.metrics['processed_chunks'], 1)
        self.assertEqual(stats.metrics['failed_chunks'], 0)
        self.assertEqual(stats.metrics['cards_generated'], 0)

if __name__ == '__main__':
    unittest.main()

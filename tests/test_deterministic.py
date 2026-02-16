import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import json
import random

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from document_processor import generate_qa_pairs
from pipeline_utils import PipelineStats

class TestDeterministicMode(unittest.TestCase):

    @patch('document_processor.check_llm_server')
    @patch('document_processor.call_lm_studio')
    @patch('document_processor.smart_chunk_text')
    def test_determinism_output_order(self, mock_chunk, mock_llm, mock_check):
        mock_check.return_value = True
        mock_chunk.return_value = ["Chunk1", "Chunk2", "Chunk3"]

        # LLM returns identifyable cards (Length > 10 for validation)
        def side_effect(prompt, *args, **kwargs):
            if "Chunk1" in prompt: return '[{"question": "Question Number One Is Here", "answer": "Answer Number One Is Here", "deck": "D1"}]'
            if "Chunk2" in prompt: return '[{"question": "Question Number Two Is Here", "answer": "Answer Number Two Is Here", "deck": "D2"}]'
            if "Chunk3" in prompt: return '[{"question": "Question Number Three Is Here", "answer": "Answer Number Three Is Here", "deck": "D3"}]'
            return '[]'
        mock_llm.side_effect = side_effect

        stats = PipelineStats()

        # Run with deterministic_mode=True
        # This forces concurrency=1, so processing should be strictly sequential: 1->2->3
        res = generate_qa_pairs("dummy", deterministic_mode=True, pipeline_stats=stats)

        self.assertEqual(len(res), 3)
        self.assertEqual(res[0]['question'], "Question Number One Is Here")
        self.assertEqual(res[1]['question'], "Question Number Two Is Here")
        self.assertEqual(res[2]['question'], "Question Number Three Is Here")

        # Verify stats
        self.assertEqual(stats.metrics['processed_chunks'], 3)
        self.assertEqual(stats.metrics['cards_generated'], 3)

    @patch('document_processor.check_llm_server')
    @patch('document_processor.call_lm_studio')
    @patch('document_processor.smart_chunk_text')
    def test_determinism_random_seeding(self, mock_chunk, mock_llm, mock_check):
        mock_check.return_value = True
        mock_chunk.return_value = ["Chunk1"]
        mock_llm.return_value = '[]'

        # We want to check if random.seed(42) was called.
        # But random is imported inside document_processor.
        # So we patch document_processor.random

        with patch('document_processor.random') as mock_random:
            generate_qa_pairs("dummy", deterministic_mode=True)
            mock_random.seed.assert_called_with(42)
            # Ensure shuffle was NOT called (unless smart_deck_match is False, but default is True)
            # Wait, logic is: if smart_deck_match and NOT deterministic_mode: shuffle.
            # So here it should NOT be called.
            mock_random.shuffle.assert_not_called()

    @patch('document_processor.check_llm_server')
    @patch('document_processor.call_lm_studio')
    @patch('document_processor.smart_chunk_text')
    def test_nondeterministic_behavior(self, mock_chunk, mock_llm, mock_check):
        mock_check.return_value = True
        mock_chunk.return_value = ["Chunk1"]
        mock_llm.return_value = '[]'

        with patch('document_processor.random') as mock_random:
            generate_qa_pairs("dummy", deck_names=["A", "B"], deterministic_mode=False, smart_deck_match=True)
            # seed should NOT be called (or at least not with fixed value, but we can't assert that easily)
            # Actually, standard random.seed() is not called by us.
            mock_random.seed.assert_not_called()
            # Shuffle SHOULD be called
            mock_random.shuffle.assert_called()

if __name__ == '__main__':
    unittest.main()
